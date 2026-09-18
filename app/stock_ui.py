"""Stock-check tab; all widget updates run on Tk's thread."""
import copy
import threading
import time
import tkinter as tk
from tkinter import ttk
from .batch_ui import prepare_game, focus_game
from .desktop_theme import COLORS
from .ocr_session import OcrSession
from .stock_check import StockScanner, StockResult, requirements


class StockPanel:
    def __init__(self, app, resources):
        self.app, self.resources = app, resources
        self.result = StockResult()
        self.scanned_at = ''
        self.panel = ttk.Frame(app.tabs, padding=6)
        app.tabs.add(self.panel, text='庫存盤點')
        self.notice = ttk.Label(self.panel, text='注意事項: 盤點前開啟「公共保管箱 → 全部」', foreground=COLORS['warning'], wraplength=620)
        self.notice.pack(anchor='w', fill='x', pady=(0,8))
        def resize_labels(event):
            for widget in self.panel.winfo_children():
                if isinstance(widget,ttk.Label):widget.configure(wraplength=max(200,event.width-20))
        self.panel.bind('<Configure>', resize_labels)
        bar = ttk.Frame(self.panel)
        bar.pack(fill='x')
        ttk.Label(bar, text='交付循環：').pack(side='left')
        self.cycles = tk.StringVar(value='1')
        self.selector = ttk.Combobox(bar, textvariable=self.cycles, values=tuple(range(1,7)),
                                     width=3, state='readonly')
        self.selector.pack(side='left')
        self.selector.bind('<<ComboboxSelected>>', lambda event: self.render())
        self.button = ttk.Button(bar, text='盤點公用保管箱', command=self.start)
        self.button.pack(side='left', padx=8)
        ttk.Button(bar, text='複製盤點結果', command=self.copy).pack(side='right')
        ttk.Label(self.panel, text='1 循環＝白名單每種 3 次；僅統計公用保管箱，不含背包。', wraplength=640).pack(anchor='w', pady=4)
        self.status = tk.StringVar(value='開啟「公用保管箱 → 全部」後按盤點；開始後會自動切回遊戲。')
        ttk.Label(self.panel, textvariable=self.status, wraplength=640).pack(anchor='w', pady=4)
        frame = ttk.Frame(self.panel)
        frame.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(frame, columns=('material','required','stock','missing'),
                                show='headings', height=6)
        for key, title, width in [('material','素材',210),('required','需要',90),
                                  ('stock','已辨識庫存',120),('missing','還缺',100)]:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=65, anchor='w' if key=='material' else 'center')
        self.tree.pack(side='left', fill='both', expand=True)
        scroll = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        scroll.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.tag_configure('missing', foreground='#F3B3B3', background='#442C30')
        self.tree.tag_configure('unknown', foreground='#F0D49A', background='#443D2C')
        self.tree.tag_configure('enough', foreground='#A8DFB8', background='#254236')
        self.render()

    def refresh(self):
        enabled = not self.app.busy and self.app.safety.hotkey_ok
        self.button['state'] = 'normal' if enabled else 'disabled'
        self.selector['state'] = 'readonly' if not self.app.busy else 'disabled'

    def render(self):
        rows = self.result.rows(self.app.quests, int(self.cycles.get()))
        for name, required, stock, missing in rows:
            values=(name, required, stock, '待確認' if missing is None else missing)
            tag = 'unknown' if missing is None else 'enough' if missing == 0 else 'missing'
            if self.tree.exists(name):
                self.tree.item(name, values=values, tags=(tag,))
            else:
                self.tree.insert('', 'end', iid=name, values=values, tags=(tag,))
        uncertain = sum(row[3] is None for row in rows)
        note = '已辨識庫存僅計入確認數量；無法確認缺額時顯示「待確認」。'+ self.result.note + (f'｜{uncertain} 種缺額待確認。' if uncertain else '')
        if self.scanned_at: note += f'｜掃描時間 {self.scanned_at}（快照）'
        self.status.set(note)

    def set_result(self, result):
        newly_counted = [cell.name for key,cell in result.cells.items()
                         if cell.name and cell.count is not None and not cell.uncertain
                         and self.result.cells.get(key) != cell]
        self.result = result
        self.render()
        if newly_counted and self.tree.exists(newly_counted[-1]):
            self.tree.see(newly_counted[-1])
            self.tree.selection_remove(*self.tree.selection())

    def text(self):
        lines = [f'公用保管箱盤點｜{self.cycles.get()} 循環（每循環各任務 3 次）',
                 f'掃描時間：{self.scanned_at or "未掃描"}', self.result.note,
                 '已辨識庫存僅計入確認數量；無法確認缺額時顯示「待確認」。',
                 '素材\t需要\t已辨識庫存\t還缺']
        for name, required, stock, missing in self.result.rows(self.app.quests, int(self.cycles.get())):
            shortage = '待確認' if missing is None else missing
            lines.append(f'{name}\t{required}\t{stock}\t{shortage}')
        return '\n'.join(lines)

    def copy(self):
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(self.text())
        self.app.footer.set('已複製庫存盤點結果。')

    def start(self):
        app = self.app
        if app.busy: return
        if not app.safety.hotkey_ok:
            app.fail('暫停熱鍵不可用；無法開始盤點。')
            return
        try: requirements(app.quests, int(self.cycles.get()))
        except ValueError as error:
            app.fail(str(error))
            return
        cycles = int(self.cycles.get())
        # No journal.ready(), batch mutation, retrieval, or quest Runner here.
        self.result = StockResult()
        self.scanned_at = time.strftime('%Y-%m-%d %H:%M:%S')
        self.render()
        self.tree.yview_moveto(0)
        self.tree.selection_remove(*self.tree.selection())
        app.busy = True
        app.start_timing('庫存盤點')
        app.current_item = ''
        app.stop_reason.set('')
        app.safety.prepare()
        app.status.set('盤點：倒數期間自動切回遊戲；暫停熱鍵可立即暫停。')
        app.refresh()

        def progress(message):
            app.log(message)
            app.emit('progress', {'step':message, 'item':'', 'quantity':None})

        def publish(result):
            app.emit('stock_result', copy.deepcopy(result))

        def run():
            scanner = None
            try:
                for remaining in (3,2,1):
                    progress(f'盤點將於 {remaining} 秒後開始，正在切回遊戲。')
                    if remaining==3:focus_game(app.safety)
                    if app.safety.cancelled.wait(1):
                        raise RuntimeError(app.safety.reason)
                window = prepare_game(app.safety)
                with OcrSession(self.resources/'scripts/ocr.ps1', app.safety.cancelled.is_set) as session:
                    scanner = StockScanner(window, app.safety, session, app.quests, progress, publish)
                    result = scanner.run()
                progress(result.note)
                for name, needed, observed, missing in result.rows(app.quests, cycles):
                    app.log(f'盤點：{name}｜需要 {needed}｜已辨識 {observed}｜還缺 {missing if missing is not None else "待確認"}')
                app.safety.pause('庫存盤點已結束。')
                app.emit('done', '庫存盤點已結束，請查看「庫存盤點」；結果為本次快照。')
            except Exception as error:
                reason = app.safety.reason if app.safety.cancelled.is_set() and app.safety.paused else str(error)
                if scanner is None:
                    publish(StockResult(note='盤點未完成：'+reason))
                app.safety.pause(reason)
                app.emit('error', reason)
        app.worker = threading.Thread(target=run, daemon=True)
        app.worker.start()
