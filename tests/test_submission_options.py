import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from PIL import Image
from app.fixed_batch import fixed_batch,Journal
from app.whitelist import load,validate
from app.automation import Runner
from app.flow_vision import Label
from app.inventory_recognition import match_scroll_tail,scroll_label_candidates,cell_boxes

ENTRIES=load(Path(__file__).resolve().parents[1]/'app/default_whitelist.json')

class SubmissionOptionsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.base=fixed_batch(ENTRIES)
        self.journal=Journal(Path(self.temp.name)/'batch.json',self.base)
    def tearDown(self):self.temp.cleanup()
    def counts(self,n=0):return {q.quest:n for q in ENTRIES}
    def test_custom_counts_zero_skip_and_reload(self):
        counts=self.counts();counts[ENTRIES[0].quest]=1;counts[ENTRIES[2].quest]=5
        self.journal.set_remaining(ENTRIES,counts)
        self.assertEqual(len(self.journal.batch.completions),6)
        self.assertEqual(self.journal.batch.materials,self.base.materials)
        restored=Journal(self.journal.path,self.base)
        self.assertEqual(restored.batch,self.journal.batch)
        self.assertEqual([q.ordinal for q in restored.batch.completions],[1,1,2,3,4,5])
    def test_edits_preserve_completed_history_without_replay(self):
        self.journal.data['completed']=4
        prefix=self.base.completions[:4]
        counts=self.counts();counts[ENTRIES[0].quest]=2
        self.journal.set_remaining(ENTRIES,counts)
        self.assertEqual(self.journal.batch.completions[:4],prefix)
        self.assertEqual([q.ordinal for q in self.journal.batch.completions[4:]],[4,5])
        self.assertEqual(Journal(self.journal.path,self.base).data['completed'],4)
    def test_pending_or_active_cannot_change_plan(self):
        for key,value in [('active',{'index':0}),('pending',{'kind':'activate'})]:
            self.journal.data[key]=value
            with self.assertRaises(RuntimeError):self.journal.set_remaining(ENTRIES,self.counts())
            self.assertEqual(self.journal.batch,self.base)
            self.journal.data[key]=None
    def test_invalid_count_does_not_mutate_plan(self):
        for value in [-1,True,1.5,10000]:
            counts=self.counts();counts[ENTRIES[0].quest]=value
            with self.assertRaises(ValueError):self.journal.set_remaining(ENTRIES,counts)
            self.assertEqual(self.journal.batch,self.base)

    def test_custom_single_quest_completes_without_tooltip_name_recheck(self):
        counts=self.counts();counts[ENTRIES[0].quest]=1
        self.journal.set_remaining(ENTRIES,counts)
        r=Runner(Mock(),Mock(),Mock(),self.journal,ENTRIES,Path('scripts/ocr.ps1'))
        r.rest=Mock();r.click=Mock();r.key=Mock();r.find_scroll=Mock(return_value=(755,202))
        world=Mock();world.world.return_value=True;world.report.return_value=None;world.tracker.return_value=None
        active=Mock();active.tracker.side_effect=AssertionError('No name recheck after scroll use');active.report.return_value=Label('回報任務',(1000,270,1150,290))
        submit=Mock();submit.submission.return_value=True;submit.has.side_effect=AssertionError("Material OCR must not be requested");submit.submitted_ready.return_value=True;submit.autofill_enabled.return_value=False
        complete=Mock();complete.completion.return_value=True
        closed=Mock();closed.world.return_value=True;closed.tracker.return_value=None;closed.report.return_value=None
        r.screen=Mock(side_effect=[world,submit,complete])
        observations=iter([active,submit,closed])
        def wait(predicate,*args):
            screen=next(observations);self.assertTrue(predicate(screen));return screen
        r.wait=Mock(side_effect=wait)
        r.wait_use_button=Mock(return_value=Label('使用',(695,875,790,920)))
        r.quests()
        r.wait_use_button.assert_called_once()
        r.click.assert_any_call((742.5,897.5))
        r.click.assert_any_call((98,625))
        submit.has.assert_not_called()
        self.assertEqual(self.journal.data['completed'],1)
        self.assertIsNone(self.journal.data['active']);self.assertIsNone(self.journal.data['pending'])
        r.find_scroll.assert_called_once()
        r.safety.pause.assert_called_once_with('1 次任務批次已完成；不再啟用剩餘卷軸。')

class ScrollTailTests(unittest.TestCase):
    def test_prefix_noise_fullwidth_colon_and_tail_only(self):
        for raw in ['採卷軸:鐵礦石','採礦卷：鐵礦石','鐵礦石']:
            self.assertEqual(match_scroll_tail(raw,ENTRIES),ENTRIES[0].quest)
    def test_plus_grade_and_material_mapping_remain_distinct(self):
        for raw in ['採集卷軸:高級原木','採集卷軸:高級羊毛','採集卷軸:蜘蛛網','冒險日誌','採卷軸:中級原木+']:
            self.assertIsNone(match_scroll_tail(raw,ENTRIES))
        self.assertEqual(match_scroll_tail('採卷:蜘蛛絲',ENTRIES),'採集卷軸: 蜘蛛絲')
    def test_unique_fuzzy_tail_and_ambiguous_rejection(self):
        self.assertEqual(match_scroll_tail('採卷:馬鈴薯塊',ENTRIES),'採集卷軸: 馬鈴薯')
        entries=validate([('料理卷軸: 蘋果汁','a',1),('採集卷軸: 蘋果汁','b',1)])
        self.assertIsNone(match_scroll_tail('蘋果汁',entries))
    def test_crop_includes_upper_text_and_batches_stay_bounded(self):
        self.assertLessEqual(cell_boxes(0)[0][1],251)
        session=Mock()
        word=dict(text='採卷軸:鐵礦石',x=40,y=45,w=180,h=30)
        session.recognize_many.side_effect=[[ [word] ]+[[]]*11,[[]]*12,[[]]]
        found=scroll_label_candidates(Image.new('RGB',(1280,960)),ENTRIES[0].quest,ENTRIES,session)
        self.assertEqual(len(found),1)
        self.assertEqual([len(c.args[0]) for c in session.recognize_many.call_args_list],[12,12,1])

class QuestNavigationTests(unittest.TestCase):
    def runner(self):
        r=Runner(Mock(),Mock(),Mock(),Mock(),ENTRIES,Path('scripts/ocr.ps1'))
        r.key=Mock();r.click=Mock();r.rest=Mock();r.progress=Mock()
        return r
    def test_single_swipe_then_fixed_click_without_tab_ocr(self):
        r=self.runner();inventory=Mock()
        inventory.find.return_value=Label('道具',(930,880,975,920))
        r.wait=Mock(return_value=inventory)
        r.inventory_screen=Mock(side_effect=AssertionError('No tab OCR'))
        r.open_quests()
        self.assertEqual(r.safety.drag.call_count,1)
        for call in r.safety.drag.call_args_list:
            self.assertEqual(call.args,(r.window,(1185,135),(775,135)))
        self.assertEqual(r.click.call_args.args[0],(1189,140))
        r.inventory_screen.assert_not_called();r.safety.key.assert_not_called()
        inventory.selected_tab.assert_not_called()
    def test_interrupted_swipe_never_clicks_quest(self):
        r=self.runner();r.wait=Mock()
        r.safety.drag.side_effect=RuntimeError('lost focus')
        with self.assertRaisesRegex(RuntimeError,'lost focus'):r.open_quests()
        self.assertEqual(r.click.call_count,1) # Only the preceding item category.
