"""Single-window batch dashboard. All Tk updates run on the UI thread."""
import os,sys,time,json,queue,threading
from collections import Counter
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from .desktop_theme import apply_theme
from .version import APP_VERSION
from .whitelist import load
from .fixed_batch import fixed_batch,Journal
from .batch_ui import prepare_game, focus_game
from .player_messages import action_step, stop_message
from .input_control import Safety
from .ocr_session import OcrSession
from .automation import Runner,SkipMaterial
from .name_memory import NameMemory,NameReviewRequired
from .stock_ui import StockPanel

RESOURCES=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))

class App:
    def __init__(self,root):
        self.root=root;self.reset_requested=False;self.busy=False;self.closed=False;self.events=queue.Queue();self.log_lock=threading.Lock()
        self.current_item='';self.started=None;self.finished=None;self.action_name='';self.last_event=time.monotonic()
        self.data_dir=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'MabinogiSideHustle'
        try:hotkey=json.loads((self.data_dir/'settings.json').read_text(encoding='utf-8')).get('pause_hotkey','F8')
        except (OSError,ValueError,AttributeError):hotkey='F8'
        if not isinstance(hotkey,str) or hotkey not in {f'F{i}' for i in range(1,13)}:hotkey='F8'
        self.hotkey_name=hotkey
        self.safety=Safety(hotkey);self.last_safety_reason=self.safety.reason
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
        root.title(f'瑪奇M - 兼職小助手 v{APP_VERSION}')
        root.iconbitmap(str(RESOURCES/'assets/app.ico'))
        root.geometry('660x720');root.minsize(640,680)
        self.debug_visible=False
        root.option_add('*Font',('Microsoft JhengHei UI',10))
        style=ttk.Style(root);style.configure('Treeview',rowheight=24);style.configure('Heading.TLabel',font=('Microsoft JhengHei UI',16,'bold'))
        outer=ttk.Frame(root,padding=14);outer.pack(fill='both',expand=True)
        self.notice=ttk.Label(outer,text='注意事項: 遊戲解析度 1280 × 960｜建議將遊戲鏡頭控制轉為手動鏡頭',wraplength=610,foreground='#c62828',font=('Microsoft JhengHei UI',12,'bold'))
        self.notice.pack(anchor='w',pady=(5,10))
        bar=ttk.Frame(outer);bar.pack(fill='x')
        self.new_button=ttk.Button(bar,text='重置',command=self.new_batch);self.new_button.pack(side='left',padx=(0,6))
        self.pause_button=ttk.Button(bar,text=f'暫停／繼續（{hotkey}）',command=self.pause);self.pause_button.pack(side='left')
        self.debug_button=ttk.Button(bar,text='顯示除錯紀錄',command=self.toggle_debug);self.debug_button.pack(side='right',padx=6)
        self.hotkey_var=tk.StringVar(value=hotkey)
        self.hotkey_selector=ttk.Combobox(bar,textvariable=self.hotkey_var,values=[f'F{i}' for i in range(1,13)],width=3,state='readonly')
        self.hotkey_selector.pack(side='left',padx=4)
        self.hotkey_selector.bind('<<ComboboxSelected>>',self.change_hotkey)
        self.status=tk.StringVar(value='待開始：按「開始領取」後，將自動切回遊戲。')
        self.summary=tk.StringVar()
        self.withdraw_progress=ttk.Progressbar(outer,maximum=19)  # Unmapped; keep progress bookkeeping unchanged.
        details=ttk.LabelFrame(outer,text='目前作業',padding=4);details.pack(fill='x',pady=(0,6))
        body=ttk.Panedwindow(outer,orient='horizontal');self.body=body;body.pack(fill='both',expand=True)
        self.tabs=ttk.Notebook(body);body.add(self.tabs,weight=1)
        left=ttk.Frame(self.tabs,padding=6);quest_panel=ttk.Frame(self.tabs,padding=6)
        self.tabs.add(left,text='素材領取');self.tabs.add(quest_panel,text='任務交付')
        self.quest_panel=quest_panel;self.withdraw_panel=left
        ttk.Label(left,text='注意事項: 領取前開啟「公用保管箱 → 全部」',foreground='#DEC29A').pack(anchor='w',pady=(0,6))
        self.withdraw_button=ttk.Button(left,text='開始／繼續領取',command=lambda:self.start('withdraw'))
        self.withdraw_button.pack(anchor='w',pady=(0,6))
        right=ttk.LabelFrame(body,text='除錯紀錄',padding=8);self.debug_panel=right
        self.quest_summary=tk.StringVar()
        ttk.Label(quest_panel,textvariable=self.quest_summary).pack(anchor='w')
        self.board_check=ttk.Label(quest_panel,text='交任務前請先前往佈告欄並關閉對話視窗',foreground='#DEC29A',wraplength=600)
        self.board_check.pack(anchor='w',fill='x',pady=(4,6))
        self.quest_button=ttk.Button(quest_panel,text='開始／繼續交付',command=lambda:self.start('quests'))
        self.quest_button.pack(anchor='w',pady=(0,6))
        quest_panel.bind('<Configure>',lambda event:self.board_check.configure(wraplength=max(220,event.width-20)))
        hint=ttk.Frame(quest_panel);hint.pack(anchor='w',pady=4)
        for text,color in [('點選每列「',None),('−','#F07178'),('／',None),('＋','#78C69B'),('」調整交付次數；0 將會被略過',None)]:
            label=ttk.Label(hint,text=text)
            if color:label.configure(foreground=color)
            label.pack(side='left')
        self.quest_amount=tk.StringVar(value='3');self.quest_editor=None;self.quest_editor_row=None
        frame=ttk.Frame(quest_panel);frame.pack(fill='both',expand=True)
        self.quest_tree=ttk.Treeview(frame,columns=('quest','planned','done','left','minus','plus'),show='headings',height=6,selectmode='browse')
        for key,title,width in [('quest','任務',270),('planned','預計',55),('done','已完成',60),('left','剩餘',55),('minus','−',26),('plus','＋',26)]:
            self.quest_tree.heading(key,text=title);self.quest_tree.column(key,width=width,minwidth=26 if key in ('minus','plus') else 30,stretch=key=='quest',anchor='w' if key=='quest' else 'center')
        self.quest_tree.pack(side='left',fill='both',expand=True)
        quest_scroll=ttk.Scrollbar(frame,orient='vertical',command=self.scroll_quest_table)
        quest_scroll.pack(side='right',fill='y');self.quest_tree.configure(yscrollcommand=quest_scroll.set)
        self.quest_tree.tag_configure('active',background='#fff1c9')
        for i,q in enumerate(self.quests):self.quest_tree.insert('','end',iid=str(i),values=(q.quest,3,0,3,'−','＋'))
        self.quest_tree.bind('<Button-1>',self.adjust_quest_count)
        self.quest_tree.bind('<MouseWheel>',lambda event:self.commit_quest_edit())
        self.quest_tree.bind('<Configure>',lambda event:self.commit_quest_edit())
        self.tree=ttk.Treeview(left,columns=('name','quantity','state'),show='headings',height=6,selectmode='browse')
        for key,title,width in [('name','素材',150),('quantity','領取量',65),('state','進度',160)]:
            self.tree.heading(key,text=title);self.tree.column(key,width=width,minwidth=55)
        self.tree.tag_configure('active',background='#fff1c9');self.tree.tag_configure('done',foreground='#28724c')
        self.tree.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(left,orient='vertical',command=self.tree.yview);scroll.pack(side='right',fill='y');self.tree.configure(yscrollcommand=scroll.set)
        for i,item in enumerate(self.batch.materials):self.tree.insert('','end',iid=str(i),values=(item.name,item.quantity,'待領取'))
        self.item_text=tk.StringVar(value='目前項目：—');self.step=tk.StringVar(value='步驟：待開始');self.elapsed=tk.StringVar(value='耗時：—')
        self.action_progress=tk.StringVar()
        self.action_progress_label=ttk.Label(details,textvariable=self.action_progress)
        self.item_label=ttk.Label(details,textvariable=self.item_text,font=('Microsoft JhengHei UI',11,'bold'),wraplength=480)
        self.item_label.pack(anchor='w')
        ttk.Label(details,textvariable=self.step,wraplength=480).pack(anchor='w',fill='x',pady=4)
        ttk.Label(details,textvariable=self.elapsed).pack(anchor='w')
        self.stop_reason=tk.StringVar(value='')
        ttk.Label(details,textvariable=self.stop_reason,foreground='#a03224',wraplength=480).pack(anchor='w',fill='x',pady=2)
        def resize_details(event):
            for widget in details.winfo_children():
                if widget.winfo_class()=='TLabel':widget.configure(wraplength=max(180,event.width-20))
        details.bind('<Configure>',resize_details)
        debug_actions=ttk.Frame(right);debug_actions.pack(fill='x',pady=(0,4))
        ttk.Button(debug_actions,text='複製全部',command=self.copy_debug).pack(side='left')
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
        self.footer=tk.StringVar(value=f'{self.hotkey_name}：'+('就緒' if self.safety.hotkey_ok else '不可用，請關閉舊版助手後重開')+'｜紀錄只存本機')
        self.log(self.footer.get())
        self.log(f'紀錄檔：{self.report}')
        self.footer.trace_add('write',lambda *_:self.log(self.footer.get()))
        self.stock_panel=StockPanel(self,RESOURCES)
        self.theme=apply_theme(self)
        root.protocol('WM_DELETE_WINDOW',self.close)
        if load_error:self.fail('無法載入批次進度：'+load_error)
        else:
            self.log('已建立新批次：素材 0/19，交付 0/57。舊紀錄已封存。')
        self.safety.on_hotkey=lambda event:self.emit('hotkey',event)
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
            self.body.add(self.debug_panel,weight=2)
            self.theme.resize(expanded=True)
            self.debug_button.configure(text='隱藏除錯紀錄')
        else:
            self.body.forget(self.debug_panel)
            self.theme.resize(expanded=False)
            self.debug_button.configure(text='顯示除錯紀錄')

    def start_timing(self, name):
        self.started=self.last_event=time.monotonic()
        self.finished=None;self.action_name=name
        self.elapsed.set(f'耗時：{name} 00:00（執行中）')

    def update_timing(self):
        if self.started is None:return
        endpoint=self.finished if self.finished is not None else time.monotonic()
        seconds=max(0,int(endpoint-self.started))
        minutes,seconds=divmod(seconds,60)
        state=('已暫停' if self.safety.user_paused is True else '執行中') if self.finished is None else '已結束'
        self.elapsed.set(f'耗時：{self.action_name} {minutes:02d}:{seconds:02d}（{state}）')

    def emit(self,kind,value):
        if kind in ('done','error'):
            self.events.put(('action_finished',time.monotonic()))
        if kind=='log':
            value=f'{time.strftime("%H:%M:%S")}  {value}'
            with self.log_lock:
                with self.report.open('a',encoding='utf-8') as f:f.write(value+'\n')
        self.events.put((kind,value))
    def log(self,message):self.emit('log',message)
    def fail(self,message):
        self.status.set('已停止，請查看停止原因。');self.stop_reason.set('停止原因：'+stop_message(message));self.log('停止：'+message)
    def pending_description(self):
        p=self.journal.data['pending']
        if p['kind']=='withdraw':
            amount=next(x.quantity for x in self.batch.materials if x.name==p['value'])
            return f"領取 {p['value']} × {amount} 的結果未確認。請核對是否已轉入背包，避免重複領取。"
        index=p['value']['index'] if p['kind']=='activate' else p['value']
        q=self.batch.completions[index]
        action='啟用' if p['kind']=='activate' else '交付'
        return f'{action} {q.quest}（第 {q.ordinal}/{sum(x.quest==q.quest for x in self.batch.completions)} 次）結果未確認。交付成功須包含通關畫面已關閉、回報追蹤消失。'
    def refresh(self):
        self.stock_panel.refresh()
        if self.journal:self.batch=self.journal.batch
        data=self.journal.data if self.journal else {'withdrawn':[],'completed':0,'pending':None,'active':None}
        count=len(data['withdrawn']);total=len(self.batch.completions);self.summary.set(f'素材領取 {count}/19 種     任務交付 {data["completed"]}/{total} 次｜剩餘 {total-data["completed"]} 次')
        if self.busy and self.action_name in ('素材領取','任務交付'):
            text=(f'素材領取 {count}/19 種' if self.action_name=='素材領取' else
                  f'任務交付 {data["completed"]}/{total} 次｜剩餘 {total-data["completed"]} 次')
            self.action_progress.set(text)
            self.action_progress_label.pack(anchor='w',before=self.item_label)
        else:
            self.action_progress.set('');self.action_progress_label.pack_forget()
        self.withdraw_progress['value']=count
        pending=data['pending'];ready=not self.busy and self.journal is not None and not pending and self.name_review is None and self.safety.hotkey_ok
        self.withdraw_button['state']='normal' if ready and count+len(data.get('skipped',{}))<19 else 'disabled'
        self.quest_button['state']='normal' if ready else 'disabled'
        self.pause_button['state']='normal' if self.busy else 'disabled'
        suspended=self.safety.user_paused is True
        self.pause_button['text']=f'{"繼續" if suspended else "暫停"}（{self.hotkey_name}）'
        self.hotkey_selector['state']='disabled' if self.busy else 'readonly'
        self.new_button['state']='normal' if self.journal and (not self.busy or suspended) else 'disabled'
        for i,item in enumerate(self.batch.materials):
            done=item.name in data['withdrawn'];active=item.name==self.current_item and not done
            state=('已手動補領' if item.name in data.get('manual',[]) else '已領取') if done else (('送出中' if self.busy else '輸入中斷') if pending and pending['kind']=='withdraw' and pending['value']==item.name else ('處理中' if active and self.busy else ('已停在此項' if active else '待領取')))
            if item.name in data.get('skipped',{}):state='待手動補領'
            values=(item.name,item.quantity,state)
            if tuple(self.tree.item(str(i),'values'))!=tuple(map(str,values)):self.tree.item(str(i),values=values)
            self.tree.item(str(i),tags=('done',) if done else ('active',) if active else ())
        planned=Counter(q.quest for q in self.batch.completions)
        completed=Counter(q.quest for q in self.batch.completions[:data['completed']])
        self.quest_summary.set(f'預計 {total} 次｜已完成 {data["completed"]} 次｜剩餘 {total-data["completed"]} 次')
        editable=not self.busy and self.journal is not None and not pending and not data['active']
        if not editable:self.cancel_quest_edit()
        for i,q in enumerate(self.quests):
            values=(q.quest,planned[q.quest],completed[q.quest],planned[q.quest]-completed[q.quest],'−' if editable else '', '＋' if editable else '')
            if tuple(self.quest_tree.item(str(i),'values'))!=tuple(map(str,values)):self.quest_tree.item(str(i),values=values)
            self.quest_tree.item(str(i),tags=('active',) if q.quest==self.current_item else ())
        skipped=data.get('skipped',{})
        names=[m.name for m in self.batch.materials if m.name in skipped]
        rows=[f'{m.name} × {m.quantity}｜{skipped[m.name]}' for m in self.batch.materials if m.name in skipped]
        if tuple(self.manual_list.get(0,'end'))!=tuple(rows):
            self.manual_list.delete(0,'end')
            for row in rows:self.manual_list.insert('end',row)
        self.manual_names=names
        if skipped:self.manual_frame.pack(fill='x',pady=4,before=self.body)
        else:self.manual_frame.pack_forget()
        if pending and not self.busy:
            self.pending_text.set(self.pending_description());self.recovery.pack(fill='x',pady=6,before=self.body)
        else:self.recovery.pack_forget();self.reconciled.set(False)
        for button in (self.happened,self.not_happened):button['state']='normal' if pending and not self.busy and self.reconciled.get() else 'disabled'
        self.theme.stepper_colors.refresh()
    def can_edit_quest_count(self):
        return (not self.busy and self.journal is not None
                and not self.journal.data['pending'] and not self.journal.data['active'])

    def cancel_quest_edit(self):
        editor=self.quest_editor;self.quest_editor=None;self.quest_editor_row=None
        if editor is not None:editor.destroy()

    def adjust_quest_count(self,event):
        column=self.quest_tree.identify_column(event.x)
        row=self.quest_tree.identify_row(event.y)
        if column not in ('#5','#6') or not row:return
        if not self.can_edit_quest_count():return 'break'
        current=int(self.quest_tree.item(row,'values')[3])
        value=max(0,min(9999,current+(-1 if column=='#5' else 1)))
        self.quest_tree.selection_set(row)
        self.edit_quest_count(row,str(value))
        return 'break'

    def begin_quest_edit(self,event):
        row=self.quest_tree.identify_row(event.y)
        if self.quest_tree.identify_column(event.x)!='#4' or not row:return
        if not self.can_edit_quest_count():return
        if not self.commit_quest_edit():return
        box=self.quest_tree.bbox(row,'left')
        if not box:return
        self.quest_tree.selection_set(row);self.quest_editor_row=row
        self.quest_amount.set(self.quest_tree.item(row,'values')[3])
        self.quest_editor=ttk.Entry(self.quest_tree,textvariable=self.quest_amount,justify='center',style='QuestCount.TEntry')
        self.quest_editor.place(x=box[0],y=box[1],width=box[2],height=box[3])
        self.quest_editor.bind('<Return>',lambda event:self.commit_quest_edit())
        self.quest_editor.bind('<FocusOut>',lambda event:self.commit_quest_edit())
        self.quest_editor.bind('<Escape>',lambda event:self.cancel_quest_edit())
        self.quest_editor.focus_set();self.quest_editor.selection_range(0,'end')
        return 'break'  # Do not let Treeview's class binding steal editor focus.

    def scroll_quest_table(self,*args):
        self.commit_quest_edit();self.quest_tree.yview(*args)

    def commit_quest_edit(self):
        if self.quest_editor is None:return True
        row=self.quest_editor_row;raw=self.quest_amount.get().strip()
        self.cancel_quest_edit()
        return self.edit_quest_count(row,raw)

    def edit_quest_count(self,row,raw):
        if not self.can_edit_quest_count():return False
        try:
            if not raw.isascii() or not raw.isdecimal():raise ValueError('請輸入 0 至 9999 的整數。')
            remaining=Counter(q.quest for q in self.batch.completions[self.journal.data['completed']:])
            counts={q.quest:remaining[q.quest] for q in self.quests}
            name=self.quests[int(row)].quest
            if int(raw)==counts[name]:return True
            counts[name]=int(raw)
            self.journal.set_remaining(self.quests,counts);self.batch=self.journal.batch
            self.log(f'交付數量已修改：{name}，剩餘 {counts[name]} 次。')
            self.refresh();return True
        except Exception as error:self.fail(str(error));return False

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
        if not self.commit_quest_edit():return
        if not self.safety.hotkey_ok:self.fail('暫停熱鍵不可用；請關閉舊版助手或占用 F8 的程式後重開。');return
        try:self.journal.ready()
        except Exception as error:self.fail(str(error));return
        self.tabs.select(self.quest_panel if stage=='quests' else self.withdraw_panel)
        self.busy=True;self.start_timing('素材領取' if stage=='withdraw' else '任務交付')
        self.stop_reason.set('');self.current_item='';self.item_text.set('目前項目：—');self.step.set('步驟：等待切回遊戲')
        self.status.set('倒數期間將自動切回遊戲；暫停熱鍵可立即暫停。');self.safety.prepare();self.refresh()
        def run():
            try:
                for remaining in (3,2,1):
                    self.emit('progress',{'step':f'{remaining} 秒後開始，正在切回遊戲','item':'','quantity':None})
                    if remaining==3:focus_game(self.safety)
                    if self.safety.cancelled.wait(1):raise RuntimeError(self.safety.reason)
                self.log('自動檢查遊戲視窗、前景及 1280 × 960 內容。')
                window=prepare_game(self.safety)
                with OcrSession(RESOURCES/'scripts/ocr.ps1',self.safety.cancelled.is_set) as session:
                    runner=Runner(window,self.safety,session,self.journal,self.quests,RESOURCES/'scripts/ocr.ps1',self.log,lambda event:self.emit('progress',event),name_memory=self.name_memory,on_name_review=self.review_name)
                    result=runner.withdrawal() if stage=='withdraw' else runner.quests()
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
            self.emit('review_resume',f'{remaining} 秒後繼續，將自動切回遊戲；請保留目前物品視窗。')
            if remaining==3:focus_game(self.safety)
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
            self.status.set('名稱已記住；倒數後自動切回遊戲，繼續目前步驟。');self.stop_reason.set('')
        review.accepted=accepted
        self.name_review=None;self.name_review_frame.pack_forget()
        review.answered.set();self.refresh()
    def clear_names(self):
        if self.busy:return
        try:
            self.name_memory.clear();self.log('已清除玩家確認的名稱記憶。')
        except Exception as error:self.fail(str(error))

    def change_hotkey(self,event=None):
        if self.busy:return
        name=self.hotkey_var.get()
        try:
            if not self.safety.rebind(name):raise RuntimeError('此熱鍵已被其他程式使用；保留原設定。')
            self.hotkey_name=name
            path=self.data_dir/'settings.json'
            try:settings=json.loads(path.read_text(encoding='utf-8'))
            except (OSError,ValueError):settings={}
            settings['pause_hotkey']=name
            path.write_text(json.dumps(settings,ensure_ascii=False),encoding='utf-8')
            self.log(f'暫停／繼續熱鍵：{name}')
        except Exception as error:self.hotkey_var.set(self.hotkey_name);self.fail(str(error))
        self.refresh()

    def pause(self):
        if not self.busy:return
        if self.safety.user_paused is True:
            try:
                window=focus_game(self.safety)
                if self.safety.hwnd is not None and window.hwnd!=self.safety.hwnd:raise RuntimeError('遊戲視窗已變更，無法繼續。')
                self.safety.resume(window)
                self.stop_reason.set('');self.step.set('步驟：繼續目前作業。')
            except Exception as error:self.fail(str(error))
        else:
            self.safety.suspend();self.step.set('步驟：已暫停，按相同熱鍵或「繼續」恢復。')
        self.refresh()
    def reconcile(self,happened):
        if self.busy or not self.journal or not self.reconciled.get():return
        try:
            description=self.pending_description();self.journal.reconcile(happened)
            self.log('人工核對：'+description+(' → 已成功' if happened else ' → 未發生'))
            self.status.set('中斷結果已記錄。可按對應階段繼續。');self.stop_reason.set('');self.reconciled.set(False);self.refresh()
        except Exception as error:self.fail(str(error))
    def new_batch(self):
        if self.busy and self.safety.user_paused is True:
            self.reset_requested=True;self.safety.pause('重置目前作業');return
        if self.busy or not self.journal:return
        try:
            self.cancel_quest_edit()
            self.batch=fixed_batch(self.quests)
            self.journal=Journal.fresh(self.journal.path,self.batch)
            self.quest_amount.set('3')
            self.name_review=None;self.name_review_frame.pack_forget()
            self.current_item='';self.started=None;self.finished=None
            self.item_text.set('目前項目：—');self.step.set('步驟：待開始');self.elapsed.set('耗時：—');self.stop_reason.set('')
            self.status.set('新批次已就緒：素材 0/19，交付 0/57。可開啟公用保管箱領取，或備齊素材後直接交付。')
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
                elif kind=='hotkey':
                    if value=='resume':self.pause()
                    elif self.busy:self.step.set('步驟：已暫停，按相同熱鍵或「繼續」恢復。')
                elif kind=='progress':
                    self.current_item=value['item'];self.item_text.set('目前項目：'+(f"{value['item']} × {value['quantity']}" if value['item'] else '—'))
                    self.step.set('步驟：'+('已暫停，按相同熱鍵或「繼續」恢復。' if self.safety.user_paused is True else action_step(value['step'],self.action_name).replace('F8',self.hotkey_name)))
                    if not self.safety.cancelled.is_set():self.status.set('執行中：'+value['step'])
                    if value['item']:
                        for i,item in enumerate(self.batch.materials):
                            if item.name==value['item']:self.tree.see(str(i));break
                        for i,quest in enumerate(self.quests):
                            if quest.quest==value['item']:self.quest_tree.see(str(i));break
                elif kind=='stock_result':self.stock_panel.set_result(value)
                elif kind=='name_review':
                    self.name_review=value
                    self.name_review_text.set(f'OCR 讀到「{value.observed}」，預期為「{value.expected}」。請查看遊戲物品提示，確定是同一素材嗎？此確認只記住名稱，不確認數量。')
                    self.name_review_frame.pack(fill='x',pady=6,before=self.body)
                    self.status.set('等待玩家核對名稱；遊戲輸入已暫停。');self.stop_reason.set(str(value))
                elif kind=='review_resume':self.status.set(value);self.step.set('步驟：'+value)
                elif kind=='action_finished':self.finished=value
                elif kind in ('done','error'):
                    self.name_review=None;self.name_review_frame.pack_forget()
                    self.busy=False
                    if kind=='error':self.fail(value)
                    else:self.status.set(value);self.step.set('步驟：作業結束，請查看結果。');self.stop_reason.set('');self.log(value)
        except queue.Empty:pass
        if self.safety.reason!=self.last_safety_reason:
            self.last_safety_reason=self.safety.reason
            if self.busy and self.safety.paused and self.safety.user_paused is not True and self.name_review is None:self.fail(self.safety.reason)
        if self.reset_requested and not self.busy and (not getattr(self,'worker',None) or not self.worker.is_alive()):
            self.reset_requested=False;self.new_batch()
        self.update_timing()
        self.refresh();self.after_id=self.root.after(100,self.poll)
    def close(self):
        if self.closed:return
        self.closed=True;self.safety.close()
        try:self.root.after_cancel(self.after_id)
        except (tk.TclError,AttributeError):pass
        self.log('關閉助手；紀錄已保留，下次啟動將建立新批次。');self.root.destroy()

def run():
    # Keep the Windows taskbar identity separate from other Python applications.
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('MabinogiSideHustle.Assistant')
    root=tk.Tk();App(root);root.mainloop()
