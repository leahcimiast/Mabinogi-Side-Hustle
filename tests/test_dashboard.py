import tempfile,threading,unittest
from unittest.mock import Mock,patch
import tkinter as tk
from app.gui import App

class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.env=patch.dict('os.environ',{'LOCALAPPDATA':self.temp.name});self.env.start()
        self.safety_patch=patch('app.gui.Safety');self.safety=self.safety_patch.start().return_value
        self.safety.hotkey_ok=True;self.safety.reason='初始暫停';self.safety.paused=True;self.safety.cancelled=threading.Event()
        def pause(reason='使用者暫停'):
            self.safety.reason=reason;self.safety.paused=True;self.safety.cancelled.set()
        self.safety.pause.side_effect=pause;self.safety.prepare.side_effect=self.safety.cancelled.clear
        self.root=tk.Tk();self.root.withdraw();self.app=App(self.root)
    def tearDown(self):
        self.app.close();self.safety_patch.stop();self.env.stop();self.temp.cleanup()
    def widgets(self,w):
        for child in w.winfo_children():yield child;yield from self.widgets(child)
    def test_no_legacy_controls_or_extra_window(self):
        widgets=list(self.widgets(self.root))
        self.assertFalse(any(w.winfo_class() in ('Canvas','Toplevel') for w in widgets))
        texts=[w.cget('text') for w in widgets if w.winfo_class()=='TButton']
        for obsolete in ['偵測遊戲','參考圖片','3 秒後唯讀擷取','載入 Excel','辨識預覽','暫停 / 取消']:
            self.assertNotIn(obsolete,texts)
        self.assertEqual(len(self.app.tree.get_children()),19)
    def test_footer_information_is_only_in_debug_log(self):
        labels=[w for w in self.widgets(self.root) if w.winfo_class()=='TLabel']
        self.assertFalse(any(str(w.cget('textvariable'))==str(self.app.footer) for w in labels))
        self.assertFalse(any(str(w.cget('text')).startswith('紀錄檔：') for w in labels))
        self.app.footer.set('已複製庫存盤點結果。');self.app.poll()
        text=self.app.debug.get('1.0','end')
        self.assertIn('紀錄檔：',text)
        self.assertIn('紀錄只存本機',text)
        self.assertIn('已複製庫存盤點結果。',text)

    def test_progress_and_stop_reason_remain_visible(self):
        self.app.busy=True;self.safety.paused=False
        self.app.emit('progress',{'step':'核對输入的領取量','item':'鐵礦石','quantity':60})
        self.app.log('數量欄核對：要求 60；讀回 1')
        self.app.emit('error','鐵礦石：要求 60，讀回 1；未按下領取。')
        self.app.poll()
        self.assertIn('鐵礦石 × 60',self.app.item_text.get())
        self.assertIn('讀回 1',self.app.stop_reason.get())
        self.assertIn('數量欄核對',self.app.debug.get('1.0','end'))
        self.assertFalse(self.app.busy)
        self.app.poll();self.assertIn('讀回 1',self.app.stop_reason.get())
    def test_name_confirmation_keeps_worker_and_progress(self):
        from app.name_memory import NameReviewRequired
        review=NameReviewRequired('箭花','花');review.answered=threading.Event();review.accepted=False
        self.app.busy=True;self.app.journal.data['withdrawn']=['鐵礦石']
        self.app.emit('name_review',review);self.app.poll()
        self.assertTrue(self.app.busy)
        self.app.answer_name(True)
        self.assertTrue(review.answered.is_set());self.assertTrue(review.accepted)
        self.assertTrue(self.app.busy)
        self.assertEqual(self.app.journal.data['withdrawn'],['鐵礦石'])
        self.assertTrue(self.app.name_memory.matches('花','箭花'))
    def test_reject_name_does_not_remember(self):
        from app.name_memory import NameReviewRequired
        review=NameReviewRequired('箭花','花');review.answered=threading.Event();review.accepted=False
        self.app.emit('name_review',review);self.app.poll();self.app.answer_name(False)
        self.assertTrue(review.answered.is_set());self.assertFalse(review.accepted)
        self.assertFalse(self.app.name_memory.aliases)
    def test_name_review_worker_resumes_after_yes_without_restarting(self):
        from app.name_memory import NameReviewRequired
        review=NameReviewRequired('箭花','花');window=Mock();window.hwnd=42
        def emit(kind,value):
            if kind=='name_review':
                value.accepted=True;value.answered.set()
        self.app.emit=emit
        with patch('app.gui.focus_game'),patch('app.gui.prepare_game',return_value=window),patch.object(self.safety.cancelled,'wait',return_value=False):
            self.app.review_name(review,window)
        self.safety.prepare.assert_called_once()
    def test_f8_during_name_review_does_not_resume(self):
        from app.name_memory import NameReviewRequired
        review=NameReviewRequired('箭花','花')
        def emit(kind,value):
            if kind=='name_review':self.safety.pause('F8 緊急停止')
        self.app.emit=emit
        with patch('app.gui.focus_game'),patch('app.gui.prepare_game') as prepare:
            with self.assertRaises(RuntimeError):self.app.review_name(review,Mock())
            prepare.assert_not_called()
    def test_manual_shortfall_does_not_gate_quests(self):
        self.app.journal.data['withdrawn']=[m.name for m in self.app.batch.materials if m.name!='洋蔥']
        self.app.journal.skip('洋蔥','未找到')
        self.app.refresh()
        self.assertFalse(self.app.debug_visible)
        self.assertEqual(self.app.manual_frame.winfo_manager(),'pack')
        self.assertIn('洋蔥 × 30',self.app.manual_list.get(0))
        self.assertEqual(str(self.app.quest_button['state']),'normal')
        self.app.manual_list.selection_set(0);self.app.confirm_manual()
        self.assertIn('洋蔥',self.app.journal.data['manual'])
        self.assertEqual(str(self.app.quest_button['state']),'normal')
    def test_new_batch_precedes_withdraw_and_notice_is_emphasized(self):
        self.assertIs(self.app.withdraw_button.master,self.app.withdraw_panel)
        self.assertEqual(self.app.new_button.cget('text'),'重置')
        self.assertIs(self.app.board_check.master,self.app.quest_panel)
        self.assertTrue(self.app.notice.cget('text').startswith('注意事項:'))
        from app.desktop_theme import COLORS
        self.assertEqual(str(self.app.notice.cget('foreground')),COLORS['warning'])
        self.assertIn('12',str(self.app.notice.cget('font')))
    def test_copy_all_uses_full_report_not_truncated_widget(self):
        full='\n'.join(f'紀錄 {i}' for i in range(2100))
        self.app.report.write_text(full,encoding='utf-8')
        with patch.object(self.root,'clipboard_clear') as clear,patch.object(self.root,'clipboard_append') as append:
            self.app.copy_debug()
            clear.assert_called_once();append.assert_called_once_with(full)
        self.assertIn('完整',self.app.footer.get())
    def test_copy_failure_does_not_stop_worker(self):
        self.app.busy=True
        with patch.object(self.root,'clipboard_clear',side_effect=tk.TclError('clipboard busy')):
            self.app.copy_debug()
        self.assertTrue(self.app.busy);self.assertIn('複製失敗',self.app.footer.get())
    def test_search_and_result_log_colors(self):
        self.app.log('搜尋素材 | 洋蔥 × 30')
        self.app.log('未找到 洋蔥，繼續向下捲動（第 1 頁）')
        self.app.log('領取確認：洋蔥 × 30')
        self.app.log('待手動補領：羊毛 × 60；未找到')
        self.app.poll()
        def tagged(tag):
            ranges=self.app.debug.tag_ranges(tag)
            return ''.join(self.app.debug.get(ranges[i],ranges[i+1]) for i in range(0,len(ranges),2))
        self.assertIn('搜尋素材 | 洋蔥',tagged('success'))
        self.assertIn('領取確認：洋蔥',tagged('success'))
        self.assertIn('待手動補領：羊毛',tagged('failure'))
        self.assertNotIn('繼續向下捲動',tagged('failure'))
        self.assertFalse(self.app.debug_visible)
    def test_debug_toggle_keeps_log_and_progress(self):
        self.root.update_idletasks()
        self.assertFalse(self.app.debug_visible)
        self.assertNotIn(str(self.app.debug_panel),self.app.body.panes())
        self.app.log('hidden log');self.app.poll()
        self.app.toggle_debug();self.root.update_idletasks()
        self.assertIn(str(self.app.debug_panel),self.app.body.panes())
        self.assertIn('hidden log',self.app.debug.get('1.0','end'))
        self.app.toggle_debug();self.root.update_idletasks()
        self.assertNotIn(str(self.app.debug_panel),self.app.body.panes())
        self.assertEqual(len(self.app.tree.get_children()),19)
    def test_progress_counts_refresh_automatically(self):
        self.app.journal.data['withdrawn']=['鐵礦石'];self.app.journal.data['completed']=2
        self.app.poll()
        self.assertIn('1/19',self.app.summary.get());self.assertIn('2/57',self.app.summary.get())
        self.assertEqual(self.app.tree.item('0','values')[2],'已領取')
    def test_start_needs_no_old_capture_or_popup(self):
        with patch('app.gui.threading.Thread') as thread:
            self.app.start('withdraw')
            thread.return_value.start.assert_called_once()
        self.assertTrue(self.app.busy)
        self.assertEqual(str(self.app.new_button['state']),'disabled')
    def test_quest_stage_has_instruction_without_checkbox_gate(self):
        self.app.journal.data['withdrawn']=[x.name for x in self.app.batch.materials]
        with patch('app.gui.threading.Thread') as thread:
            self.app.start('quests');thread.return_value.start.assert_called_once()
        self.assertEqual(self.app.board_check.winfo_class(),'TLabel')
        self.assertEqual(self.app.board_check.cget('text'),'交任務前請先前往佈告欄並關閉對話視窗')
    def test_pending_panel_hidden_during_normal_transfer(self):
        self.app.busy=True
        self.app.journal.begin('withdraw','鐵礦石');self.app.refresh()
        self.assertEqual(self.app.recovery.winfo_manager(),'')
        self.assertIsNotNone(self.app.journal.data['pending'])
        self.app.busy=False;self.app.refresh()
        self.assertEqual(self.app.recovery.winfo_manager(),'pack')

    def test_pending_reconciliation_is_inline_and_explicit(self):
        self.app.journal.begin('withdraw','鐵礦石');self.app.refresh()
        self.assertEqual(self.app.recovery.winfo_manager(),'pack')
        self.app.reconcile(True);self.assertIsNotNone(self.app.journal.data['pending'])
        self.app.reconciled.set(True);self.app.reconcile(True)
        self.assertIsNone(self.app.journal.data['pending']);self.assertIn('鐵礦石',self.app.journal.data['withdrawn'])
        self.assertFalse(any(w.winfo_class()=='Toplevel' for w in self.widgets(self.root)))
    def test_new_batch_is_one_click_and_archives_pending(self):
        self.app.journal.data['withdrawn']=['鐵礦石'];self.app.journal.begin('withdraw','牛奶')
        self.app.new_batch()
        self.assertEqual(self.app.journal.data['withdrawn'],[])
        self.assertIsNone(self.app.journal.data['pending'])
        self.assertEqual(len(list((self.app.data_dir/'batch-history').glob('*.json'))),1)
    def test_new_batch_cannot_reset_running_worker(self):
        self.app.journal.data['withdrawn']=['鐵礦石'];self.app.busy=True
        self.app.new_batch();self.assertEqual(self.app.journal.data['withdrawn'],['鐵礦石'])
    def test_pause_preserves_current_material(self):
        self.app.current_item='鐵礦石';self.app.busy=True;self.safety.user_paused=False;self.app.pause()
        self.assertEqual(self.app.current_item,'鐵礦石');self.assertFalse(self.safety.cancelled.is_set())
        self.safety.suspend.assert_called_once()
        self.assertIn('已暫停',self.app.step.get())

    def test_resume_refocuses_without_starting_another_worker(self):
        import copy
        self.app.busy=True;self.safety.user_paused=True;self.safety.hwnd=42
        window=Mock(hwnd=42);before=copy.deepcopy(self.app.journal.data)
        with patch('app.gui.focus_game',return_value=window) as focus,patch('app.gui.threading.Thread') as thread:
            self.app.pause()
        focus.assert_called_once_with(self.safety)
        self.safety.resume.assert_called_once_with(window);thread.assert_not_called()
        self.assertEqual(self.app.journal.data,before)

    def test_rebind_persists_and_removed_manual_button_stays_absent(self):
        import json
        self.safety.rebind.return_value=True
        self.app.hotkey_var.set('F9');self.app.change_hotkey()
        self.assertEqual(json.loads((self.app.data_dir/'settings.json').read_text(encoding='utf-8'))['pause_hotkey'],'F9')
        self.assertIn('F9',self.app.pause_button.cget('text'))
        buttons=[w.cget('text') for w in self.widgets(self.root) if w.winfo_class()=='TButton']
        self.assertNotIn('已手動補足選取素材的全部數量',buttons)

    def test_reset_during_manual_pause_waits_for_worker_exit(self):
        self.app.busy=True;self.safety.user_paused=True
        self.app.journal.data['withdrawn']=['鐵礦石']
        self.app.new_batch()
        self.assertTrue(self.app.reset_requested)
        self.assertEqual(self.app.journal.data['withdrawn'],['鐵礦石'])
        self.app.worker=Mock();self.app.worker.is_alive.return_value=False
        self.app.busy=False;self.app.poll()
        self.assertFalse(self.app.reset_requested)
        self.assertEqual(self.app.journal.data['withdrawn'],[])

    def test_action_progress_is_scoped_and_hidden_when_idle_or_counting(self):
        self.app.busy=True
        for action,expected in [('素材領取','素材領取 0/19 種'),('任務交付','任務交付 0/57 次｜剩餘 57 次')]:
            self.app.action_name=action;self.app.refresh()
            self.assertEqual(self.app.action_progress.get(),expected)
            self.assertEqual(self.app.action_progress_label.winfo_manager(),'pack')
            self.assertIs(self.app.action_progress_label.master,self.app.item_label.master)
        self.app.action_name='庫存盤點';self.app.refresh()
        self.assertEqual(self.app.action_progress_label.winfo_manager(),'')
        self.app.action_name='任務交付';self.app.busy=False;self.app.refresh()
        self.assertEqual(self.app.action_progress_label.winfo_manager(),'')
        buttons=[w.cget('text') for w in self.widgets(self.root) if w.winfo_class()=='TButton']
        self.assertNotIn('清除已記住的名稱',buttons)

    def test_every_launch_starts_fresh(self):
        self.app.journal.data['withdrawn']=['鐵礦石','咻咻蘑菇','洋蔥'];self.app.journal.save()
        self.app.close();self.root=tk.Tk();self.root.withdraw();self.app=App(self.root)
        self.assertEqual(self.app.journal.data['withdrawn'],[])
        self.assertIn('0/19',self.app.summary.get())
        from app.version import APP_VERSION
        self.assertEqual(self.root.title(),f'瑪奇M - 兼職小助手 v{APP_VERSION}')
        texts=[str(w.cget('text')) for w in self.widgets(self.root) if w.winfo_class() in ('TLabel','TButton')]
        self.assertFalse(any('19 種素材領取' in t or t=='確認新批次' for t in texts))
        import json
        archives=list((self.app.data_dir/'batch-history').glob('*.json'))
        self.assertEqual(len(json.loads(archives[0].read_text(encoding='utf-8'))['withdrawn']),3)

    def test_fresh_batch_can_start_submission_without_retrieval(self):
        self.app.refresh()
        self.assertEqual(str(self.app.quest_button['state']),'normal')
        with patch('app.gui.threading.Thread') as thread:
            self.app.start('quests')
            thread.return_value.start.assert_called_once()
        self.assertEqual(self.app.journal.data['withdrawn'],[])

    def test_edit_remaining_and_new_batch_defaults(self):
        self.app.edit_quest_count('0','1')
        self.assertEqual(len(self.app.batch.completions),55)
        self.assertEqual(tuple(map(str,self.app.quest_tree.item('0','values')[1:4])),('1','0','1'))
        self.assertIn('55',self.app.quest_summary.get())
        self.app.new_batch()
        self.assertEqual(len(self.app.batch.completions),57)
        self.assertEqual(tuple(map(str,self.app.quest_tree.item('0','values')[1:4])),('3','0','3'))
    def test_edit_disabled_while_worker_running(self):
        self.app.busy=True;self.app.refresh()
        self.assertFalse(self.app.can_edit_quest_count())
        self.app.edit_quest_count('0','0')
        self.assertEqual(len(self.app.batch.completions),57)

    def test_stepper_changes_only_clicked_row_and_saves(self):
        from app.fixed_batch import Journal
        with patch.object(self.app.quest_tree,'identify_column',return_value='#6'),patch.object(self.app.quest_tree,'identify_row',return_value='1'):
            self.app.adjust_quest_count(Mock(x=1,y=1))
        self.assertEqual(self.app.quest_tree.item('0','values')[3],'3')
        self.assertEqual(self.app.quest_tree.item('1','values')[3],'4')
        self.assertEqual(len(Journal(self.app.journal.path,self.app.batch).batch.completions),58)
        self.assertIsNone(self.app.quest_editor)
    def test_stepper_stops_at_zero_and_locks_during_pending(self):
        with patch.object(self.app.quest_tree,'identify_column',return_value='#5'),patch.object(self.app.quest_tree,'identify_row',return_value='0'):
            for _ in range(5):self.app.adjust_quest_count(Mock(x=1,y=1))
        self.assertEqual(self.app.quest_tree.item('0','values')[3],'0')
        self.app.journal.begin('activate',{'index':0,'identity':None});self.app.refresh()
        with patch.object(self.app.quest_tree,'identify_column',return_value='#6'),patch.object(self.app.quest_tree,'identify_row',return_value='0'):
            self.app.adjust_quest_count(Mock(x=1,y=1))
        self.assertEqual(self.app.quest_tree.item('0','values')[3],'0')

    def test_adopted_quest_completion_updates_its_own_gui_row(self):
        wool=next(q for q in self.app.quests if q.material=='羊毛')
        self.app.journal.adopt_active(self.app.quests,wool.quest,'取得羊毛')
        self.app.journal.begin('complete',0);self.app.journal.confirm();self.app.refresh()
        row=str(self.app.quests.index(wool))
        self.assertEqual(self.app.quest_tree.item(row,'values')[1:4],('3','1','2'))
        self.assertEqual(self.app.quest_tree.item('0','values')[1:4],('3','0','3'))
        self.assertIs(self.app.batch,self.app.journal.batch)
    def test_empty_plan_can_start_detection_of_existing_active_quest(self):
        self.app.journal.set_remaining(self.app.quests,{q.quest:0 for q in self.app.quests})
        self.app.refresh();self.assertEqual(str(self.app.quest_button['state']),'normal')
        with patch('app.gui.threading.Thread') as thread:
            self.app.start('quests');thread.return_value.start.assert_called_once()
