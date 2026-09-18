import unittest,tempfile
from pathlib import Path
from unittest.mock import Mock,patch
from app.fixed_batch import fixed_batch,Journal
from app.whitelist import load
from app.automation import Runner
from app.flow_vision import Label

ENTRIES=load(Path(__file__).resolve().parents[1]/'app/default_whitelist.json')
class FixedBatchTests(unittest.TestCase):
    def test_nineteen_materials_fifty_seven_completions(self):
        batch=fixed_batch(ENTRIES)
        self.assertEqual(len(batch.materials),19);self.assertEqual(len(batch.completions),57)
        quantities={m.name:m.quantity for m in batch.materials}
        self.assertEqual(quantities['鐵礦石'],60);self.assertEqual(quantities['蜘蛛網'],30)
        self.assertEqual(quantities['煎蛋'],15);self.assertEqual(quantities['高級原木+'],60)
        self.assertEqual([x.ordinal for x in batch.completions[:3]],[1,2,3])
    def test_wrong_whitelist_size_rejected(self):
        with self.assertRaises(ValueError):fixed_batch(ENTRIES[:18])
    def test_pending_survives_restart_and_blocks_replay(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'progress.json';batch=fixed_batch(ENTRIES)
            j=Journal(p,batch);j.begin('withdraw','鐵礦石')
            restored=Journal(p,batch)
            with self.assertRaises(RuntimeError):restored.begin('withdraw','鐵礦石')
            restored.reconcile(True)
            self.assertEqual(Journal(p,batch).data['withdrawn'],['鐵礦石'])
    def test_activation_and_completion_are_separate(self):
        with tempfile.TemporaryDirectory() as d:
            j=Journal(Path(d)/'p.json',fixed_batch(ENTRIES));j.begin('activate',{'index':0,'identity':'取得鐵礦石'});j.confirm()
            self.assertEqual(j.data['completed'],0);self.assertIsNotNone(j.data['active'])
            j.begin('complete',0);j.reconcile(False)
            self.assertIsNotNone(j.data['active']);self.assertEqual(j.data['completed'],0)
            j.begin('complete',0);j.confirm()
            self.assertEqual(j.data['completed'],1);self.assertIsNone(j.data['active'])

class WithdrawalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.j=Journal(Path(self.temp.name)/'p.json',fixed_batch(ENTRIES))
        self.j.data['withdrawn']=[m.name for m in self.j.batch.materials[1:]]
        self.safety=Mock();self.runner=Runner(Mock(),self.safety,Mock(),self.j,ENTRIES,Path('scripts/ocr.ps1'))
        self.runner.wait_transfer_confirmation=Mock();self.runner.wait_transfer_prompt=Mock();self.runner.storage_top=Mock();self.runner.rest=Mock();self.runner.click=Mock();self.runner.key=Mock()
        self.screen=Mock();self.screen.storage.return_value=True;self.screen.quantity_dialog.return_value=True
        self.runner.screen=Mock(return_value=self.screen)
        self.runner.wait=Mock(return_value=self.screen)
        self.runner.vision.storage_names=Mock(return_value=[Label('鐵礦石',(250,350,340,390))])
        self.runner.vision.entered_quantity=Mock(return_value=60)
        self.runner.vision.storage_names_retry=Mock(return_value=[])
        self.runner.vision.tooltip_retry=Mock(return_value=[])
    def tearDown(self):self.temp.cleanup()
    def test_quantity_field_gets_focus_delay_before_typing(self):
        events=Mock()
        events.attach_mock(self.runner.click,'click')
        events.attach_mock(self.runner.rest,'rest')
        events.attach_mock(self.safety.number,'number')
        self.runner.withdrawal()
        from unittest.mock import call
        calls=events.mock_calls
        focus=calls.index(call.click((960,788)))
        self.assertEqual(calls[focus+1],call.rest(.5))
        self.assertEqual(calls[focus+2],call.number(self.runner.window,60))

    def test_transfer_does_not_read_back_number(self):
        self.runner.vision.entered_quantity.side_effect=AssertionError('numeric OCR must not run')
        self.runner.withdrawal()
        self.runner.vision.entered_quantity.assert_not_called()
        self.runner.wait_transfer_confirmation.assert_called_once()
        self.safety.click.assert_called_once_with(self.runner.window,960,902)
        self.assertIn('鐵礦石',self.j.data['withdrawn'])

    def test_unavailable_green_button_never_confirms(self):
        from app.automation import ScreenTimeout
        self.runner.wait_transfer_confirmation.side_effect=ScreenTimeout('button unavailable')
        self.runner.withdrawal()
        self.safety.click.assert_not_called()
        self.assertIsNone(self.j.data['pending'])
        self.assertNotIn('鐵礦石',self.j.data['withdrawn'])

    def test_missing_title_does_not_block_matching_number(self):
        self.screen.item_title.return_value=None
        self.screen.tooltip_titles.return_value=[]
        self.assertEqual(self.runner.verify_quantity('箭花',60),60)
        self.screen.item_title.assert_not_called()
        self.runner.vision.tooltip_retry.assert_not_called()
        self.runner.click.assert_not_called()
    def test_transient_dialog_failure_rechecks_same_frame_identity(self):
        self.screen.quantity_dialog.side_effect=[False,True]
        self.assertEqual(self.runner.verify_quantity('箭花',60),60)
        self.runner.vision.entered_quantity.assert_called_once()
        self.runner.click.assert_not_called()
    def test_confirmed_transfer_not_repeated(self):
        self.runner.withdrawal();calls=self.runner.click.call_count
        self.runner.withdrawal();self.assertEqual(self.runner.click.call_count,calls)
        self.assertIn('鐵礦石',self.j.data['withdrawn'])
    def test_missing_list_after_click_keeps_assumed_success_without_replay(self):
        from app.automation import ScreenTimeout
        self.runner.wait.side_effect=[self.screen,ScreenTimeout('list unavailable')]
        with self.assertRaisesRegex(ScreenTimeout,'list unavailable'):self.runner.withdrawal()
        self.assertIsNone(self.j.data['pending'])
        self.assertIn('鐵礦石',self.j.data['withdrawn'])
        self.assertNotIn('鐵礦石',self.j.data['skipped'])
        self.safety.click.assert_called_once_with(self.runner.window,960,902)
        self.runner.withdrawal()
        self.assertEqual(self.safety.click.call_count,1)

    def test_pause_after_dispatched_click_preserves_success(self):
        def pause_after_send(*args):
            if self.safety.click.called:raise RuntimeError('F8')
        self.runner.rest.side_effect=pause_after_send
        with self.assertRaisesRegex(RuntimeError,'F8'):self.runner.withdrawal()
        self.assertIn('鐵礦石',self.j.data['withdrawn'])
        self.assertIsNone(self.j.data['pending'])

    def test_failed_input_dispatch_does_not_mark_success(self):
        self.safety.click.side_effect=RuntimeError('input failed')
        with self.assertRaisesRegex(RuntimeError,'input failed'):self.runner.withdrawal()
        self.assertNotIn('鐵礦石',self.j.data['withdrawn'])


class QuestLoopTests(unittest.TestCase):
    def test_uncertain_submission_cannot_activate_next_scroll(self):
        with tempfile.TemporaryDirectory() as d:
            j=Journal(Path(d)/'p.json',fixed_batch(ENTRIES));j.data['withdrawn']=[m.name for m in j.batch.materials]
            j.data['active']={'index':0,'identity':'取得鐵礦石'}
            runner=Runner(Mock(),Mock(),Mock(),j,ENTRIES,Path('scripts/ocr.ps1'))
            runner.rest=Mock();runner.click=Mock();runner.key=Mock();runner.find_scroll=Mock()
            screen=Mock();screen.tracker.return_value=Label('取得鐵礦石',(1000,240,1150,265));screen.report.return_value=Label('回報任務',(1000,270,1150,290))
            screen.submission.return_value=True;screen.has.return_value=True;screen.submitted_ready.return_value=True
            runner.screen=Mock(side_effect=[screen,screen,RuntimeError('lost screen after submit')])
            with self.assertRaises(RuntimeError):runner.quests()
            self.assertEqual(j.data['pending']['kind'],'complete');self.assertEqual(j.data['completed'],0)
            runner.find_scroll.assert_not_called()
            with self.assertRaises(RuntimeError):runner.quests()
    def test_no_unknown_active_state_assumption(self):
        with tempfile.TemporaryDirectory() as d:
            j=Journal(Path(d)/'p.json',fixed_batch(ENTRIES));j.data['withdrawn']=[m.name for m in j.batch.materials]
            runner=Runner(Mock(),Mock(),Mock(),j,ENTRIES,Path('scripts/ocr.ps1'));runner.screen=Mock(side_effect=RuntimeError("game check reached"))
            with self.assertRaises(RuntimeError):runner.quests()
            runner.screen.assert_called_once()

    def test_submission_without_retrieval_reaches_game_checks(self):
        with tempfile.TemporaryDirectory() as d:
            j=Journal(Path(d)/'p.json',fixed_batch(ENTRIES))
            j.data['skipped']={'鐵礦石':'not found'}
            runner=Runner(Mock(),Mock(),Mock(),j,ENTRIES,Path('scripts/ocr.ps1'))
            runner.screen=Mock(side_effect=RuntimeError('game check reached'))
            with self.assertRaisesRegex(RuntimeError,'game check reached'):
                runner.quests()
            runner.screen.assert_called_once()
            self.assertEqual(j.data['withdrawn'],[])
            self.assertEqual(j.data['completed'],0)
