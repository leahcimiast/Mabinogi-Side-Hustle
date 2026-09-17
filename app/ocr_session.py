"""Bounded, scan-local Windows OCR process; no background service or uploads."""
import json
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import time


class OcrSession:
    def __init__(self, script, cancelled=None):
        self.script=Path(script).with_name('ocr_worker.ps1')
        self.cancelled=cancelled or (lambda:False)
        self.process=None
        self.reader=None
        self.temp=None
        self.responses=queue.Queue()
        self.metrics=dict(process_count=0,batch_count=0,image_count=0,png_encode_ms=0.0,
                          startup_ms=0.0,engine_init_ms=0.0,host_startup_estimate_ms=0.0,
                          decode_ms=0.0,recognition_ms=0.0,batch_roundtrip_ms=0.0)

    def __enter__(self):
        started=time.perf_counter()
        self.temp=tempfile.TemporaryDirectory(prefix='mabinogi-ocr-')
        try:
            self.process=subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive',
                '-ExecutionPolicy','Bypass','-File',str(self.script)],stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',
                errors='replace',bufsize=1,creationflags=subprocess.CREATE_NO_WINDOW)
            self.metrics['process_count']=1
            self.reader=threading.Thread(target=self._read,daemon=True)
            self.reader.start()
            ready=self._receive(15)
            if not ready.get('ready'):
                raise RuntimeError('Invalid OCR startup response')
            self.metrics['startup_ms']=(time.perf_counter()-started)*1000
            self.metrics['engine_init_ms']=ready['init_ms']
            self.metrics['host_startup_estimate_ms']=max(0,self.metrics['startup_ms']-ready['init_ms'])
            return self
        except BaseException:
            self.close()
            raise

    def _read(self):
        try:
            for line in self.process.stdout:
                self.responses.put(line)
        finally:
            self.responses.put(None)

    def _receive(self,timeout):
        deadline=time.monotonic()+timeout
        while True:
            if self.cancelled():
                raise RuntimeError('辨識已取消')
            left=deadline-time.monotonic()
            if left<=0:
                raise TimeoutError('Windows OCR batch timed out')
            try:
                line=self.responses.get(timeout=min(.05,left))
            except queue.Empty:
                continue
            if line is None:
                raise RuntimeError('Windows OCR process exited before responding')
            result=json.loads(line.lstrip('\ufeff'))
            if result.get('error'):
                raise RuntimeError(result['error'])
            return result

    def recognize_many(self,images,timeout=30):
        if not 1<=len(images)<=12:
            raise ValueError('OCR batch must contain 1 to 12 images')
        if self.cancelled():
            raise RuntimeError('辨識已取消')
        paths=[]
        started=time.perf_counter()
        for i,image in enumerate(images):
            path=Path(self.temp.name)/f'{self.metrics["batch_count"]}-{i}.png'
            image.save(path)
            paths.append(path)
        self.metrics['png_encode_ms']+=(time.perf_counter()-started)*1000
        started=time.perf_counter()
        self.process.stdin.write(json.dumps({'paths':[str(p) for p in paths]})+'\n')
        self.process.stdin.flush()
        reply=self._receive(timeout)
        self.metrics['batch_roundtrip_ms']+=(time.perf_counter()-started)*1000
        items=reply.get('items',[])
        if len(items)!=len(images):
            raise RuntimeError('OCR response does not match batch size')
        self.metrics['batch_count']+=1
        self.metrics['image_count']+=len(images)
        for item in items:
            self.metrics['decode_ms']+=item['decode_ms']
            self.metrics['recognition_ms']+=item['recognition_ms']
        for path in paths:
            path.unlink(missing_ok=True)
        return [item['words'] for item in items]

    def close(self):
        if self.process:
            if self.process.poll() is None:
                try:
                    self.process.stdin.write('{"stop":true}\n')
                    self.process.stdin.flush()
                    self.process.wait(timeout=.3)
                except (OSError,subprocess.TimeoutExpired):
                    self.process.kill()
                    self.process.wait(timeout=2)
            if self.reader:
                self.reader.join(timeout=1)
            for stream in (self.process.stdin,self.process.stdout):
                if stream:
                    stream.close()
            self.process=None
        if self.temp:
            self.temp.cleanup()
            self.temp=None

    def __exit__(self,*exc):
        self.close()
