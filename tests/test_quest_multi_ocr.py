import unittest
from unittest.mock import Mock,patch
from PIL import Image
from app.inventory_recognition import _preview
from app.whitelist import validate

class QuestMultiOcrTests(unittest.TestCase):
    def scan(self,sets):
        session=Mock();session.recognize_many.side_effect=[[[],[],[],[],[]],sets]
        entries=validate([('採集卷軸: 小麥','小麥',10),('採集卷軸: 羊毛','羊毛',20)])
        times=dict(preprocess_ms=0,matching_ms=0,retry_stage_ms=0,fuzzy_matching_ms=0)
        with patch('app.inventory_recognition.selected_tab',return_value=True),patch('app.inventory_recognition.retry_unconfirmed',side_effect=lambda image,entries,session,cells,alternate,times:(cells,0)):
            result=_preview(Image.new('RGB',(1280,960)),entries,session,'quest',times)
        self.assertEqual(len(session.recognize_many.call_args_list[1].args[0]),5)
        return result
    def label(self,name):return dict(text=name,x=15,y=15,w=350,h=80)
    def test_last_method_recovers_cell_missed_by_first_four(self):
        result=self.scan([[],[],[],[],[self.label('採集卷軸:小麥')]])
        self.assertEqual(result.detections[0].name,'採集卷軸: 小麥')
        self.assertEqual(result.detections[0].kind,'quest')
    def test_conflicting_exact_names_cannot_become_fuzzy_candidate(self):
        result=self.scan([[self.label('採集卷軸:小麥')],[],[],[],[self.label('採集卷軸:羊毛')]])
        self.assertEqual(result.detections[0].kind,'conflict')
        self.assertEqual(result.reviews,[])
