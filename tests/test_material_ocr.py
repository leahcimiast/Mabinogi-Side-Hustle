import unittest
from unittest.mock import Mock
from PIL import Image
from app.flow_vision import Screen,Vision,Label

def word(text,x,y,w=100,h=24):return dict(text=text,x=x,y=y,w=w,h=h)

class MaterialOcrTests(unittest.TestCase):
    def setUp(self):self.image=Image.new('RGB',(1280,960))
    def test_food_title_does_not_require_material_category(self):
        for name in ('烤整顆馬鈴薯','煎蛋','蘋果汁'):
            screen=Screen(self.image,[word(name,143,350),word('食物',143,386,h=14),word('獲得方法',143,660,h=16)])
            self.assertEqual([title.text for title in screen.tooltip_titles()],[name])
    def test_grid_name_alone_does_not_become_tooltip(self):
        screen=Screen(self.image,[word('煎蛋',350,350,h=14)])
        self.assertEqual(screen.tooltip_titles(),[])
    def test_footer_anchor_chooses_title_not_description(self):
        screen=Screen(self.image,[word('煎蛋',143,350),word('美味的食物',143,500),word('獲得方法',143,660,h=16)])
        self.assertEqual(screen.tooltip_titles()[0].text,'煎蛋')
    def test_storage_retry_exhausts_variants_and_deduplicates(self):
        vision=Vision(Mock());label=Label('黃豆',(100,400,180,420))
        vision.storage_names=Mock(side_effect=[[],[label],[label],[]])
        self.assertEqual(vision.storage_names_retry(self.image),[label])
        self.assertEqual([c.args[1] for c in vision.storage_names.call_args_list],['color','gray','threshold','wide'])

    def test_full_screen_runs_five_methods_on_first_observation(self):
        session=Mock();session.recognize_many.return_value=[[],[],[],[],[word('自動放入',60,1200,180,40)]]
        screen=Vision(session).observe(self.image)
        self.assertEqual(len(session.recognize_many.call_args.args[0]),5)
        self.assertTrue(screen.has('自動放入',(30,585,250,660)))
        self.assertIs(screen.image,self.image)
    def test_report_seen_by_only_one_method_still_blocks_absence(self):
        from app.flow_vision import MultiScreen
        screen=MultiScreen(self.image,[[],[],[word('回報任務佈告欄',1000,300)],[]])
        self.assertIsNotNone(screen.report())
    def test_disagreeing_tracker_identities_stop(self):
        from app.flow_vision import MultiScreen
        screen=MultiScreen(self.image,[[word('取得鐵礦石',1000,240)],[word('取得高級鐵礦石',1000,240)]])
        with self.assertRaises(RuntimeError):screen.tracker('鐵礦石')
    def test_variant_words_are_not_concatenated_into_a_name(self):
        from app.flow_vision import MultiScreen
        screen=MultiScreen(self.image,[[word('自動',30,600)],[word('放入',80,600)]])
        self.assertFalse(screen.has('自動放入'))

    def test_unread_storage_cell_gets_isolated_two_times_ocr(self):
        session=Mock();session.recognize_many.return_value=[[word('黃豆',40,30,50,26)]]
        vision=Vision(session);vision._storage_boxes=[(152,700,246,730)]
        vision.storage_names=Mock(return_value=[])
        found=vision.storage_names_retry(self.image)
        self.assertEqual(found,[Label('黃豆',(152,635,246,695))])
        self.assertEqual(session.recognize_many.call_args.args[0][0].size,(228,100))
    def test_storage_roi_maps_control_coordinates_and_keeps_five_methods(self):
        session=Mock()
        # Quantity controls are placed at atlas (10,1055) from game (660,620).
        session.recognize_many.return_value=[[word('移至背包',250,1330,100,24)],[],[],[],[]]
        screen=Vision(session).observe_storage(self.image)
        self.assertEqual(len(session.recognize_many.call_args.args[0]),5)
        self.assertTrue(screen.has('移至背包',(660,620,1260,955)))
        self.assertEqual(screen.find('移至背包').box,(900,895,1000,919))
