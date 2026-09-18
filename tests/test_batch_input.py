import unittest,threading
from unittest.mock import patch,Mock,call
from app.input_control import Safety
from app.capture import GameWindow

class BatchInputTests(unittest.TestCase):
    def setUp(self):
        self.s=Safety.__new__(Safety);self.s.lock=threading.RLock();self.s.paused=True;self.s.cancelled=threading.Event();self.s.hwnd=42
        self.s.condition=threading.Condition(self.s.lock);self.s.user_paused=False;self.s.running=False
        self.w=GameWindow(42,'test','MabinogiMobile.exe',(0,0,1280,960))
    def test_all_primitives_reject_pause(self):
        with patch('app.input_control.u.SendInput') as send:
            for action in [lambda:self.s.click(self.w,10,10),lambda:self.s.key(self.w,32),lambda:self.s.number(self.w,60),lambda:self.s.scroll(self.w,350,500,-3)]:
                with self.assertRaises(RuntimeError):action()
            send.assert_not_called()
    def test_lost_focus_prevents_mouse_and_keyboard(self):
        self.s.paused=False
        with patch('app.input_control.client_rect',return_value=(0,0,1280,960)),patch('app.input_control.u.GetForegroundWindow',return_value=99),patch('app.input_control.u.SendInput') as send:
            with self.assertRaises(RuntimeError):self.s.click(self.w,350,500)
            send.assert_not_called();self.assertTrue(self.s.cancelled.is_set())

    def test_number_allows_clear_and_each_digit_to_settle(self):
        events=Mock();self.s.key=events.key;self.s.cancelled=Mock()
        self.s.cancelled.wait=events.wait;events.wait.return_value=False
        self.s.number(self.w,30)
        self.assertEqual(events.mock_calls,[
            call.key(self.w,0x41,control=True),call.wait(.15),
            call.key(self.w,0x08),call.wait(.15),
            call.key(self.w,ord('3')),call.wait(.15),
            call.key(self.w,ord('0')),call.wait(.15)])

    def test_cancel_after_clear_does_not_type_digits(self):
        self.s.key=Mock();self.s.cancelled=Mock()
        self.s.cancelled.wait.side_effect=[False,True]
        with self.assertRaises(RuntimeError):self.s.number(self.w,30)
        self.assertEqual(self.s.key.call_count,2)

    def test_drag_releases_button_on_focus_loss_without_further_movement(self):
        rect=(0,0,1280,960)
        self.s.check=Mock(side_effect=[rect,rect,RuntimeError('focus lost')]);self.s._send=Mock()
        self.s.cancelled=Mock();self.s.cancelled.wait.return_value=False
        with self.assertRaisesRegex(RuntimeError,'focus lost'):self.s.drag(self.w,(1185,135),(775,135))
        self.assertEqual(self.s._send.call_count,2)
        self.assertEqual(self.s._send.call_args_list[0].args[0][-1].payload.mi.dwFlags,2)
        self.assertEqual(self.s._send.call_args.args[0][0].payload.mi.dwFlags,4)
    def test_drag_paused_sends_nothing(self):
        with patch('app.input_control.u.SendInput') as send:
            with self.assertRaises(RuntimeError):self.s.drag(self.w,(1185,135),(775,135))
            send.assert_not_called()
    def test_drag_f8_releases_and_does_not_continue(self):
        self.s.check=Mock(return_value=(0,0,1280,960));self.s._send=Mock()
        self.s.cancelled=Mock();self.s.cancelled.wait.return_value=True
        with self.assertRaisesRegex(RuntimeError,'拖曳已暫停'):self.s.drag(self.w,(1185,135),(775,135))
        self.assertEqual(self.s._send.call_count,2)
        self.assertEqual(self.s._send.call_args.args[0][0].payload.mi.dwFlags,4)
