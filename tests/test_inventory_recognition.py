import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw
from app.inventory_recognition import resolve_cell,selected_tab,atlas_words,preview
from app.recognition import match_items
from app.whitelist import validate

Q=validate([('採集卷軸: 血紅藥草','血紅藥草',20),('採集卷軸: 高級原木+','高級原木+',20),('採集卷軸: 蜘蛛絲','蜘蛛網',10)])
def word(text,x=10,y=10,w=50,h=12):
    return dict(text=text,x=x,y=y,w=w,h=h)

class QuestRecognitionTests(unittest.TestCase):
    def test_two_lines_are_one_scroll_not_material(self):
        item=resolve_cell([word('血紅藥草',y=30),word('採集卷軸:')],[word('3')],Q,(0,0,100,50))
        self.assertEqual((item.name,item.count,item.kind),('採集卷軸: 血紅藥草',3,'quest'))
    def test_wrap_can_split_scroll_prefix(self):
        item=resolve_cell([word('採集卷'),word('軸:血紅藥草',y=30)],[word('23')],Q,(0,0,100,50))
        self.assertEqual(item.count,23)
        self.assertEqual(item.name,Q[0].quest)
    def test_material_fragment_does_not_become_scroll_or_material(self):
        self.assertIsNone(resolve_cell([word('血紅藥草')],[word('3')],Q,(0,0,100,50)))
        self.assertEqual(match_items([word('血紅藥草')],Q,(1280,960)),[])
    def test_missing_prefix_and_missing_plus_are_not_invented(self):
        for name in ['採集卷:血紅藥草','採集卷軸:高級原木','採集卷軸:蜘蛛網']:
            result=resolve_cell([word(name)],[word('3')],Q,(0,0,100,50))
            self.assertEqual(result.kind,'unconfirmed')
            self.assertIsNone(result.count)
    def test_unknown_and_ambiguous_counts(self):
        for words in [[],[word('1萬')],[word('3'),word('4')],[word('0')]]:
            self.assertIsNone(resolve_cell([word('採集卷軸:血紅藥草')],words,Q,(0,0,100,50)).count)
    def test_atlas_never_imports_neighbor_or_qty_cue(self):
        mapped=atlas_words([word('Qty',15,55),word('3',200,50,10,20),word('8',650,50,10,20)],0,(450,200),(140,40),(700,220,766,242))
        self.assertEqual([w['text'] for w in mapped],['3'])
        self.assertEqual(mapped[0]['x'],715)
    def test_selected_tab_requires_white_background(self):
        words=[word('任務',1174,133,30,14)]
        image=Image.new('RGB',(1280,960),(25,35,40))
        self.assertFalse(selected_tab(image,words,'任務'))
        ImageDraw.Draw(image).rectangle((1160,124,1215,158),fill='white')
        self.assertTrue(selected_tab(image,words,'任務'))
        self.assertFalse(selected_tab(image,words,'材料'))
    def test_wrong_page_never_returns_material_counts(self):
        words=[word('任務',1174,133,30,14),word('血紅藥草',800,400)]
        image=Image.new('RGB',(1280,960),'white')
        with patch('app.inventory_recognition.OcrSession') as factory:
            session=factory.return_value.__enter__.return_value
            session.recognize_many.return_value=[words]
            session.metrics=dict(batch_roundtrip_ms=0,decode_ms=0,recognition_ms=0)
            result=preview(image,Q,'unused','material')
            self.assertEqual(result.detections,[])
            self.assertEqual(session.recognize_many.call_count,1)

if __name__=='__main__':unittest.main()
