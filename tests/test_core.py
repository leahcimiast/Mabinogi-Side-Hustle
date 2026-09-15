import unittest
import time
import ctypes as C
from app.capture import u
from unittest.mock import patch
from pathlib import Path
from app.whitelist import validate,load
from app.recognition import match_items
from app.input_control import Safety
from app.capture import GameWindow

Q=validate([('採集卷軸: 羊毛','羊毛',20),('採集卷軸: 高級原木+','高級原木+',20)])
def word(text,x=100,y=100,w=40,h=15):
    return dict(text=text,x=x,y=y,w=w,h=h)

class WhitelistTests(unittest.TestCase):
    def test_default_special_mapping(self):
        q=load(Path(__file__).resolve().parents[1]/'app/default_whitelist.json')
        self.assertEqual(len(q),19)
        self.assertEqual(next(x.material for x in q if x.quest=='採集卷軸: 蜘蛛絲'),'蜘蛛網')
        self.assertIn('高級原木+',[x.material for x in q])
    def test_invalid_rows(self):
        for amount in [0,-1,1.5,True,'20','=1+1',float('nan')]:
            with self.subTest(amount=amount),self.assertRaises((ValueError,OverflowError)):
                validate([('a','b',amount)])
        with self.assertRaises(ValueError):
            validate([('a','b',1),('a','c',2)])

class RecognitionTests(unittest.TestCase):
    def test_label_and_count(self):
        found=match_items([word('羊',100,w=15),word('毛',117,w=15),word('70',120,65)],Q,(1280,960))
        self.assertEqual([(x.name,x.count) for x in found],[('羊毛',70)])
    def test_no_partial_material_match(self):
        self.assertEqual(match_items([word('高級羊毛',w=70)],Q,(1280,960)),[])
    def test_plus_is_literal(self):
        self.assertEqual(match_items([word('高級原木')],Q,(1280,960)),[])
        self.assertEqual(match_items([word('高級原木+')],Q,(1280,960))[0].name,'高級原木+')
    def test_missing_abbreviated_and_ambiguous_counts(self):
        for counts in [[],[word('1萬',120,65)],[word('70',120,65),word('80',140,65)]]:
            self.assertIsNone(match_items([word('羊毛')]+counts,Q,(1280,960))[0].count)
    def test_whitespace_not_character_substitution(self):
        self.assertEqual(match_items([word('採集卷軸:羊毛',w=150)],Q,(1280,960))[0].name,'採集卷軸: 羊毛')
        self.assertEqual(match_items([word('採集卷軸：羊毛',w=150)],Q,(1280,960)),[])

class SafetyTests(unittest.TestCase):
    def test_paused_and_cancelled_never_send(self):
        s=Safety()
        try:
            w=GameWindow(42,'test','MabinogiMobile.exe',(0,0,1280,960))
            with patch('app.input_control.u.SendInput') as send:
                with self.assertRaises(RuntimeError):
                    s.inventory_once(w)
                s.pause('F8')
                with self.assertRaises(RuntimeError):
                    s.arm(w)
                send.assert_not_called()
        finally:
            s.close()
    def test_hotkey_message_and_focus_monitor(self):
        s=Safety()
        try:
            if not s.hotkey_ok:
                self.skipTest('F8 in use by another application')
            s.prepare()
            self.assertTrue(u.PostThreadMessageW(s.thread.native_id,0x0312,1,0))
            self.assertTrue(s.cancelled.wait(.5))
            self.assertEqual(s.reason,'F8 緊急停止')
            with patch('app.input_control.u.GetForegroundWindow',return_value=99):
                s.prepare()
                with s.lock:
                    s.hwnd=42;s.paused=False
                self.assertTrue(s.cancelled.wait(.5))
                self.assertTrue(s.paused)
        finally:
            s.close()

    def test_foreground_and_size_gates(self):
        s=Safety()
        try:
            w=GameWindow(42,'test','MabinogiMobile.exe',(0,0,1280,960))
            s.hwnd=42
            for foreground,size in [(99,(0,0,1280,960)),(42,(0,0,1920,1080))]:
                with s.lock,patch('app.input_control.u.GetForegroundWindow',return_value=foreground),patch('app.input_control.u.IsIconic',return_value=False),patch('app.input_control.client_rect',return_value=size),patch('app.input_control.process_name',return_value='MabinogiMobile.exe'),patch('app.input_control.u.SendInput') as send:
                    s.prepare();s.paused=False
                    with self.assertRaises(RuntimeError):
                        s.inventory_once(w)
                    send.assert_not_called()
        finally:
            s.close()

if __name__=='__main__':
    unittest.main()
