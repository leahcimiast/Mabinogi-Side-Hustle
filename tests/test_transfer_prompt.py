import unittest
from unittest.mock import Mock,patch
from PIL import Image
from app.automation import Runner,ScreenTimeout
from app.flow_vision import Vision
import test_fixed_batch as fixtures

class PromptTransitionTests(unittest.TestCase):
    setUp=fixtures.WithdrawalTests.setUp
    tearDown=fixtures.WithdrawalTests.tearDown
    def test_waits_for_button_then_sends_space_once(self):
        self.runner.wait_transfer_prompt=Runner.wait_transfer_prompt.__get__(self.runner)
        self.runner.vision.transfer_prompt_ready=Mock(side_effect=[False,False,True])
        with patch('app.automation.capture.capture',return_value=Mock()):self.runner.withdrawal()
        self.assertEqual(self.runner.vision.transfer_prompt_ready.call_count,3)
        self.runner.key.assert_called_once_with(0x20)
        self.assertIn('鐵礦石',self.j.data['withdrawn'])
    def test_prompt_timeout_never_sends_space_or_quantity(self):
        self.runner.wait_transfer_prompt.side_effect=ScreenTimeout('prompt unavailable')
        self.runner.withdrawal()
        self.runner.key.assert_not_called();self.safety.number.assert_not_called()
        self.assertIsNone(self.j.data['pending'])
    def test_no_space_replay_when_quantity_dialog_does_not_open(self):
        self.runner.wait.side_effect=ScreenTimeout('quantity dialog unavailable')
        self.runner.withdrawal()
        self.runner.key.assert_called_once_with(0x20)
        self.safety.number.assert_not_called()
        self.assertIsNone(self.j.data['pending'])
    def test_cancel_during_prompt_ocr_prevents_space(self):
        self.runner.wait_transfer_prompt=Runner.wait_transfer_prompt.__get__(self.runner)
        self.runner.vision.transfer_prompt_ready=Mock(return_value=True)
        self.runner.check=Mock(side_effect=[None,RuntimeError('F8')])
        with patch('app.automation.capture.capture',return_value=Mock()):
            with self.assertRaisesRegex(RuntimeError,'F8'):self.runner.withdrawal()
        self.runner.key.assert_not_called()

class PromptVisionTests(unittest.TestCase):
    def test_dark_or_disabled_button_never_uses_text_alone(self):
        session=Mock();self.assertFalse(Vision(session).transfer_prompt_ready(Image.new('RGB',(1280,960))))
        session.recognize_many.assert_not_called()
