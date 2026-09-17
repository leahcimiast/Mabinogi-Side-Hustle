import unittest
from unittest.mock import Mock
from PIL import Image
from app.recognition import Detection
from app.inventory_recognition import choose_retry,retry_unconfirmed

class RetryTests(unittest.TestCase):
    def setUp(self):
        self.old=Detection('未確認卷軸',None,(0,0,96,40),'unknown','unconfirmed','採集卷:小麥')
        self.a=Detection('採集卷軸: 小麥',3,(0,0,96,40),'verified','quest','採集卷軸:小麥')
        self.b=Detection('採集卷軸: 羊毛',3,(0,0,96,40),'verified','quest','採集卷軸:羊毛')
    def test_accept_one_exact_identity(self):
        self.assertEqual(choose_retry(self.old,[self.a,None,self.a]).name,self.a.name)
    def test_conflicting_exact_identities_stay_unknown(self):
        self.assertIs(choose_retry(self.old,[self.a,self.b]),self.old)
    def test_incomplete_retry_never_fills_characters(self):
        self.assertIs(choose_retry(self.old,[self.old,None]),self.old)
    def test_no_retry_for_already_confirmed(self):
        cells=[(self.a,[],[])]
        session=Mock()
        self.assertEqual(retry_unconfirmed(Image.new('RGB',(1280,960)),[],session,cells,[]),(cells,0))
        session.recognize_many.assert_not_called()
    def test_one_batch_with_eight_image_limit(self):
        cells=[(self.old,[],[])]*25
        session=Mock()
        session.recognize_many.return_value=[[]]*8
        retry_unconfirmed(Image.new('RGB',(1280,960)),[],session,cells,[])
        session.recognize_many.assert_called_once()
        self.assertEqual(len(session.recognize_many.call_args.args[0]),8)
        self.assertEqual(session.recognize_many.call_args.kwargs['timeout'],20)

if __name__=='__main__': unittest.main()
