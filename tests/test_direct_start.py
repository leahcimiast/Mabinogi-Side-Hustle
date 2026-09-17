import threading,unittest
from unittest.mock import Mock,patch,call
from app.input_control import Safety
from app.batch_ui import prepare_game

class QuantityReplacementTests(unittest.TestCase):
    def test_default_one_is_cleared_before_sixty(self):
        safety=Safety.__new__(Safety);safety.cancelled=threading.Event()
        field={'text':'1','selected':False};history=[]
        def key(window,vk,control=False):
            history.append((vk,control))
            if control and vk==0x41:field['selected']=True
            elif vk==0x08:
                field['text']='' if field['selected'] else field['text'][:-1];field['selected']=False
            else:
                field['text']=('' if field['selected'] else field['text'])+chr(vk);field['selected']=False
        safety.key=key;safety.number('window',60)
        self.assertEqual(field['text'],'60')
        self.assertEqual(history,[(0x41,True),(0x08,False),(ord('6'),False),(ord('0'),False)])
    def test_cancel_after_select_all_does_not_type_quantity(self):
        safety=Safety.__new__(Safety);safety.cancelled=threading.Event()
        safety.key=Mock(side_effect=lambda *a,**kw:safety.cancelled.set())
        with self.assertRaises(RuntimeError):safety.number('window',60)
        self.assertEqual(safety.key.call_count,1)

class DirectStartTests(unittest.TestCase):
    @patch('app.batch_ui.capture.capture')
    @patch('app.batch_ui.capture.detect')
    def test_start_automatically_checks_capture_and_arms(self,detect,capture):
        window=object();detect.return_value=[window];safety=Mock()
        self.assertIs(prepare_game(safety),window)
        capture.assert_called_once_with(window)
        safety.arm.assert_called_once_with(window);safety.check.assert_called_once_with(window)
    @patch('app.batch_ui.capture.capture',side_effect=RuntimeError('wrong size'))
    @patch('app.batch_ui.capture.detect',return_value=[object()])
    def test_invalid_resolution_does_not_arm(self,detect,capture):
        safety=Mock()
        with self.assertRaises(RuntimeError):prepare_game(safety)
        safety.arm.assert_not_called()
    @patch('app.batch_ui.capture.capture')
    @patch('app.batch_ui.capture.detect',return_value=[])
    def test_no_game_does_not_arm(self,detect,capture):
        safety=Mock()
        with self.assertRaises(RuntimeError):prepare_game(safety)
        capture.assert_not_called();safety.arm.assert_not_called()
    @patch('app.batch_ui.capture.capture')
    @patch('app.batch_ui.capture.detect',return_value=[object(),object()])
    def test_multiple_games_do_not_arm(self,detect,capture):
        safety=Mock()
        with self.assertRaises(RuntimeError):prepare_game(safety)
        capture.assert_not_called();safety.arm.assert_not_called()
