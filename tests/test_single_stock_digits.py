"""Single counts must retain the same complete-glyph safeguards as long counts."""
import unittest
from unittest.mock import Mock

from PIL import Image, ImageDraw

from app.flow_vision import Label
from app.stock_check import StockVision
from app.stock_digits import digit_strip, single_digit_strips, white_mask
from app.whitelist import Quest


class SingleStockDigitTests(unittest.TestCase):
    def setUp(self):
        self.image = Image.new('RGB', (1280,960), (40,45,55))
        self.box = (462,673,531,708)
        # A white 7 above a red icon; a separate top-edge glint is not a digit.
        raw = Image.new('RGB', (69,35), (170,25,15))
        draw = ImageDraw.Draw(raw)
        draw.polygon([(39,12),(47,12),(47,15),(43,25),(40,25),
                      (44,15),(39,15)], fill='white')
        draw.rectangle((8,0,10,3), fill='white')
        self.image.paste(raw, self.box[:2])
        vision = Mock()
        vision._storage_boxes = [(437,713,531,743)]
        vision.storage_names.return_value = [Label('蘋果汁',(437,648,531,708))]
        vision.storage_names_retry.return_value = []
        self.reader = StockVision(vision, [Quest('juice','蘋果汁',10)])

    @staticmethod
    def readings(values):
        return [[] if value is None else [
            dict(text='Qty', x=8,y=32,w=50,h=31),
            dict(text=str(value), x=132,y=28,w=27,h=42)] for value in values]

    def test_complete_single_glyph_supported_at_both_positions_and_masks(self):
        strips = single_digit_strips(self.image,self.box)
        self.assertEqual(len(strips),4)
        self.assertEqual(digit_strip(self.image.crop(self.box),160,allow_single=True)[1],1)
        self.assertIsNone(digit_strip(self.image.crop(self.box),160))

    def test_same_workload_recovers_single_count_for_any_material_name(self):
        for name in ('蘋果汁','煎蛋','牛奶'):
            with self.subTest(name=name):
                vision=self.reader.vision
                vision.reset_mock()
                self.reader.names={name}
                vision.storage_names.return_value=[Label(name,(437,648,531,708))]
                vision.session.recognize_many.return_value=self.readings([7]*8)
                cell=self.reader.cells(self.image)[0]
                self.assertEqual((cell.name,cell.count,cell.uncertain),(name,7,False))
                vision.session.recognize_many.assert_called_once()
                self.assertEqual(len(vision.session.recognize_many.call_args.args[0]),8)

    def test_every_position_and_mask_must_read_and_all_numeric_reads_agree(self):
        for values in ([7]*7+[1], [7]*6+[None,None],
                       [7,7,None,None,7,7,7,7], [12]*8, [None]*8):
            with self.subTest(values=values):
                session=self.reader.vision.session
                session.reset_mock()
                session.recognize_many.return_value=self.readings(values)
                cell=self.reader.cells(self.image)[0]
                self.assertIsNone(cell.count)
                self.assertTrue(cell.uncertain)
                session.recognize_many.assert_called_once()

    def test_one_read_per_mask_and_position_is_sufficient(self):
        self.reader.vision.session.recognize_many.return_value=self.readings([7,None]*4)
        self.assertEqual(self.reader.cells(self.image)[0].count,7)

    def test_mixed_single_and_long_counts_keep_cell_and_batch_boundaries(self):
        vision=self.reader.vision
        self.reader.names={'牛奶','蘋果汁'}
        vision._storage_boxes=[(342,713,436,743),(437,713,531,743)]
        vision.storage_names.return_value=[Label('牛奶',(342,648,436,708)),
                                           Label('蘋果汁',(437,648,531,708))]
        normal=[[dict(text='500',x=140 if i<6 and i%2 else 20,
                      y=20,w=40,h=30)] for i in range(8)]
        combined=normal+self.readings([7]*8)
        vision.session.recognize_many.side_effect=[combined[:12],combined[12:]]
        cells=self.reader.cells(self.image)
        self.assertEqual([(c.name,c.count) for c in cells],[('牛奶',500),('蘋果汁',7)])
        self.assertEqual([len(c.args[0]) for c in vision.session.recognize_many.call_args_list],
                         [12,4])

    def test_cue_and_out_of_crop_words_are_never_count_evidence(self):
        results=self.readings([None]*8)
        for words in results:
            words.extend([dict(text='7',x=8,y=32,w=27,h=42),
                          dict(text='7',x=380,y=28,w=27,h=42)])
        self.reader.vision.session.recognize_many.return_value=results
        self.assertIsNone(self.reader.cells(self.image)[0].count)

    def test_focus_loss_or_stop_after_ocr_prevents_credit(self):
        done=[]
        def recognize(crops):
            done.append(True)
            return self.readings([7]*8)
        def check():
            if done:
                raise RuntimeError('F8 / focus lost')
        self.reader.vision.session.recognize_many.side_effect=recognize
        with self.assertRaisesRegex(RuntimeError,'F8'):
            self.reader.cells(self.image,check)

    def test_thin_leading_glyph_is_not_removed_to_make_a_single_digit(self):
        draw=ImageDraw.Draw(self.image)
        draw.rectangle((462+33,673+12,462+35,673+25),fill='white')
        self.assertIsNone(single_digit_strips(self.image,self.box))
        self.assertEqual(digit_strip(self.image.crop(self.box),160)[1],2)

    def test_threshold_disagreement_is_not_single_digit_evidence(self):
        ImageDraw.Draw(self.image).rectangle((495,685,497,698),fill=(170,170,170))
        self.assertIsNone(single_digit_strips(self.image,self.box))

    def test_blank_clipped_and_icon_contaminated_shapes_are_rejected(self):
        self.assertIsNone(single_digit_strips(Image.new('RGB',(1280,960)),self.box))
        for rectangle in ((501,673,509,686), (462,685,465,698),
                          (470,680,481,690)):
            with self.subTest(rectangle=rectangle):
                image=self.image.copy()
                ImageDraw.Draw(image).rectangle(rectangle,fill='white')
                self.assertIsNone(single_digit_strips(image,self.box))

    def test_crop_must_fit_both_positions_inside_image(self):
        self.assertIsNone(single_digit_strips(self.image,(-1,673,531,708)))
        self.assertIsNone(single_digit_strips(self.image,(462,930,531,959)))

    def test_fast_mask_preserves_exact_threshold_and_color_rules(self):
        # Include strict threshold boundaries, saturated icons and near-white ink.
        colors=[(r,g,b) for r in (0,150,160,170,180,200,255)
                for g in (0,150,160,170,180,200,255)
                for b in (0,150,160,170,180,200,255)]
        image=Image.new('RGB',(len(colors),1))
        image.putdata(colors)
        for threshold in (140,150,160,170,180,200):
            for spread in (None,20,40):
                expected=bytes(255 if min(p)>threshold and
                               (spread is None or max(p)-min(p)<spread) else 0
                               for p in colors)
                self.assertEqual(white_mask(image,threshold,spread).tobytes(),expected)


if __name__ == '__main__':
    unittest.main()
