import unittest
from unittest.mock import Mock,patch
from PIL import Image,ImageDraw
from app.flow_vision import Screen,Vision
from app.automation import Runner

class SubmissionControlsTests(unittest.TestCase):
    def test_ready_without_any_material_text(self):
        image=Image.new('RGB',(1280,960))
        ImageDraw.Draw(image).rectangle((160,545,500,570),fill=(0,190,120))
        words=[dict(text='傳達',x=70,y=25,w=50,h=25),dict(text='自動放入',x=130,y=615,w=80,h=20)]
        self.assertTrue(Screen(image,words).submitted_ready())
        self.assertFalse(Screen(Image.new('RGB',(1280,960)),words).submitted_ready())
        self.assertFalse(Screen(image,[]).submitted_ready())
    def test_autofill_already_on_is_distinguished_from_off(self):
        image=Image.new('RGB',(1280,960),(70,80,90))
        self.assertFalse(Screen(image,[]).autofill_enabled())
        ImageDraw.Draw(image).rectangle((84,620,94,632),fill=(0,190,120))
        self.assertTrue(Screen(image,[]).autofill_enabled())
    def test_cropped_ocr_preserves_coordinates_and_batch_limit(self):
        session=Mock()
        def recognize(images,timeout):
            self.assertLessEqual(len(images),12)
            self.assertTrue(all(im.width<1280 and im.height<400 for im in images))
            return [[dict(text='自動放入',x=30,y=30,w=60,h=20)] for im in images]
        session.recognize_many.side_effect=recognize
        screen=Vision(session).observe_submission_controls(Image.new('RGB',(1280,960)))
        self.assertTrue(screen.has('自動放入',(30,585,250,660)))
    def test_transition_capture_checks_safety_before_and_after_ocr(self):
        r=Runner(Mock(),Mock(),Mock(),Mock(),[],None)
        r.submission_mode=True;r.vision=Mock();r.journal.data={"pending":None}
        with patch('app.automation.capture.capture',return_value=Image.new('RGB',(1280,960))):r.screen()
        r.vision.observe_submission_controls.assert_called_once()
        r.vision.observe.assert_not_called()
        self.assertEqual(r.safety.check.call_count,2)

    def test_wide_bottom_confirm_needs_no_ocr(self):
        image=Image.new('RGB',(1280,960))
        ImageDraw.Draw(image).rounded_rectangle((390,875,890,935),radius=20,fill=(0,190,120))
        self.assertTrue(Screen(image,[]).completion())
        for box in [(695,875,790,920),(145,533,535,581),(390,650,890,710)]:
            image=Image.new('RGB',(1280,960))
            ImageDraw.Draw(image).rectangle(box,fill=(0,190,120))
            self.assertFalse(Screen(image,[]).completion())
        self.assertFalse(Screen(Image.new('RGB',(1280,960)),[]).completion())

    def test_pending_completion_uses_button_without_ocr(self):
        r=Runner(Mock(),Mock(),Mock(),Mock(),[],None)
        r.submission_mode=True;r.vision=Mock();r.journal.data={'pending':{'kind':'complete'}}
        image=Image.new('RGB',(1280,960))
        ImageDraw.Draw(image).rounded_rectangle((390,875,890,935),radius=20,fill=(0,190,120))
        with patch('app.automation.capture.capture',return_value=image):
            self.assertTrue(r.screen().completion())
        r.vision.observe_submission_controls.assert_not_called()
        self.assertEqual(r.safety.check.call_count,2)

    def test_pending_completion_reads_only_dialogue_when_button_absent(self):
        r=Runner(Mock(),Mock(),Mock(),Mock(),[],None)
        r.submission_mode=True;r.vision=Mock();r.journal.data={'pending':{'kind':'complete'}}
        with patch('app.automation.capture.capture',return_value=Image.new('RGB',(1280,960))):r.screen()
        r.vision.observe_dialogue.assert_called_once()
        r.vision.observe_submission_controls.assert_not_called()
        self.assertEqual(r.safety.check.call_count,2)
