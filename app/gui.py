import os
from pathlib import Path
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import ImageTk, ImageDraw
from . import capture, recognition, whitelist
from .input_control import Safety

RESOURCES = Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))

class App:
    def __init__(self,root):
        self.root=root
        root.title('瑪奇 Mobile 助手 — 擷取與辨識原型')
        root.geometry('1150x850')
        root.minsize(1000,700)
        root.option_add('*Font', ('Microsoft JhengHei UI',10))
        ttk.Style(root).configure('.',font=('Microsoft JhengHei UI',10))
        self.safety=Safety()
        self.events=queue.Queue()
        self.generation=0
        self.busy=False
        self.image=None
        self.live_window=None
        self.validated=None
        self.words=[]
        self.quests=whitelist.load(RESOURCES/'app/default_whitelist.json')
        self.report_dir=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'MabinogiSideHustle/reports'
        self.report_dir.mkdir(parents=True,exist_ok=True)
        self.report=self.report_dir/time.strftime('%Y%m%d-%H%M%S.txt')
        self.status=tk.StringVar(value='初始暫停。F8 緊急停止；背景輸入：未驗證。')
        bar=ttk.Frame(root,padding=8)
        bar.pack(fill='x')
        for title,command in [('偵測遊戲',self.detect),('參考圖片',self.reference),('3 秒後唯讀擷取',self.live),('載入 Excel',self.load_whitelist),('辨識預覽',self.ocr),('暫停 / 取消',self.pause)]:
            ttk.Button(bar,text=title,command=command).pack(side='left',padx=3)
        setup=ttk.Frame(root,padding=8)
        setup.pack(fill='x')
        ttk.Button(setup,text='確認本次遊戲 UI 比例與內容',command=self.confirm_setup).pack(side='left')
        ttk.Button(setup,text='Start / Resume：單次 I 測試',command=self.input_test).pack(side='left',padx=8)
        ttk.Label(setup,text='每次輸入需單獨觸發；請先關閉聊天與對話。').pack(side='left')
        ttk.Label(root,textvariable=self.status,wraplength=1100,padding=8).pack(fill='x')
        self.canvas=tk.Canvas(root,background='#17212a',height=480)
        self.canvas.pack(fill='both',expand=True,padx=8)
        self.canvas.bind('<Configure>',lambda event:self.draw())
        self.tree=ttk.Treeview(root,columns=('name','count','box','note'),show='headings',height=7)
        for key,title,width in [('name','白名單名稱',240),('count','數量',80),('box','位置 x1,y1,x2,y2',220),('note','辨識狀態',400)]:
            self.tree.heading(key,text=title)
            self.tree.column(key,width=width)
        self.tree.pack(fill='x',padx=8,pady=8)
        ttk.Label(root,text=f'本機報告：{self.report_dir} | F8 '+('已就緒' if self.safety.hotkey_ok else '不可用，輸入停用')).pack(fill='x',padx=8)
        root.protocol('WM_DELETE_WINDOW',self.close)
        root.bind('<Configure>',lambda e:self.draw() if e.widget==root else None)
        self.last_reason=self.safety.reason
        self.log(f'Started; {len(self.quests)} whitelist rows; background input unverified')
        root.after(50,self.poll)

    def log(self,message):
        with self.report.open('a',encoding='utf-8') as file:
            file.write(f'{time.strftime("%H:%M:%S")} {message}\n')

    def set_status(self,message):
        self.status.set(message)
        self.log(message)

    def pause(self):
        self.generation+=1
        self.safety.pause()
        self.set_status('已暫停；取消待執行動作。重新測試需明確按 Start / Resume。')

    def poll(self):
        if self.safety.reason!=self.last_reason:
            self.last_reason=self.safety.reason
            if self.safety.paused:
                self.set_status(self.safety.reason)
        try:
            while True:
                token,callback,result,error=self.events.get_nowait()
                self.busy=False
                if token!=self.generation:
                    continue
                if error:
                    self.safety.pause(str(error))
                    self.set_status(str(error))
                else:
                    callback(result)
        except queue.Empty:
            pass
        self.root.after(50,self.poll)

    def work(self,function,callback):
        if self.busy:
            self.set_status('請等待目前辨識或測試結束。')
            return
        self.busy=True
        token=self.generation
        def execute():
            try:
                self.events.put((token,callback,function(),None))
            except Exception as error:
                self.events.put((token,callback,None,error))
        threading.Thread(target=execute,daemon=True).start()

    def window(self):
        windows=capture.detect()
        if len(windows)!=1:
            raise RuntimeError(f'找到 {len(windows)} 個候選視窗；請只保留一個遊戲視窗')
        return windows[0]

    def detect(self):
        try:
            window=self.window()
            self.set_status(f'{window.title} / {window.process} / client rect {window.rect}；尚未驗證 UI 比例')
        except Exception as error:
            self.set_status(str(error))

    def show_image(self,image,description,window=None):
        self.image,self.live_window=image,window
        self.validated=None
        self.words=[]
        self.tree.delete(*self.tree.get_children())
        self.set_status(description)
        self.draw()

    def reference(self):
        if self.busy:
            return
        path=filedialog.askopenfilename(filetypes=[('Images','*.png *.jpg *.jpeg *.bmp')])
        if path:
            try:
                image,note=capture.reference(path)
                self.show_image(image,note)
            except Exception as error:
                self.set_status(str(error))

    def live(self):
        if self.busy:
            return
        self.safety.prepare()
        self.set_status('3 秒內切到遊戲；擷取時請勿遮住遊戲內容。')
        def take():
            if self.safety.cancelled.wait(3):
                raise RuntimeError('擷取已取消')
            window=self.window()
            return capture.capture(window),window
        self.work(take,lambda result:self.show_image(result[0],'已擷取 1280 × 960 client area；請核對 UI 與邊界',result[1]))

    def confirm_setup(self):
        if not self.live_window or not self.image or self.image.size!=capture.BASELINE:
            self.set_status('先完成本次唯讀即時擷取；參考圖片不能啟用輸入。')
            return
        if messagebox.askyesno('確認本次設定','預覽是否完整顯示 1280 × 960 遊戲內容，沒有邊框、黑邊、其他視窗遮擋，且文字與圖示比例正確？'):
            self.validated=self.live_window
            self.set_status('本次設定已人工核對；輸入仍須按單次測試。')

    def load_whitelist(self):
        if self.busy:
            return
        path=filedialog.askopenfilename(filetypes=[('Excel','*.xlsx')])
        if path:
            try:
                self.quests=whitelist.load(path)
                self.tree.delete(*self.tree.get_children())
                self.set_status(f'已唯讀載入 {len(self.quests)} 筆；保留原始順序與名稱。')
            except Exception as error:
                self.set_status(f'白名單載入失敗，保留原設定：{error}')

    def ocr(self):
        if self.image is None:
            self.set_status('先載入參考圖片或擷取遊戲。')
            return
        image=self.image.copy()
        self.set_status('Windows OCR 辨識中；數量為候選配對，不能直接用於領取。')
        self.work(lambda:recognition.recognize(image,RESOURCES/'scripts/ocr.ps1'),self.show_words)

    def show_words(self,words):
        self.words=words
        self.tree.delete(*self.tree.get_children())
        detections=recognition.match_items(words,self.quests,self.image.size)
        for item in detections:
            self.tree.insert('','end',values=(item.name,item.count if item.count is not None else '不明',tuple(round(n) for n in item.box),item.note))
            self.log(f'{item.name}: count={item.count}; box={item.box}; {item.note}')
        self.set_status(f'OCR {len(words)} 個文字區塊；{len(detections)} 個白名單候選。橘框：全部 OCR；綠框：白名單名稱。不累加跨畫面數量。')
        self.draw()

    def draw(self):
        if self.image is None:
            return
        image=self.image.copy()
        draw=ImageDraw.Draw(image)
        for w in self.words:
            draw.rectangle((w['x'],w['y'],w['x']+w['w'],w['y']+w['h']),outline='#e7a040',width=2)
        for item in recognition.match_items(self.words,self.quests,image.size):
            draw.rectangle(item.box,outline='#42ff8c',width=3)
        image.thumbnail((max(100,self.canvas.winfo_width()),max(100,self.canvas.winfo_height())))
        self.photo=ImageTk.PhotoImage(image)
        self.canvas.delete('all')
        self.canvas.create_image(self.canvas.winfo_width()/2,self.canvas.winfo_height()/2,image=self.photo)

    def input_test(self):
        if self.busy:
            return
        if not self.validated or not self.safety.hotkey_ok:
            self.set_status('需先通過即時擷取、UI 人工核對與 F8 註冊。')
            return
        if not messagebox.askyesno('單次 I 測試','確定遊戲沒有聊天輸入、NPC 對話或交易視窗？\n3 秒內切回遊戲，僅送出一次 I。\n請人工確認背包開啟或關閉；關閉測試需另按一次。'):
            return
        window=self.validated
        self.safety.prepare()
        self.set_status('3 秒內切回遊戲。F8 或暫停可取消；不會自動重試。')
        def test():
            if self.safety.cancelled.wait(3):
                raise RuntimeError('輸入測試已取消')
            current=self.window()
            if current.hwnd!=window.hwnd or current.rect!=window.rect:
                raise RuntimeError('視窗已改變，請重新擷取與核對')
            capture.capture(current)
            self.safety.arm(current)
            self.safety.inventory_once(current)
            if self.safety.cancelled.wait(.6):
                raise RuntimeError(self.safety.reason)
            image=capture.capture(current)
            self.safety.pause('單次 I 已送出，已暫停；結果需要人工確認')
            return image,current
        self.work(test,lambda result:self.show_image(result[0],'單次 I 已送出；請檢查背包狀態。再次測試前重新確認本次 UI。',result[1]))

    def close(self):
        self.generation+=1
        self.safety.close()
        self.log('Closed. Completed quests: 0; remaining scrolls/shortages: not evaluated.')
        self.root.destroy()

def run():
    root=tk.Tk()
    App(root)
    root.mainloop()
