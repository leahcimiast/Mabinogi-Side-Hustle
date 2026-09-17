import tempfile,unittest,threading
from pathlib import Path
from unittest.mock import Mock
from app.name_memory import NameMemory,NameReviewCompleted
from app.automation import Runner
from app.flow_vision import Label

class NameMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'names.json'
        self.memory=NameMemory(self.path,['箭花','鐵礦石','高級原木','高級原木+'])
    def tearDown(self):self.temp.cleanup()
    def test_explicit_memory_persists_and_clears(self):
        self.assertFalse(self.memory.matches('花','箭花'))
        self.memory.remember('花','箭花')
        restored=NameMemory(self.path,self.memory.materials)
        self.assertTrue(restored.matches('花','箭花'))
        self.assertFalse(restored.matches('花','鐵礦石'))
        restored.clear();self.assertFalse(NameMemory(self.path,self.memory.materials).aliases)
    def test_other_material_and_plus_conflicts_rejected(self):
        for raw,name in [('鐵礦石','箭花'),('高級原木','高級原木+'),('木+','高級原木')]:
            with self.assertRaises(ValueError):self.memory.remember(raw,name)
    def test_quantity_check_ignores_name_memory_and_title_ocr(self):
        journal=Mock();journal.batch=Mock()
        runner=Runner(Mock(),Mock(),Mock(),journal,[],None,name_memory=self.memory)
        old=Mock();old.quantity_dialog.return_value=True;old.item_title.return_value=None
        old.tooltip_titles.return_value=[Label('花',(100,300,150,325))]
        fresh=Mock();fresh.quantity_dialog.return_value=True;fresh.item_title.return_value=None
        fresh.tooltip_titles.return_value=[Label('花',(100,300,150,325))]
        runner.screen=Mock(side_effect=[old,fresh])
        runner.vision.entered_quantity=Mock(return_value=60)
        runner.vision.tooltip_retry=Mock(return_value=[])
        runner.batch.materials=[]
        runner.on_name_review=lambda review,window:self.memory.remember(review.observed,review.expected)
        self.assertEqual(runner.verify_quantity('箭花',60),60)
        runner.vision.entered_quantity.assert_called_once_with(old.image)
        runner.safety.number.assert_not_called()
    def test_remembered_name_does_not_approve_wrong_quantity(self):
        self.memory.remember('花','箭花')
        runner=Runner(Mock(),Mock(),Mock(),Mock(),[],None,name_memory=self.memory)
        screen=Mock();screen.quantity_dialog.return_value=True;screen.item_title.return_value=None
        screen.tooltip_titles.return_value=[Label('花',(100,300,150,325))]
        runner.screen=Mock(return_value=screen);runner.vision.entered_quantity=Mock(return_value=59)
        runner.vision.tooltip_retry=Mock(return_value=[])
        runner.batch.materials=[]
        with self.assertRaisesRegex(RuntimeError,'59'):runner.verify_quantity('箭花',60)
        runner.safety.click.assert_not_called()

    def test_wool_requires_exact_name_even_for_player_memory(self):
        memory=NameMemory(self.path,['羊毛','箭花'])
        for raw in ('高級羊毛','級羊毛','高羊毛','毛'):
            self.assertFalse(memory.allowed(raw,'羊毛'))
            with self.assertRaises(ValueError):memory.remember(raw,'羊毛')
            memory.aliases[raw]='羊毛'
            self.assertFalse(memory.matches(raw,'羊毛'))
        self.assertTrue(memory.allowed('羊毛','羊毛'))
    def test_old_wool_alias_is_ignored_and_other_memory_preserved(self):
        import json
        self.path.write_text(json.dumps({'級羊毛':'羊毛','高級羊毛':'羊毛','花':'箭花'},ensure_ascii=False),encoding='utf-8')
        original=self.path.read_bytes()
        memory=NameMemory(self.path,['羊毛','箭花'])
        self.assertEqual(memory.aliases,{'花':'箭花'})
        self.assertEqual(self.path.read_bytes(),original)
