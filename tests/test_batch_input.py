import unittest,threading
from unittest.mock import patch
from app.input_control import Safety
from app.capture import GameWindow

class BatchInputTests(unittest.TestCase):
    def setUp(self):
        self.s=Safety.__new__(Safety);self.s.lock=threading.RLock();self.s.paused=True;self.s.cancelled=threading.Event();self.s.hwnd=42
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
