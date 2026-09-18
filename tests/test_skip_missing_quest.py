import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from app.fixed_batch import Journal,fixed_batch
from app.whitelist import load
from app.automation import Runner,MissingQuestScroll
ENTRIES=load(Path(__file__).resolve().parents[1]/'app/default_whitelist.json')
class SkipQuestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=fixed_batch(ENTRIES)
        self.j=Journal(Path(self.temp.name)/'batch.json',self.base)
    def tearDown(self):self.temp.cleanup()
    def test_skip_preserves_completed_and_other_quantities_on_reload(self):
        self.j.data['completed']=1
        self.assertEqual(self.j.skip_missing_quest(ENTRIES[0].quest,'missing'),2)
        loaded=Journal(self.j.path,self.base)
        self.assertEqual(loaded.data['completed'],1)
        self.assertEqual(loaded.batch.completions[0].quest,ENTRIES[0].quest)
        self.assertEqual(loaded.batch.completions[1].quest,ENTRIES[1].quest)
        self.assertEqual(len(loaded.batch.completions),55)
    def test_failed_save_rolls_back(self):
        with patch.object(self.j,'save',side_effect=OSError('disk')):
            with self.assertRaises(OSError):self.j.skip_missing_quest(ENTRIES[0].quest,'missing')
        self.assertEqual(self.j.batch,self.base);self.assertNotIn('skipped_quests',self.j.data)
    def test_pending_and_active_cannot_skip(self):
        for field,value in [('pending',{'kind':'activate'}),('active',{'index':0})]:
            self.j.data[field]=value
            with self.assertRaises(RuntimeError):self.j.skip_missing_quest(ENTRIES[0].quest,'missing')
            self.j.data[field]=None
    def test_missing_scroll_keeps_inventory_for_next_kind(self):
        r=Runner(Mock(),Mock(),Mock(),self.j,ENTRIES,None)
        world=Mock();world.world.return_value=True;world.report.return_value=None;world.tracker.return_value=None
        r.screen=Mock(return_value=world);r.key=Mock();r.click=Mock();r.wait=Mock(return_value=world)
        r.find_scroll=Mock(side_effect=[MissingQuestScroll('missing'),RuntimeError('next reached')])
        with self.assertRaisesRegex(RuntimeError,'next reached'):r.quests()
        self.assertEqual(r.find_scroll.call_args_list[1].args[0].quest,ENTRIES[1].quest)
        self.assertEqual(self.j.data['completed'],0);self.assertEqual(len(self.j.batch.completions),54)
        r.key.assert_not_called();r.click.assert_not_called()
        r.screen.assert_called_once();self.assertTrue(r.inventory_ready)
    def test_other_failure_does_not_skip(self):
        r=Runner(Mock(),Mock(),Mock(),self.j,ENTRIES,None)
        world=Mock();world.world.return_value=True;world.report.return_value=None;world.tracker.return_value=None
        r.screen=Mock(return_value=world);r.find_scroll=Mock(side_effect=RuntimeError('F8'))
        with self.assertRaisesRegex(RuntimeError,'F8'):r.quests()
        self.assertEqual(len(self.j.batch.completions),57)

    def test_start_on_material_inventory_does_not_press_i(self):
        r=Runner(Mock(),Mock(),Mock(),self.j,ENTRIES,None)
        initial=Mock();initial.world.return_value=False;initial.report.return_value=None
        inventory=Mock();inventory.find.return_value=Mock(point=(954,918))
        r.screen=Mock(return_value=initial);r.inventory_category_screen=Mock(return_value=inventory)
        r.key=Mock();r.click=Mock();r.rest=Mock()
        r.find_scroll=Mock(side_effect=RuntimeError('search reached'))
        with self.assertRaisesRegex(RuntimeError,'search reached'):r.quests()
        r.key.assert_not_called();r.safety.drag.assert_called_once()
        r.click.assert_any_call((1189,140));self.assertTrue(r.inventory_ready)
        initial.report.assert_called_once()
    def test_unknown_start_screen_never_opens_or_skips_quests(self):
        r=Runner(Mock(),Mock(),Mock(),self.j,ENTRIES,None)
        initial=Mock();initial.world.return_value=False;initial.report.return_value=None
        inventory=Mock();inventory.find.return_value=None
        r.screen=Mock(return_value=initial);r.inventory_category_screen=Mock(return_value=inventory)
        r.key=Mock();r.find_scroll=Mock()
        with self.assertRaisesRegex(RuntimeError,'關閉對話'):r.quests()
        r.key.assert_not_called();r.find_scroll.assert_not_called()
