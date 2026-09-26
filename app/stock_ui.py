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
        self.collected = set()
        self.panel = ttk.Frame(app.tabs, padding=6)
        app.tabs.add(self.panel, text='庫存盤點')
        self.notice = ttk.Label(self.panel, text='盤點前請開啟保管箱；程式會切至公用保管箱並篩選「一般」。', foreground=COLORS['warning'], wraplength=620)
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
        self.selector.bind('<<ComboboxSelected>>', self.change_cycles)
        self.button = ttk.Button(bar, text='盤點公用保管箱', command=self.start)
        self.button.pack(side='left', padx=8)
        ttk.Button(bar, text='複製盤點結果', command=self.copy).pack(side='right')
        ttk.Label(self.panel, text='1 循環＝白名單每種 3 次；僅統計公用保管箱，不含背包。', wraplength=640).pack(anchor='w', pady=4)
        self.status = tk.StringVar(value='開啟「公用保管箱 → 全部」後按盤點；開始後會自動切回遊戲。')
        ttk.Label(self.panel, textvariable=self.status, wraplength=640).pack(anchor='w', pady=4)
        frame = ttk.Frame(self.panel)
        frame.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(frame, columns=('collected','material','required','stock','missing'),
                                show='headings', height=6)
        for key, title, width in [('collected','已備齊',58),('material','素材',155),('required','需要',65),
                                  ('stock','已辨識庫存',95),('missing','還缺',65)]:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=width, stretch=key=='material', anchor='w' if key=='material' else 'center')
        self.tree.bind('<Button-1>', self.click_collected)
        self.tree.bind('<space>', self.key_collected)
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
        uncertain = self.result.uncertain_materials(self.app.quests, int(self.cycles.get()))
        for name, required, stock, missing in rows:
            checked = name in self.collected
            values=('☑' if checked else '☐', name, required, stock, 0 if checked else missing)
            tag = 'enough' if checked or missing == 0 else 'unknown' if name in uncertain else 'missing'
            if self.tree.exists(name):
                self.tree.item(name, values=values, tags=(tag,))
            else:
                self.tree.insert('', 'end', iid=name, values=values, tags=(tag,))
        note = '依循環數計算還缺素材；補齊後點「已備齊」勾選，該列會變綠。'
        if self.scanned_at:
            note += f'\n上次盤點：{self.scanned_at}｜' + ('盤點完成' if self.result.complete else '盤點未完成')
            if uncertain: note += '；缺額依已辨識庫存估算，黃色列請核對。'
        else:
            note += '\n' + (self.result.note if self.result.note.startswith('盤點未開始：')
                            else '尚未完成本次盤點；盤點結束後可勾選。')
        self.status.set(note)

    def change_cycles(self, event=None):
        self.collected.clear()
        self.render()

    def toggle_collected(self, name):
        if self.app.busy or not self.scanned_at or not self.tree.exists(name):
            return
        if name in self.collected: self.collected.remove(name)
        else: self.collected.add(name)
        # ttk's selected background overrides row tags, hiding the green state.
        self.tree.selection_remove(*self.tree.selection())
        self.render()

    def click_collected(self, event):
        if self.tree.identify_region(event.x,event.y) == 'cell' and self.tree.identify_column(event.x) == '#1':
            name = self.tree.identify_row(event.y)
            if name: self.tree.focus(name)
            self.toggle_collected(name)
            return 'break'

    def key_collected(self, event):
        self.toggle_collected(self.tree.focus())
        return 'break'

    def set_result(self, result):
        newly_counted = [cell.name for key,cell in result.cells.items()
                         if cell.name and cell.count is not None and not cell.uncertain
                         and self.result.cells.get(key) != cell]
        self.result = result
        self.scanned_at = result.finished_at
        self.render()
        if newly_counted and self.tree.exists(newly_counted[-1]):
            self.tree.see(newly_counted[-1])
            self.tree.selection_remove(*self.tree.selection())

    def text(self):
        lines = [f'公用保管箱盤點｜{self.cycles.get()} 循環（每循環各任務 3 次）',
                 f'掃描時間：{self.scanned_at or "未掃描"}', self.result.note,
                 '缺額依已辨識庫存估算；已備齊為玩家手動確認，不改寫庫存。',
                 '素材\t需要\t已辨識庫存\t還缺\t已備齊\t辨識狀態']
        uncertain = self.result.uncertain_materials(self.app.quests, int(self.cycles.get()))
        for name, required, stock, missing in self.result.rows(self.app.quests, int(self.cycles.get())):
            shortage = 0 if name in self.collected else missing
            checked = '是（手動）' if name in self.collected else '否'
            confidence = '缺額估算，請核對' if name in uncertain else '已確認'
            lines.append(f'{name}\t{required}\t{stock}\t{shortage}\t{checked}\t{confidence}')
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
        self.scanned_at = ''
        self.collected.clear()
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
                result.finished_at = time.strftime('%Y-%m-%d %H:%M:%S')
                publish(result)
                progress(result.note)
                for name, needed, observed, missing in result.rows(app.quests, cycles):
                    app.log(f'盤點：{name}｜需要 {needed}｜已辨識 {observed}｜還缺 {missing if missing is not None else "待確認"}')
                app.safety.pause('庫存盤點已結束。')
                app.emit('done', '庫存盤點已結束，請查看「庫存盤點」；結果為本次快照。')
            except Exception as error:
                reason = app.safety.reason if app.safety.cancelled.is_set() and app.safety.paused else str(error)
                result = scanner.result if scanner is not None else StockResult()
                result.note = ('盤點未完成：' if scanner is not None else '盤點未開始：')+reason
                result.finished_at = time.strftime('%Y-%m-%d %H:%M:%S') if scanner is not None else ''
                publish(result)
                app.safety.pause(reason)
                app.emit('error', reason)
        app.worker = threading.Thread(target=run, daemon=True)
        app.worker.start()
