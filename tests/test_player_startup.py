import threading
import unittest
from unittest.mock import Mock,patch
from app.batch_ui import focus_game
from app.capture import GameWindow
from app.player_messages import action_step,stop_message
from app.stock_check import StockVision
from app.whitelist import load


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.safety=Mock(hotkey_ok=True,reason='F8')
        self.safety.cancelled=threading.Event()
        self.window=GameWindow(123,'game','MabinogiMobile.exe',(0,0,1280,960))
        self.capture_patch=patch('app.batch_ui.capture');self.capture=self.capture_patch.start()
        self.capture.detect.return_value=[self.window]
        self.capture.process_name.return_value='MabinogiMobile.exe'
        self.capture.u.IsIconic.return_value=False
        self.capture.u.GetForegroundWindow.return_value=123
    def tearDown(self):self.capture_patch.stop()
    def test_focuses_once_without_game_input_or_arming(self):
        self.assertIs(focus_game(self.safety),self.window)
        self.capture.u.SetForegroundWindow.assert_called_once_with(123)
        self.capture.u.ShowWindow.assert_not_called()
        self.safety.arm.assert_not_called()
        self.capture.capture.assert_not_called()
    def test_restores_minimized_game(self):
        self.capture.u.IsIconic.return_value=True
        focus_game(self.safety)
        self.capture.u.ShowWindow.assert_called_once_with(123,9)
    def test_cancelled_or_ambiguous_target_never_changes_focus(self):
        self.safety.cancelled.set()
        with self.assertRaises(RuntimeError):focus_game(self.safety)
        self.safety.cancelled.clear();self.capture.detect.return_value=[self.window,self.window]
        with self.assertRaises(RuntimeError):focus_game(self.safety)
        self.capture.u.SetForegroundWindow.assert_not_called()
    def test_focus_denied_stops_without_retry(self):
        self.capture.u.GetForegroundWindow.return_value=999
        with patch.object(self.safety.cancelled,'wait',return_value=False):
            with self.assertRaisesRegex(RuntimeError,'手動切回'):focus_game(self.safety)
        self.capture.u.SetForegroundWindow.assert_called_once()
    def test_wrong_process_never_changes_focus(self):
        self.capture.process_name.return_value='other.exe'
        with self.assertRaises(RuntimeError):focus_game(self.safety)
        self.capture.u.SetForegroundWindow.assert_not_called()


class PlayerMessageTests(unittest.TestCase):
    def test_scanner_details_are_replaced_by_player_summary(self):
        for raw in ('盤點捲動中：實測 400/540 px（尚未做物品 OCR）','品名比對：黄豆 → 黃豆','已保留堆疊：黃豆 × 90'):
            self.assertEqual(action_step(raw,'庫存盤點'),'正在盤點公用保管箱，請勿操作遊戲。')
        self.assertIn('2 秒後開始',action_step('盤點將於 2 秒後開始，正在切回遊戲。','庫存盤點'))
        self.assertNotIn('OCR',action_step('辨識 OCR','素材領取'))
        self.assertNotIn('OCR',action_step('辨識 OCR','任務交付'))
        self.assertEqual(stop_message('F8 緊急停止'),'F8 緊急停止')
    def test_soybean_variant_is_whole_name_only(self):
        reader=StockVision(Mock(),load('app/default_whitelist.json'))
        self.assertEqual(reader.resolve_name({'黄豆'}),'黃豆')
        for raw in ('黄','黄豆+','高級黄豆'):
            self.assertIsNone(reader.resolve_name({raw}))
