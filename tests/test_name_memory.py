"""Compatibility checks for legacy settings still loaded at app startup."""
import json,tempfile,unittest
from pathlib import Path
from app.name_memory import NameMemory

class SavedNameSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'names.json'
        self.memory=NameMemory(self.path,['箭花','鐵礦石','高級原木','高級原木+'])
    def tearDown(self):self.temp.cleanup()
    def test_saved_other_material_and_plus_conflicts_rejected(self):
        for raw,name in [('鐵礦石','箭花'),('高級原木','高級原木+'),('木+','高級原木')]:
            with self.subTest(raw=raw,name=name):
                self.path.write_text(json.dumps({raw:name}),encoding='utf-8')
                with self.assertRaises(ValueError):NameMemory(self.path,self.memory.materials)

    def test_old_wool_alias_is_ignored_and_other_memory_preserved(self):
        self.path.write_text(json.dumps({'級羊毛':'羊毛','高級羊毛':'羊毛','花':'箭花'},ensure_ascii=False),encoding='utf-8')
        original=self.path.read_bytes()
        memory=NameMemory(self.path,['羊毛','箭花'])
        self.assertEqual(memory.aliases,{'花':'箭花'})
        self.assertEqual(self.path.read_bytes(),original)
