"""Local OCR evidence. Uncertain counts remain unknown; never guess a stack of one."""
from dataclasses import dataclass
import json
import re
import subprocess
import tempfile
from pathlib import Path


@dataclass(frozen=True)
class Detection:
    name: str
    count: int | None
    box: tuple
    note: str


def recognize(image, script):
    with tempfile.TemporaryDirectory(prefix='mabinogi-ocr-') as temp:
        path = Path(temp) / 'capture.png'
        image.save(path)
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                 '-File', str(script), '-ImagePath', str(path)],
                                capture_output=True, encoding='utf-8', errors='replace',
                                timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or 'OCR failed')
        return json.loads(result.stdout.lstrip('\ufeff'))


def match_items(words, whitelist, size):
    # Group character tokens into full visual labels, never substring-match materials.
    names = {q.quest for q in whitelist} | {q.material for q in whitelist}
    rows = []
    for word in sorted(words, key=lambda w: (w['y'], w['x'])):
        center = word['y'] + word['h']/2
        group = next((r for r in rows if abs(r[0]['y']+r[0]['h']/2-center) < max(5,word['h']*.55)),None)
        if group is None:
            rows.append([word])
        else:
            group.append(word)
    detections = []
    sx, sy = size[0]/1280, size[1]/960
    proposals = []
    for row in rows:
        row.sort(key=lambda w:w['x'])
        groups = []
        for word in row:
            if not groups or word['x']-(groups[-1][-1]['x']+groups[-1][-1]['w']) > 18*sx:
                groups.append([word])
            else:
                groups[-1].append(word)
        for segment in groups:
            text = ''.join(w['text'] for w in segment).replace(' ','')
            matched = [name for name in names if name.replace(' ','') == text]
            if len(matched) != 1:
                continue
            x, y = segment[0]['x'], min(w['y'] for w in segment)
            right = max(w['x']+w['w'] for w in segment)
            bottom = max(w['y']+w['h'] for w in segment)
            nearby = [(n,w) for n,w in enumerate(words) if
                      x-8*sx <= w['x'] <= right+30*sx and 8*sy <= y-(w['y']+w['h']) <= 60*sy
                      and any(c.isdigit() for c in w['text'])]
            proposals.append((matched[0],(x,y,right,bottom),nearby))
    for name,box,nearby in proposals:
        count = None
        if len(nearby) == 1:
            n,word = nearby[0]
            owners = sum(any(candidate[0] == n for candidate in p[2]) for p in proposals)
            if owners == 1 and re.fullmatch(r'[0-9]+',word['text']):
                count = int(word['text'])
        detections.append(Detection(name,count,box,
            '候選配對，需人工核對' if count is not None else '數量不明：缺少、縮寫或配對不唯一'))
    return detections
