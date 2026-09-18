import threading,time,unittest
from unittest.mock import Mock,patch
from PIL import Image,ImageDraw
from app.input_control import Safety
from app.capture import GameWindow
from app.flow_vision import Vision


class ResumablePauseTests(unittest.TestCase):
    def safety(self):
        s=Safety.__new__(Safety)
        s.lock=threading.RLock();s.condition=threading.Condition(s.lock)
        s.cancelled=threading.Event();s.user_paused=False;s.paused=False
        s.running=True;s.hwnd=42;s.hotkey_ok=True;s.paused_seconds=0.;s.pause_started=None
        return s
    def test_suspended_input_waits_and_resumes_once_without_deadlock(self):
        s=self.safety();w=GameWindow(42,'game','MabinogiMobile.exe',(0,0,1280,960))
        s.suspend();sent=threading.Event();finished=threading.Event();errors=[]
        def work():
            try:s.key(w,32)
            except Exception as error:errors.append(error)
            finally:finished.set()
        with patch('app.input_control.u.GetForegroundWindow',return_value=42),patch('app.input_control.u.IsIconic',return_value=False),patch('app.input_control.process_name',return_value='MabinogiMobile.exe'),patch('app.input_control.client_rect',return_value=(0,0,1280,960)),patch('app.input_control.u.GetSystemMetrics',side_effect=lambda x:1280 if x==78 else 960 if x==79 else 0),patch.object(s,'_send',side_effect=lambda events:sent.set()) as send:
            worker=threading.Thread(target=work);worker.start()
            try:
                self.assertFalse(sent.wait(.1));self.assertFalse(s.cancelled.is_set())
                s.resume(w)
                self.assertTrue(finished.wait(1));self.assertFalse(errors)
                send.assert_called_once();self.assertGreater(s.paused_seconds,0)
            finally:s.pause('test cleanup');worker.join(1)
    def test_fatal_stop_releases_suspended_worker_without_input(self):
        s=self.safety();s.suspend();finished=threading.Event();errors=[]
        def work():
            try:s.check(Mock())
            except RuntimeError as e:errors.append(e)
            finally:finished.set()
        worker=threading.Thread(target=work);worker.start()
        s.pause('close');self.assertTrue(finished.wait(1));worker.join(1)
        self.assertTrue(errors);self.assertTrue(s.cancelled.is_set())
    def test_rebind_failure_retains_original_registration(self):
        with patch('app.input_control.u.RegisterHotKey',side_effect=[True,False,True]),patch('app.input_control.u.UnregisterHotKey') as unregister,patch('app.input_control.u.PeekMessageW',return_value=0):
            s=Safety('F8')
            try:
                self.assertFalse(s.rebind('F9'));self.assertEqual(s.hotkey_name,'F8')
                unregister.assert_not_called()
                self.assertTrue(s.rebind('F10'));self.assertEqual(s.hotkey_name,'F10')
                unregister.assert_called_once_with(None,1)
            finally:s.close()
            self.assertEqual(unregister.call_count,2)


class TransferColorTests(unittest.TestCase):
    def test_confirmation_uses_only_fixed_green_area_without_ocr(self):
        session=Mock();vision=Vision(session);im=Image.new('RGB',(1280,960))
        self.assertFalse(vision.transfer_confirmation_ready(im))
        ImageDraw.Draw(im).rectangle((900,885,1020,920),fill=(10,180,110))
        self.assertTrue(vision.transfer_confirmation_ready(im))
        session.recognize_many.assert_not_called()
    def test_green_elsewhere_does_not_authorize_confirmation(self):
        im=Image.new('RGB',(1280,960));ImageDraw.Draw(im).rectangle((565,875,700,915),fill=(10,180,110))
        self.assertFalse(Vision(Mock()).transfer_confirmation_ready(im))
