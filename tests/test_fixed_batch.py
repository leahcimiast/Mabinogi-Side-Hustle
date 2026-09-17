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
        self.runner.storage_top=Mock();self.runner.rest=Mock();self.runner.click=Mock();self.runner.key=Mock()
        self.screen=Mock();self.screen.storage.return_value=True;self.screen.quantity_dialog.return_value=True
        self.runner.screen=Mock(return_value=self.screen)
        self.runner.wait=Mock(return_value=self.screen)
        self.runner.vision.storage_names=Mock(return_value=[Label('鐵礦石',(250,350,340,390))])
        self.runner.vision.entered_quantity=Mock(return_value=60)
        self.runner.vision.storage_names_retry=Mock(return_value=[])
        self.runner.vision.tooltip_retry=Mock(return_value=[])
    def tearDown(self):self.temp.cleanup()
    def test_mismatched_field_never_confirms_transfer(self):
        self.runner.vision.entered_quantity.return_value=59
        self.runner.withdrawal()
        self.assertIn('鐵礦石',self.j.data['skipped'])
        self.assertIsNone(self.j.data['pending'])
        self.assertNotIn('鐵礦石',self.j.data['withdrawn'])
        self.assertNotIn(((960,902),),[c.args for c in self.runner.click.call_args_list])
    def test_transient_unreadable_quantity_retries_without_retyping(self):
        self.runner.vision.entered_quantity.side_effect=[None,None,60]
        self.runner.withdrawal()
        self.assertEqual(self.runner.vision.entered_quantity.call_count,3)
        self.safety.number.assert_called_once()
        self.assertEqual(sum(c.args==((960,902),) for c in self.runner.click.call_args_list),1)
    def test_persistent_unreadable_quantity_never_confirms(self):
        self.runner.vision.entered_quantity.return_value=None
        self.runner.withdrawal()
        self.assertIn('三次',self.j.data['skipped']['鐵礦石'])
        self.assertEqual(self.runner.vision.entered_quantity.call_count,3)
        self.assertNotIn(((960,902),),[c.args for c in self.runner.click.call_args_list])
        self.assertIsNone(self.j.data['pending'])
    def test_missing_title_cannot_use_matching_number(self):
        self.screen.item_title.return_value=None
        self.screen.tooltip_titles.return_value=[]
        with self.assertRaises(RuntimeError):self.runner.verify_quantity('箭花',60)
        self.runner.vision.entered_quantity.assert_not_called()
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
    def test_lost_confirmation_leaves_pending_for_manual_reconciliation(self):
        self.runner.wait.side_effect=[self.screen,RuntimeError('lost confirmation')]
        with self.assertRaises(RuntimeError):self.runner.withdrawal()
        self.assertEqual(self.j.data['pending']['kind'],'withdraw')
        with self.assertRaises(RuntimeError):self.runner.withdrawal()

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
            runner=Runner(Mock(),Mock(),Mock(),j,ENTRIES,Path('scripts/ocr.ps1'));runner.screen=Mock()
            with self.assertRaises(RuntimeError):runner.quests(no_active_confirmed=False)
            runner.screen.assert_not_called()
