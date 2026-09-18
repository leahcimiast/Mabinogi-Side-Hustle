"""CLI preview uses a planned count of three; it does not enter or scan quantities."""
import unittest
from unittest.mock import patch,Mock
from PIL import Image
from app.inventory_recognition import _preview
from app.recognition import Detection
from app.whitelist import validate

class DiagnosticPreviewTests(unittest.TestCase):
    def scan(self,raw,entries):
        item=Detection('?',None,(707,257,803,297),'','unconfirmed',raw)
        session=Mock();session.recognize_many.side_effect=[[[],[],[],[],[]],[[],[],[],[],[]]]
        times=dict(preprocess_ms=0,matching_ms=0,retry_stage_ms=0,fuzzy_matching_ms=0)
        with patch('app.inventory_recognition.selected_tab',return_value=True),patch('app.inventory_recognition.build_atlases',return_value=['labels','digits','green','color','gray','threshold']),patch('app.inventory_recognition.retry_unconfirmed',return_value=([(item,[],[])],0)):
            result=_preview(Image.new('RGB',(1280,960)),entries,session,'quest',times)
        self.assertEqual(session.recognize_many.call_args_list[1].args[0],['labels','green','color','gray','threshold'])
        self.assertEqual(result.detections[0].count,3)
        return result
    def test_unique_typo_adopted(self):
        result=self.scan('採集卷軸:咻咻磨菇',validate([('採集卷軸: 咻咻蘑菇','咻咻蘑菇',20)]))
        self.assertEqual(result.detections[0].kind,'quest_fuzzy')
        self.assertEqual(result.reviews,[])
    def test_tied_names_not_adopted(self):
        result=self.scan('採集卷軸:灰蘑菇',validate([('採集卷軸: 紅蘑菇','紅蘑菇',1),('採集卷軸: 白蘑菇','白蘑菇',1)]))
        self.assertEqual(result.detections[0].kind,'unconfirmed')
    def test_type_conflict_not_adopted(self):
        result=self.scan('採集卷軸:鐵礦石',validate([('採礦卷軸: 鐵礦石','鐵礦石',20)]))
        self.assertEqual(result.detections[0].kind,'unconfirmed')
    def test_missing_plus_not_adopted(self):
        result=self.scan('採集卷軸:高級原木',validate([('採集卷軸: 高級原木+','高級原木+',20)]))
        self.assertEqual(result.detections[0].kind,'unconfirmed')
