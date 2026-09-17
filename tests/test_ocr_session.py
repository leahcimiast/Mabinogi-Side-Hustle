import unittest
import queue
from app.ocr_session import OcrSession

class OcrTransportTests(unittest.TestCase):
    def test_cancel_does_not_wait_for_worker(self):
        session=OcrSession('unused',cancelled=lambda:True)
        with self.assertRaisesRegex(RuntimeError,'取消'):
            session._receive(20)
    def test_timeout_is_bounded(self):
        with self.assertRaises(TimeoutError):OcrSession('unused')._receive(0)
    def test_worker_exit_is_not_empty_inventory(self):
        session=OcrSession('unused');session.responses.put(None)
        with self.assertRaisesRegex(RuntimeError,'exited'):session._receive(1)
    def test_worker_error_is_not_empty_inventory(self):
        session=OcrSession('unused');session.responses.put('{"error":"language missing"}')
        with self.assertRaisesRegex(RuntimeError,'language missing'):session._receive(1)
    def test_invalid_batch_size_rejected_before_process_access(self):
        for batch in [[],[None]*13]:
            with self.assertRaises(ValueError):OcrSession('unused').recognize_many(batch)

if __name__=='__main__':unittest.main()
