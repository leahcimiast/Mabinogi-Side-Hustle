import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from collections import Counter
from app.fixed_batch import fixed_batch,Journal
from app.whitelist import load
from app.automation import Runner
from app.flow_vision import Label

ENTRIES=load(Path(__file__).resolve().parents[1]/'app/default_whitelist.json')
class ActiveFirstTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=fixed_batch(ENTRIES)
        self.j=Journal(Path(self.temp.name)/'batch.json',self.base)
        self.wool=next(q for q in ENTRIES if q.material=='羊毛')
    def tearDown(self):self.temp.cleanup()
    def test_reorders_one_completion_without_changing_totals_and_reloads(self):
        self.j.adopt_active(ENTRIES,self.wool.quest,'取得羊毛')
        self.assertEqual(self.j.batch.completions[0].quest,self.wool.quest)
        self.assertEqual(self.j.batch.completions[1].quest,ENTRIES[0].quest)
        self.assertEqual(Counter(q.quest for q in self.base.completions),Counter(q.quest for q in self.j.batch.completions))
        self.assertEqual(self.j.data['completed'],0)
        reloaded=Journal(self.j.path,self.base);self.assertEqual(reloaded.batch,self.j.batch)
        self.assertEqual(reloaded.data['active']['identity'],'取得羊毛')
        self.j.begin('complete',0);self.j.confirm()
        self.assertEqual(Counter(q.quest for q in self.j.batch.completions[1:])[self.wool.quest],2)
    def test_completed_prefix_survives_adoption(self):
        self.j.data['completed']=4;prefix=self.j.batch.completions[:4]
        self.j.adopt_active(ENTRIES,self.wool.quest,'取得羊毛')
        self.assertEqual(self.j.batch.completions[:4],prefix)
        self.assertEqual(self.j.data['active']['index'],4)
    def test_zero_remaining_active_quest_adds_only_its_one_completion(self):
        self.j.set_remaining(ENTRIES,{q.quest:0 for q in ENTRIES})
        self.j.adopt_active(ENTRIES,self.wool.quest,'取得羊毛')
        self.assertEqual(len(self.j.batch.completions),1)
        self.j.begin('complete',0);self.j.confirm()
        self.assertEqual(self.j.data['completed'],1)
    def test_failed_save_does_not_change_in_memory_schedule(self):
        with patch.object(self.j,'save',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.j.adopt_active(ENTRIES,self.wool.quest,'取得羊毛')
        self.assertEqual(self.j.batch,self.base);self.assertIsNone(self.j.data['active'])
    def test_finishes_wool_before_opening_inventory_for_first_planned_quest(self):
        r=Runner(Mock(),Mock(),Mock(),self.j,ENTRIES,Path('scripts/ocr.ps1'))
        r.click=Mock();r.key=Mock();r.rest=Mock();r.wait_use_button=Mock()
        active=Mock();active.world.return_value=True
        active.report.return_value=Label('回報任務佈告欄',(1160,282,1268,296))
        active.tracker.side_effect=lambda name:Label('取得羊毛',(1135,235,1250,255)) if name=='羊毛' else None
        submit=Mock();submit.submission.return_value=True;submit.has.return_value=True;submit.submitted_ready.return_value=True
        complete=Mock();complete.completion.return_value=True
        world=Mock();world.world.return_value=True;world.report.return_value=None;world.tracker.return_value=None
        r.screen=Mock(side_effect=[active,submit,complete,world])
        def wait(predicate,*args):self.assertTrue(predicate(world));return world
        r.wait=Mock(side_effect=wait)
        def inventory(q):
            self.assertEqual(self.j.data['completed'],1)
            self.assertEqual(q.quest,ENTRIES[0].quest)
            raise RuntimeError('cycle resumed')
        r.find_scroll=Mock(side_effect=inventory)
        with self.assertRaisesRegex(RuntimeError,'cycle resumed'):r.quests()
        r.wait_use_button.assert_not_called();r.find_scroll.assert_called_once()
        self.assertEqual(self.j.batch.completions[0].quest,self.wool.quest)
        self.assertIsNone(self.j.data['active'])
        self.assertEqual(Counter(q.quest for q in self.j.batch.completions[1:])[self.wool.quest],2)

    def test_three_character_report_finishes_each_whitelist_quest_and_resumes(self):
        from PIL import Image
        from app.flow_vision import MultiScreen
        image=Image.new('RGB',(1280,960))
        def word(text,x,y,w,h):return dict(text=text,x=x,y=y,w=w,h=h)
        for entry in ENTRIES:
            with self.subTest(quest=entry.quest):
                journal=Journal(Path(self.temp.name)/(entry.material+'.json'),self.base)
                r=Runner(Mock(),Mock(),Mock(),journal,ENTRIES,Path('scripts/ocr.ps1'))
                r.click=Mock();r.key=Mock();r.rest=Mock();r.wait_use_button=Mock()
                active=MultiScreen(image,[[word('取得'+entry.material,1135,235,115,20),
                    word('告回報',1208,282,55,14)]])
                submit=Mock();submit.submission.return_value=True
                submit.autofill_enabled.return_value=True;submit.submitted_ready.return_value=True
                complete=Mock();complete.completion.return_value=True
                world=Mock();world.world.return_value=True;world.report.return_value=None;world.tracker.return_value=None
                r.screen=Mock(side_effect=[active,submit,complete,world])
                def wait(predicate,*args):
                    self.assertEqual(journal.data['completed'],0)
                    self.assertTrue(predicate(world));return world
                r.wait=Mock(side_effect=wait)
                def inventory(q):
                    self.assertEqual(journal.data['completed'],1)
                    self.assertEqual(q.quest,ENTRIES[0].quest)
                    raise RuntimeError('cycle resumed')
                r.find_scroll=Mock(side_effect=inventory)
                with self.assertRaisesRegex(RuntimeError,'cycle resumed'):r.quests()
                self.assertEqual(journal.batch.completions[0].quest,entry.quest)
                self.assertEqual(Counter(q.quest for q in journal.batch.completions[1:])[entry.quest],2)
                self.assertIsNone(journal.data['active'])
                r.wait_use_button.assert_not_called()
