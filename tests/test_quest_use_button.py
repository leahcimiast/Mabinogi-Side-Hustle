import unittest
from unittest.mock import Mock,patch
from PIL import Image,ImageDraw
from app.flow_vision import Vision,Label
from app.automation import Runner,ScreenTimeout

class UseButtonVisionTests(unittest.TestCase):
    def image(self):
        image=Image.new('RGB',(1280,960))
        ImageDraw.Draw(image).rectangle((695,875,790,920),fill=(10,190,125))
        return image
    def word(self,text='使用',x=140,y=100):
        return dict(text=text,x=x,y=y,w=70,h=36)
    def test_fixed_button_center_without_ocr(self):
        session=Mock();session.recognize_many.return_value=[[],[self.word()],[],[],[]]
        result=Vision(session).quest_use_button(self.image())
        self.assertEqual(result.point,(742.5,897.5))
        session.recognize_many.assert_not_called()
    def test_disabled_green_absent_never_uses_text_alone(self):
        session=Mock()
        self.assertIsNone(Vision(session).quest_use_button(Image.new('RGB',(1280,960))))
        session.recognize_many.assert_not_called()
    def test_wide_completion_button_not_confused_with_use(self):
        image=Image.new('RGB',(1280,960))
        ImageDraw.Draw(image).rectangle((390,875,890,935),fill=(10,190,125))
        self.assertIsNone(Vision(Mock()).quest_use_button(image))

class UseButtonWaitTests(unittest.TestCase):
    def runner(self):
        r=Runner.__new__(Runner);r.check=Mock();r.progress=Mock();r.rest=Mock();r.window=Mock();r.vision=Mock()
        return r
    def test_retry_reads_only_and_returns_ready_button(self):
        r=self.runner();button=Label('使用',(695,875,790,920));r.vision.quest_use_button.side_effect=[None,button]
        with patch('app.automation.capture.capture',return_value=Mock()):self.assertIs(r.wait_use_button(),button)
        self.assertEqual(r.check.call_count,4);self.assertEqual(r.rest.call_count,1)
    def test_cancel_after_button_check_never_returns_click_target(self):
        r=self.runner();r.vision.quest_use_button.return_value=Label('使用',(695,875,790,920))
        r.check.side_effect=[None,RuntimeError('F8')]
        with patch('app.automation.capture.capture',return_value=Mock()):
            with self.assertRaisesRegex(RuntimeError,'F8'):r.wait_use_button()
    def test_timeout_never_returns_click_target(self):
        r=self.runner()
        with self.assertRaises(ScreenTimeout):r.wait_use_button(seconds=0)
        r.vision.quest_use_button.assert_not_called()
