"""Report recognition under changing tracker backgrounds."""
import unittest
from unittest.mock import Mock
from PIL import Image
from app.flow_vision import Vision, MultiScreen


def word(text,x,y,w=100,h=18):
    return dict(text=text,x=x,y=y,w=w,h=h)


class ReportLineRetryTests(unittest.TestCase):
    def setUp(self):
        self.image=Image.new('RGB',(1280,960))
        self.session=Mock()
        self.vision=Vision(self.session)
        self.rows=[word('取得貝類',1157,233,86,20),word('向回報',1142,281,120,13)]

    def results(self,text):
        return [[word(text,30,38,420,39)]]+[[] for _ in range(11)]

    def test_light_and_dark_backgrounds_preserve_coordinates_and_identity(self):
        for color in ((235,235,235),(20,25,30)):
            with self.subTest(color=color):
                image=Image.new('RGB',(1280,960),color)
                self.session.recognize_many.return_value=self.results('向任務佈告欄回報')
                screen=self.vision.retry_report_line(image,MultiScreen(image,[self.rows]))
                self.assertIsNotNone(screen.report())
                self.assertEqual(screen.tracker('貝類').text,'取得貝類')
                self.assertAlmostEqual(screen.report().point[0],1105+(30-20+420/2)/3)
                images=self.session.recognize_many.call_args.args[0]
                self.assertEqual(len(images),12)
                self.assertEqual(images[0].size,(550,127))

    def test_incomplete_text_does_not_become_permission(self):
        for text in ('10/10','佈告欄','回報','向其他人回報','尚未完成'):
            with self.subTest(text=text):
                self.session.recognize_many.return_value=self.results(text)
                screen=self.vision.retry_report_line(self.image,MultiScreen(self.image,[self.rows]))
                self.assertIsNone(screen.report())

    def test_count_only_or_unrelated_report_never_triggers_retry(self):
        for rows in ([self.rows[0],word('10/10',1200,265)],
                     [self.rows[1]],
                     [self.rows[0],word('告回報',1142,400,120,13)]):
            self.vision.retry_report_line(self.image,MultiScreen(self.image,[rows]))
        self.session.recognize_many.assert_not_called()

    def test_two_report_rows_remain_ambiguous(self):
        rows=self.rows+[word('取得羊毛',1157,350,86,20),word('向務告回報',1142,400,120,13)]
        self.session.recognize_many.return_value=self.results('向任務佈告欄回報')
        screen=self.vision.retry_report_line(self.image,MultiScreen(self.image,[rows]))
        with self.assertRaisesRegex(RuntimeError,'多個'):screen.report()

    def test_cancelled_ocr_propagates_without_another_retry(self):
        self.session.recognize_many.side_effect=RuntimeError('辨識已取消')
        with self.assertRaisesRegex(RuntimeError,'已取消'):
            self.vision.retry_report_line(self.image,MultiScreen(self.image,[self.rows]))
        self.assertEqual(self.session.recognize_many.call_count,1)

    def test_dim_white_text_is_normalized_before_masking(self):
        image=Image.new('RGB',(1280,960),(20,25,30))
        image.putpixel((1120,280),(150,150,150))
        self.session.recognize_many.return_value=[[] for _ in range(12)]
        self.vision.retry_report_line(image,MultiScreen(image,[self.rows]))
        mask=self.session.recognize_many.call_args.args[0][4]
        self.assertLess(mask.getpixel((66,36)),100)
