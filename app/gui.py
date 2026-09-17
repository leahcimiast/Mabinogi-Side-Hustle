"""Single-window batch dashboard. All Tk updates run on the UI thread."""
import os,sys,time,json,queue,threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from .desktop_theme import apply_theme
from .whitelist import load
from .fixed_batch import fixed_batch,Journal
from .batch_ui import prepare_game
from .input_control import Safety
from .ocr_session import OcrSession
from .automation import Runner,SkipMaterial
from .name_memory import NameMemory,NameReviewRequired

RESOURCES=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))

class App:
    def __init__(self,root):
        self.root=root;self.busy=False;self.closed=False;self.events=queue.Queue();self.log_lock=threading.Lock()
        self.current_item='';self.started=None;self.last_event=time.monotonic()
        self.safety=Safety();self.last_safety_reason=self.safety.reason
        self.quests=load(RESOURCES/'app/default_whitelist.json');self.batch=fixed_batch(self.quests)
        self.data_dir=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'MabinogiSideHustle'
        self.report_dir=self.data_dir/'reports';self.report_dir.mkdir(parents=True,exist_ok=True)
        self.report=self.report_dir/(time.strftime('%Y%m%d-%H%M%S')+f'-{time.time_ns()%1000000:06d}.txt')
        self.journal=None;load_error=None
        try:self.journal=Journal.fresh(self.data_dir/'fixed-batch.json',self.batch)
        except Exception as error:load_error=str(error)
        self.name_review=None;self.name_memory=None
        try:self.name_memory=NameMemory(self.data_dir/'name-memory.json',[m.name for m in self.batch.materials])
        except Exception as error:load_error='無法讀取名稱記憶：'+str(error)
        root.title('瑪奇M - 兼職小助手')
        root.geometry('660x720');root.minsize(640,680)
        self.debug_visible=False
        root.option_add('*Font',('Microsoft JhengHei UI',10))
        style=ttk.Style(root);style.configure('Treeview',rowheight=24);style.configure('Heading.TLabel',font=('Microsoft JhengHei UI',16,'bold'))
        outer=ttk.Frame(root,padding=14);outer.pack(fill='both',expand=True)
        self.notice=ttk.Label(outer,text='注意事項: 遊戲內容 1280 × 960｜領取前開啟「公用保管箱 → 全部」｜每種卷軸準備 3 張，庫存與負重要足夠。',wraplength=610,foreground='#c62828',font=('Microsoft JhengHei UI',12,'bold'))
        self.notice.pack(anchor='w',pady=(5,10))
        bar=ttk.Frame(outer);bar.pack(fill='x')
        self.new_button=ttk.Button(bar,text='新批次',command=self.new_batch);self.new_button.pack(side='left',padx=(0,6))
        self.withdraw_button=ttk.Button(bar,text='1  開始／繼續領取',command=lambda:self.start('withdraw'));self.withdraw_button.pack(side='left')
        self.quest_button=ttk.Button(bar,text='2  開始／繼續交付',command=lambda:self.start('quests'));self.quest_button.pack(side='left',padx=8)
        self.pause_button=ttk.Button(bar,text='暫停（F8）',command=self.pause);self.pause_button.pack(side='left')
        self.debug_button=ttk.Button(bar,text='顯示除錯紀錄',command=self.toggle_debug);self.debug_button.pack(side='right',padx=6)
        self.board_ready=tk.BooleanVar(value=False)
        self.board_check=ttk.Checkbutton(outer,text='交付前確認：已到佈告欄並關閉背包／對話，沒有其他佈告欄任務。',variable=self.board_ready)
        self.board_check.pack(anchor='w',pady=(8,5))
        self.status=tk.StringVar(value='待開始：按「開始領取」後，3 秒內切回遊戲。')
        ttk.Label(outer,textvariable=self.status,wraplength=610,font=('Microsoft JhengHei UI',11,'bold')).pack(anchor='w',fill='x',pady=4)
        self.summary=tk.StringVar();ttk.Label(outer,textvariable=self.summary).pack(anchor='w')
        self.withdraw_progress=ttk.Progressbar(outer,maximum=19);self.withdraw_progress.pack(fill='x',pady=(4,8))
        details=ttk.LabelFrame(outer,text='目前作業',padding=8);details.pack(fill='x',pady=(0,6))
        body=ttk.Panedwindow(outer,orient='horizontal');self.body=body;body.pack(fill='both',expand=True)
        left=ttk.LabelFrame(body,text='素材與批次進度',padding=6);right=ttk.LabelFrame(body,text='除錯紀錄',padding=8);self.debug_panel=right
        body.add(left,weight=1)
        self.tree=ttk.Treeview(left,columns=('name','quantity','state'),show='headings',height=12,selectmode='browse')
        for key,title,width in [('name','素材',150),('quantity','領取量',65),('state','進度',160)]:
            self.tree.heading(key,text=title);self.tree.column(key,width=width,minwidth=55)
        self.tree.tag_configure('active',background='#fff1c9');self.tree.tag_configure('done',foreground='#28724c')
        self.tree.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(left,orient='vertical',command=self.tree.yview);scroll.pack(side='right',fill='y');self.tree.configure(yscrollcommand=scroll.set)
        for i,item in enumerate(self.batch.materials):self.tree.insert('','end',iid=str(i),values=(item.name,item.quantity,'待領取'))
        self.item_text=tk.StringVar(value='目前項目：—');self.step=tk.StringVar(value='步驟：待開始');self.elapsed=tk.StringVar(value='')
        ttk.Label(details,textvariable=self.item_text,font=('Microsoft JhengHei UI',11,'bold'),wraplength=480).pack(anchor='w')
        ttk.Label(details,textvariable=self.step,wraplength=480).pack(anchor='w',fill='x',pady=4)
        ttk.Label(details,textvariable=self.elapsed).pack(anchor='w')
        self.stop_reason=tk.StringVar(value='')
        ttk.Label(details,textvariable=self.stop_reason,foreground='#a03224',wraplength=480).pack(anchor='w',fill='x',pady=6)
        def resize_details(event):
            for widget in details.winfo_children():
                if widget.winfo_class()=='TLabel':widget.configure(wraplength=max(180,event.width-20))
        details.bind('<Configure>',resize_details)
        ttk.Button(right,text='複製全部',command=self.copy_debug).pack(anchor='w',pady=(0,4))
        log_frame=ttk.Frame(right);log_frame.pack(fill='both',expand=True)
        self.debug=tk.Text(log_frame,wrap='word',height=15,width=48,state='disabled',font=('Microsoft JhengHei UI',10))
        self.debug.tag_configure('success',foreground='#145c2e',background='#d9f2df')
        self.debug.tag_configure('failure',foreground='#a01818',background='#ffe0e0')
        self.debug.pack(side='left',fill='both',expand=True)
        log_scroll=ttk.Scrollbar(log_frame,orient='vertical',command=self.debug.yview);log_scroll.pack(side='right',fill='y');self.debug.configure(yscrollcommand=log_scroll.set)
        self.name_review_frame=ttk.LabelFrame(outer,text='請玩家核對物品名稱',padding=8)
        self.name_review_text=tk.StringVar()
        ttk.Label(self.name_review_frame,textvariable=self.name_review_text,wraplength=600).pack(anchor='w')
        name_buttons=ttk.Frame(self.name_review_frame);name_buttons.pack(fill='x')
        ttk.Button(name_buttons,text='是，記住此名稱並繼續',command=lambda:self.answer_name(True)).pack(side='left')
        ttk.Button(name_buttons,text='不是／不確定，跳過此素材',command=lambda:self.answer_name(False)).pack(side='left',padx=6)
        ttk.Button(right,text='清除已記住的名稱',command=self.clear_names).pack(anchor='w',pady=4)
        self.recovery=ttk.LabelFrame(outer,text='中斷結果待核對',padding=8)
        self.pending_text=tk.StringVar();ttk.Label(self.recovery,textvariable=self.pending_text,wraplength=600).pack(anchor='w')
        self.reconciled=tk.BooleanVar(value=False)
        ttk.Checkbutton(self.recovery,text='我已查看遊戲並確認結果；不確定時不要選擇下方動作。',variable=self.reconciled).pack(anchor='w')
        recovery_bar=ttk.Frame(self.recovery);recovery_bar.pack(fill='x')
        self.happened=ttk.Button(recovery_bar,text='確認已成功',command=lambda:self.reconcile(True));self.happened.pack(side='left')
        self.not_happened=ttk.Button(recovery_bar,text='確認未發生',command=lambda:self.reconcile(False));self.not_happened.pack(side='left',padx=8)
        self.manual_frame=ttk.LabelFrame(outer,text='待手動補領（名稱、數量、原因）',padding=6)
        self.manual_list=tk.Listbox(self.manual_frame,height=3,exportselection=False)
        self.manual_list.pack(fill='x')
        self.manual_confirm=ttk.Button(self.manual_frame,text='已手動補足選取素材的全部數量',command=self.confirm_manual)
        self.manual_confirm.pack(anchor='w')
        self.footer=tk.StringVar(value=f'F8：'+('就緒' if self.safety.hotkey_ok else '不可用，請關閉舊版助手後重開')+'｜紀錄只存本機')
        ttk.Label(outer,textvariable=self.footer).pack(anchor='w',pady=(8,0))
        ttk.Label(outer,text=f'紀錄檔：{self.report}',wraplength=610).pack(anchor='w')
        self.theme=apply_theme(self)
        root.protocol('WM_DELETE_WINDOW',self.close)
        if load_error:self.fail('無法載入批次進度：'+load_error)
        else:
            self.log('已建立新批次：素材 0/19，交付 0/57。舊紀錄已封存。')
        self.refresh();self.after_id=root.after(100,self.poll)

    @staticmethod
    def debug_tag(value):
        message=value.partition('  ')[2] or value
        if message.startswith(('搜尋素材 |','已領取 |','領取確認：')):return 'success'
        if message.startswith(('待手動補領：','停止：')):return 'failure'
        return ''

    def copy_debug(self):
        try:
            with self.log_lock:
                text=self.report.read_text(encoding='utf-8') if self.report.exists() else ''
            self.root.clipboard_clear();self.root.clipboard_append(text)
            self.footer.set('已複製本次完整除錯紀錄到剪貼簿。')
        except (OSError,tk.TclError) as error:
            self.footer.set('複製失敗：'+str(error))

    def toggle_debug(self):
        self.debug_visible=not self.debug_visible
        if self.debug_visible:
            self.body.add(self.debug_panel,weight=1)
            self.theme.resize(expanded=True)
            self.debug_button.configure(text='隱藏除錯紀錄')
        else:
            self.body.forget(self.debug_panel)
            self.theme.resize(expanded=False)
            self.debug_button.configure(text='顯示除錯紀錄')

    def emit(self,kind,value):
        if kind=='log':
            value=f'{time.strftime("%H:%M:%S")}  {value}'
            with self.log_lock:
                with self.report.open('a',encoding='utf-8') as f:f.write(value+'\n')
        self.events.put((kind,value))
    def log(self,message):self.emit('log',message)
    def fail(self,message):
        self.status.set('已停止，請查看停止原因。');self.stop_reason.set('停止原因：'+message);self.log('停止：'+message)
    def pending_description(self):
        p=self.journal.data['pending']
        if p['kind']=='withdraw':
            amount=next(x.quantity for x in self.batch.materials if x.name==p['value'])
            return f"領取 {p['value']} × {amount} 的結果未確認。請核對是否已轉入背包，避免重複領取。"
        index=p['value']['index'] if p['kind']=='activate' else p['value']
        q=self.batch.completions[index]
        action='啟用' if p['kind']=='activate' else '交付'
        return f'{action} {q.quest}（第 {q.ordinal}/3 次）結果未確認。交付成功須包含通關畫面已關閉、回報追蹤消失。'
    def refresh(self):
        data=self.journal.data if self.journal else {'withdrawn':[],'completed':0,'pending':None,'active':None}
        count=len(data['withdrawn']);self.summary.set(f'素材領取 {count}/19 種     任務交付 {data["completed"]}/57 次')
        self.withdraw_progress['value']=count
        pending=data['pending'];ready=not self.busy and self.journal is not None and not pending and self.name_review is None and self.safety.hotkey_ok
        self.withdraw_button['state']='normal' if ready and count+len(data.get('skipped',{}))<19 else 'disabled'
        self.quest_button['state']='normal' if ready and count==19 and data['completed']<57 else 'disabled'
        self.pause_button['state']='normal' if self.busy else 'disabled'
        self.new_button['state']='normal' if self.journal and not self.busy else 'disabled'
        self.board_check['state']='disabled' if self.busy else 'normal'
        self.board_check['text']=('交付前確認：已到佈告欄旁並關閉背包／對話；將接續本批次已啟用的任務。' if data['active'] else '交付前確認：已到佈告欄並關閉背包／對話，沒有其他佈告欄任務。')
        for i,item in enumerate(self.batch.materials):
            done=item.name in data['withdrawn'];active=item.name==self.current_item and not done
            state=('已手動補領' if item.name in data.get('manual',[]) else '已領取') if done else ('結果待核對' if pending and pending['kind']=='withdraw' and pending['value']==item.name else ('處理中' if active and self.busy else ('已停在此項' if active else '待領取')))
            if item.name in data.get('skipped',{}):state='待手動補領'
            values=(item.name,item.quantity,state)
            if tuple(self.tree.item(str(i),'values'))!=tuple(map(str,values)):self.tree.item(str(i),values=values)
            self.tree.item(str(i),tags=('done',) if done else ('active',) if active else ())
        skipped=data.get('skipped',{})
        names=[m.name for m in self.batch.materials if m.name in skipped]
        rows=[f'{m.name} × {m.quantity}｜{skipped[m.name]}' for m in self.batch.materials if m.name in skipped]
        if tuple(self.manual_list.get(0,'end'))!=tuple(rows):
            self.manual_list.delete(0,'end')
            for row in rows:self.manual_list.insert('end',row)
        self.manual_names=names
        if skipped:self.manual_frame.pack(fill='x',pady=4,before=self.body)
        else:self.manual_frame.pack_forget()
        self.manual_confirm['state']='normal' if not self.busy and not pending else 'disabled'
        if pending:
            self.pending_text.set(self.pending_description());self.recovery.pack(fill='x',pady=6,before=self.body)
        else:self.recovery.pack_forget();self.reconciled.set(False)
        for button in (self.happened,self.not_happened):button['state']='normal' if pending and not self.busy and self.reconciled.get() else 'disabled'
    def confirm_manual(self):
        if self.busy or not self.journal or self.journal.data['pending']:return
        selection=self.manual_list.curselection()
        if not selection:return
        name=self.manual_names[selection[0]]
        try:
            self.journal.confirm_manual(name)
            self.log(f'玩家確認已手動補足：{name}')
            self.refresh()
        except Exception as error:self.fail(str(error))
    def start(self,stage):
        if self.busy or self.journal is None:return
        if not self.safety.hotkey_ok:self.fail('F8 不可用；請關閉舊版助手或占用 F8 的程式後重開。');return
        try:self.journal.ready()
        except Exception as error:self.fail(str(error));return
        if stage=='quests':
            if len(self.journal.data['withdrawn'])!=19:self.fail('本批次素材尚未全部領取。');return
            if not self.board_ready.get():self.fail('請先勾選交付前確認，再開始交付。');return
        self.busy=True;self.started=time.monotonic();self.last_event=self.started
        self.stop_reason.set('');self.current_item='';self.item_text.set('目前項目：—');self.step.set('步驟：等待切回遊戲')
        self.status.set('3 秒內切回遊戲；F8 可立即暫停。');self.safety.prepare();self.refresh()
        no_active=self.board_ready.get()
        def run():
            try:
                for remaining in (3,2,1):
                    self.emit('progress',{'step':f'{remaining} 秒後開始，請切回遊戲','item':'','quantity':None})
                    if self.safety.cancelled.wait(1):raise RuntimeError(self.safety.reason)
                self.log('自動檢查遊戲視窗、前景及 1280 × 960 內容。')
                window=prepare_game(self.safety)
                with OcrSession(RESOURCES/'scripts/ocr.ps1',self.safety.cancelled.is_set) as session:
                    runner=Runner(window,self.safety,session,self.journal,self.quests,RESOURCES/'scripts/ocr.ps1',self.log,lambda event:self.emit('progress',event),name_memory=self.name_memory,on_name_review=self.review_name)
                    result=runner.withdrawal() if stage=='withdraw' else runner.quests(no_active_confirmed=no_active)
                self.safety.pause(result);self.emit('done',result)
            except Exception as error:
                reason=self.safety.reason if self.safety.cancelled.is_set() and self.safety.paused else str(error)
                self.safety.pause(reason);self.emit('error',reason)
        self.worker=threading.Thread(target=run,daemon=True);self.worker.start()
    def review_name(self,review,window):
        # Worker stays at the same action; Tk handles the response on its own thread.
        review.answered=threading.Event();review.accepted=False
        reason=str(review);self.safety.pause(reason);self.emit('name_review',review)
        deadline=time.monotonic()+300
        while not review.answered.wait(.1):
            if self.closed or self.safety.reason!=reason:raise RuntimeError('名稱核對已取消')
            if time.monotonic()>deadline:raise RuntimeError('等待玩家核對名稱逾時；未領取。')
        if self.closed or self.safety.reason!=reason:raise RuntimeError('名稱核對已取消')
        self.safety.prepare()
        for remaining in (3,2,1):
            self.emit('review_resume',f'{remaining} 秒後繼續，請切回遊戲並保留目前物品視窗。')
            if self.safety.cancelled.wait(1):raise RuntimeError(self.safety.reason)
        checked=prepare_game(self.safety)
        if checked.hwnd!=window.hwnd:
            self.safety.pause('遊戲視窗已變更');raise RuntimeError('遊戲視窗已變更，未繼續。')
        if not review.accepted:raise SkipMaterial('玩家未確認物品名稱；未領取。')
        self.log('玩家確認後繼續目前步驟；重新擷取畫面及核對數量。')
    def answer_name(self,accepted):
        if self.name_review is None:return
        review=self.name_review
        if accepted:
            try:self.name_memory.remember(review.observed,review.expected)
            except Exception as error:self.fail(str(error));return
            self.log(f'玩家確認並記住名稱：{review.observed} → {review.expected}')
            self.status.set('名稱已記住；3 秒內切回遊戲，將繼續目前步驟。');self.stop_reason.set('')
        review.accepted=accepted
        self.name_review=None;self.name_review_frame.pack_forget()
        review.answered.set();self.refresh()
    def clear_names(self):
        if self.busy:return
        try:
            self.name_memory.clear();self.log('已清除玩家確認的名稱記憶。')
        except Exception as error:self.fail(str(error))

    def pause(self):
        self.safety.pause('使用者暫停');self.fail('使用者暫停；等待目前步驟停止後才能繼續。')
    def reconcile(self,happened):
        if self.busy or not self.journal or not self.reconciled.get():return
        try:
            description=self.pending_description();self.journal.reconcile(happened)
            self.log('人工核對：'+description+(' → 已成功' if happened else ' → 未發生'))
            self.status.set('中斷結果已記錄。可按對應階段繼續。');self.stop_reason.set('');self.reconciled.set(False);self.refresh()
        except Exception as error:self.fail(str(error))
    def new_batch(self):
        if self.busy or not self.journal:return
        try:
            self.journal=Journal.fresh(self.journal.path,self.batch)
            self.name_review=None;self.name_review_frame.pack_forget()
            self.board_ready.set(False);self.current_item='';self.started=None
            self.item_text.set('目前項目：—');self.step.set('步驟：待開始');self.elapsed.set('');self.stop_reason.set('')
            self.status.set('新批次已就緒：素材 0/19，交付 0/57。請開啟公用保管箱，再按開始領取。')
            self.log('已建立新批次；舊進度已封存。');self.refresh()
        except Exception as error:self.fail(str(error))
    def poll(self):
        if self.closed:return
        try:
            while True:
                kind,value=self.events.get_nowait();self.last_event=time.monotonic()
                if kind=='log':
                    self.debug.configure(state='normal');self.debug.insert('end',value+'\n',self.debug_tag(value))
                    if int(self.debug.index('end-1c').split('.')[0])>2000:self.debug.delete('1.0','200.0')
                    self.debug.see('end');self.debug.configure(state='disabled')
                elif kind=='progress':
                    self.current_item=value['item'];self.item_text.set('目前項目：'+(f"{value['item']} × {value['quantity']}" if value['item'] else '—'))
                    self.step.set('步驟：'+value['step'])
                    if not self.safety.cancelled.is_set():self.status.set('執行中：'+value['step'])
                    if value['item']:
                        for i,item in enumerate(self.batch.materials):
                            if item.name==value['item']:self.tree.see(str(i));break
                elif kind=='name_review':
                    self.name_review=value
                    self.name_review_text.set(f'OCR 讀到「{value.observed}」，預期為「{value.expected}」。請查看遊戲物品提示，確定是同一素材嗎？此確認只記住名稱，不確認數量。')
                    self.name_review_frame.pack(fill='x',pady=6,before=self.body)
                    self.status.set('等待玩家核對名稱；遊戲輸入已暫停。');self.stop_reason.set(str(value))
                elif kind=='review_resume':self.status.set(value)
                elif kind in ('done','error'):
                    self.name_review=None;self.name_review_frame.pack_forget()
                    self.busy=False;self.board_ready.set(False)
                    if kind=='error':self.fail(value)
                    else:self.status.set(value);self.stop_reason.set('');self.log(value)
        except queue.Empty:pass
        if self.safety.reason!=self.last_safety_reason:
            self.last_safety_reason=self.safety.reason
            if self.busy and self.safety.paused and self.name_review is None:self.fail(self.safety.reason)
        if self.started:
            self.elapsed.set(f'本次執行 {int(time.monotonic()-self.started)} 秒｜距上次回報 {int(time.monotonic()-self.last_event)} 秒' if self.busy else '本次作業已停止；紀錄與進度已保留。')
        self.refresh();self.after_id=self.root.after(100,self.poll)
    def close(self):
        if self.closed:return
        self.closed=True;self.safety.close()
        try:self.root.after_cancel(self.after_id)
        except (tk.TclError,AttributeError):pass
        self.log('關閉助手；紀錄已保留，下次啟動將建立新批次。');self.root.destroy()

def run():
    root=tk.Tk();App(root);root.mainloop()
