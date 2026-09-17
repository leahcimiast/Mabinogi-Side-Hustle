import unittest
from unittest.mock import patch
from app.capture import detect

class DetectionTests(unittest.TestCase):
    def detect_windows(self, windows):
        def enum(callback, argument):
            for handle in windows:
                callback(handle, argument)
            return True
        def title(handle, buffer, length):
            buffer.value = windows[handle][0]
            return len(buffer.value)
        with patch('app.capture.u.EnumWindows',side_effect=enum), \
             patch('app.capture.u.IsWindowVisible',side_effect=lambda h:windows[h][2]), \
             patch('app.capture.u.GetWindowTextLengthW',side_effect=lambda h:len(windows[h][0])), \
             patch('app.capture.u.GetWindowTextW',side_effect=title), \
             patch('app.capture.process_name',side_effect=lambda h:windows[h][1]), \
             patch('app.capture.client_rect',return_value=(0,0,1280,960)):
            return detect()

    def test_assistant_and_same_title_document_excluded(self):
        windows={1:('瑪奇 Mobile','MabinogiMobile.exe',True),
                 2:('瑪奇 Mobile 助手 — 擷取與辨識原型','MabinogiAssistant.exe',True),
                 3:('瑪奇 Mobile','notepad.exe',True)}
        self.assertEqual([w.hwnd for w in self.detect_windows(windows)],[1])

    def test_unknown_process_not_accepted_by_title(self):
        self.assertEqual(self.detect_windows({1:('瑪奇 Mobile','',True)}),[])

    def test_real_multiple_game_windows_remain_ambiguous(self):
        windows={1:('瑪奇 Mobile','MabinogiMobile.exe',True),
                 2:('Game','MABINOGIMOBILE.EXE',True),
                 3:('Hidden','MabinogiMobile.exe',False)}
        self.assertEqual([w.hwnd for w in self.detect_windows(windows)],[1,2])

if __name__=='__main__':
    unittest.main()
