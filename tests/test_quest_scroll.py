import unittest
from unittest.mock import Mock,patch
from PIL import Image,ImageDraw
from app.quest_scroll import quest_list_moved
from app.automation import Runner,MissingQuestScroll

class QuestScrollTests(unittest.TestCase):
    def test_icons_and_tiny_noise_do_not_look_like_list_motion(self):
        before=Image.new('RGB',(1280,960));after=before.copy()
        ImageDraw.Draw(after).rectangle((720,185,780,235),fill='white')
        ImageDraw.Draw(after).point((750,260),fill='white')
        self.assertFalse(quest_list_moved(before,after))
    def test_changed_name_rows_are_motion(self):
        before=Image.new('RGB',(1280,960));after=before.copy()
        draw=ImageDraw.Draw(after)
        for y in range(255,290,7):draw.rectangle((715,y,1195,y+2),fill='white')
        self.assertTrue(quest_list_moved(before,after))
    def test_stationary_list_stops_without_repeating_ocr(self):
        r=Runner(Mock(),Mock(),Mock(),Mock(),[],None)
        r.open_quests=Mock();r.rest=Mock();r.check=Mock()
        with patch('app.automation.capture.capture',return_value=Image.new('RGB',(1280,960))),patch('app.automation.scroll_label_candidates',return_value=[]) as read:
            with self.assertRaises(MissingQuestScroll):r.find_scroll(Mock(quest='missing'))
        self.assertEqual(read.call_count,2) # One screen, normal and enlarged reads.
        self.assertEqual(r.safety.scroll.call_count,3) # Top, down, one alternate-position retry.
    def test_moving_list_has_six_screen_limit(self):
        r=Runner(Mock(),Mock(),Mock(),Mock(),[],None)
        r.open_quests=Mock();r.rest=Mock();r.check=Mock()
        with patch('app.automation.capture.capture',return_value=Image.new('RGB',(1280,960))),patch('app.automation.scroll_label_candidates',return_value=[]) as read,patch('app.quest_scroll.quest_list_moved',return_value=True):
            with self.assertRaises(MissingQuestScroll):r.find_scroll(Mock(quest='missing'))
        self.assertEqual(read.call_count,12)
