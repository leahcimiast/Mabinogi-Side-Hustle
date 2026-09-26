"""v1.0.3 icon and leading-digit conflict regressions; no private fixtures."""
import unittest
from unittest.mock import Mock
from PIL import Image, ImageDraw
from app.stock_check import StockVision
from app.stock_digits import digit_strip
from app.whitelist import Quest
from app.flow_vision import Label


def glyph_image():
    image=Image.new('RGB',(69,35),(40,45,55))
    draw=ImageDraw.Draw(image)
    # Three complete, aligned white glyph components (leading 1 is thin).
    draw.rectangle((18,12,21,25),fill='white')
    draw.rectangle((25,12,33,25),outline='white',width=2)
    draw.rectangle((37,12,45,25),outline='white',width=2)
    return image


def words(value):
    return [dict(text=str(value),x=24,y=24,w=100,h=50)]


class StockRecognitionV103Tests(unittest.TestCase):
    def setUp(self):
        self.reader=StockVision(Mock(),[Quest('iron','鐵礦石',20)])
        self.image=Image.new('RGB',(1280,960))
        self.image.paste(glyph_image(),(557,550))
        self.box=(557,550,626,585)

    def test_digit_shapes_preserve_leading_one(self):
        for threshold in (160,180):
            strip, count, box=digit_strip(glyph_image(),threshold)
            self.assertEqual(count,3)
            self.assertEqual(box,(18,12,46,26))

    def test_recover_suffix_conflict_only_with_four_agreeing_reads(self):
        self.reader.vision.session.recognize_many.return_value=[words(182)]*4
        self.assertEqual(self.reader.retry_conflicting_count(self.image,self.box,lambda:None,{82:3,182:2}),182)
        self.assertEqual(self.reader.vision.session.recognize_many.call_count,1)

    def test_majority_suffix_does_not_override_full_glyph_count(self):
        self.reader.vision.session.recognize_many.return_value=[words(82)]*4
        self.assertIsNone(self.reader.retry_conflicting_count(self.image,self.box,lambda:None,{82:3,182:2}))

    def test_conflicting_or_missing_fallback_results_stay_unknown(self):
        for results in ([words(182)]*3+[words(82)], [words(182)]*2+[[],[]], [words(982)]*4):
            self.reader.vision.session.recognize_many.return_value=results
            self.assertIsNone(self.reader.retry_conflicting_count(self.image,self.box,lambda:None,{82:3,182:2}))

    def test_single_blank_is_allowed_when_both_masks_corroborate(self):
        self.reader.vision.session.recognize_many.return_value=[words(182)]*3+[[]]
        self.assertEqual(self.reader.retry_conflicting_count(self.image,self.box,lambda:None,{82:3,182:2}),182)

    def test_suffix_plus_same_length_conflict_requires_visual_corroboration(self):
        self.reader.vision.session.recognize_many.return_value=[words(182)]*4
        self.assertEqual(self.reader.retry_conflicting_count(self.image,self.box,lambda:None,
                                                           {82:1,182:3,192:1}),182)

    def test_milk_57_7_47_votes_can_only_accept_corroborated_original(self):
        self.image.paste((40,45,55),(575,562,579,576))
        self.reader.vision.session.recognize_many.return_value=[words(47)]*4
        self.assertEqual(self.reader.retry_conflicting_count(self.image,self.box,lambda:None,
                                                           {57:1,7:1,47:3}),47)
        self.reader.vision.session.recognize_many.return_value=[words(87)]*4
        self.assertIsNone(self.reader.retry_conflicting_count(self.image,self.box,lambda:None,
                                                            {57:1,7:1,47:3}))

    def test_missing_leading_component_cannot_confirm_smaller_candidate(self):
        self.image.paste((40,45,55),(575,562,579,576))
        self.reader.vision.session.recognize_many.return_value=[words(82)]*4
        self.assertIsNone(self.reader.retry_conflicting_count(self.image,self.box,lambda:None,{82:3,182:2}))
        self.reader.vision.session.recognize_many.assert_not_called()

    def test_non_suffix_conflict_never_enters_extra_ocr(self):
        self.assertIsNone(self.reader.retry_conflicting_count(self.image,self.box,lambda:None,{182:3,192:2}))
        self.reader.vision.session.recognize_many.assert_not_called()

    def test_blank_clipped_or_contaminated_glyphs_are_rejected(self):
        self.assertIsNone(digit_strip(Image.new('RGB',(69,35)),160))
        self.assertIsNone(digit_strip(glyph_image().crop((18,0,69,35)),160))
        noisy=glyph_image()
        ImageDraw.Draw(noisy).rectangle((2,2,15,5),fill='white')
        self.assertIsNone(digit_strip(noisy,160))

    def test_unaligned_components_cannot_silently_drop_leading_digit(self):
        im=glyph_image()
        im.paste((40,45,55),(18,12,22,26))
        ImageDraw.Draw(im).rectangle((18,6,21,19),fill='white')
        self.assertIsNone(digit_strip(im,160))

    def test_wide_top_icon_highlight_does_not_replace_digit_components(self):
        im=glyph_image()
        ImageDraw.Draw(im).rectangle((0,0,48,5),fill='white')
        self.assertEqual(digit_strip(im,160)[1],3)

    def test_tiny_top_edge_noise_above_baseline_is_not_a_leading_digit(self):
        im=glyph_image()
        ImageDraw.Draw(im).line((9,0,9,6),fill='white')
        self.assertEqual(digit_strip(im,160)[1],3)

    def test_cell_suffix_majority_enters_corroboration(self):
        self.reader.names={'貝類'}
        vision=self.reader.vision
        vision.storage_names.return_value=[Label('貝類',(532,525,626,585))]
        vision.storage_names_retry.return_value=[]
        vision._storage_boxes=[(532,590,626,620)]
        values=[None,182,82,82,182,82,None,None]
        first=[]
        for method,value in enumerate(values):
            first.append([] if value is None else [dict(text=str(value),
                x=140 if method<6 and method%2 else 20,y=20,w=40,h=30)])
        vision.session.recognize_many.side_effect=[first,[words(182)]*4]
        cell=self.reader.cells(self.image)[0]
        self.assertEqual((cell.name,cell.count,cell.uncertain),('貝類',182,False))

    def test_failed_iron_color_gate_does_not_ocr_count(self):
        vision=self.reader.vision
        vision.storage_names.return_value=[Label('鐵礦石',(57,281,151,341))]
        vision.storage_names_retry.return_value=[]
        vision._storage_boxes=[(57,346,151,376)]
        cell=self.reader.cells(self.image)[0]
        self.assertEqual((cell.name,cell.count,cell.uncertain),('鐵礦石',None,True))
        vision.session.recognize_many.assert_not_called()

    def test_cancel_after_fallback_ocr_does_not_accept_result(self):
        self.reader.vision.session.recognize_many.return_value=[words(182)]*4
        check=Mock(side_effect=[None,RuntimeError('F8')])
        with self.assertRaisesRegex(RuntimeError,'F8'):
            self.reader.retry_conflicting_count(self.image,self.box,check,{82:3,182:2})

    def test_iron_blue_icon_corrobates_but_gold_and_white_do_not(self):
        for color,expected in (((20,90,180),True),((210,180,90),False),((240,240,240),False),((40,45,55),False)):
            im=Image.new('RGB',(1280,960),(40,45,55))
            ImageDraw.Draw(im).rectangle((80,282,118,310),fill=color)
            self.assertEqual(self.reader.iron_icon(im,(57,346,151,376)),expected)

    def test_single_blue_pixel_or_blue_quantity_does_not_pass(self):
        im=Image.new('RGB',(1280,960))
        im.putpixel((90,290),(20,90,180))
        ImageDraw.Draw(im).rectangle((82,316,151,341),fill=(20,90,180))
        self.assertFalse(self.reader.iron_icon(im,(57,346,151,376)))

    def test_blue_icon_never_supplies_name_identity(self):
        self.assertIsNone(self.reader.resolve_name({'白銅礦石'}))
        self.assertIsNone(self.reader.resolve_name({'鐵礦石+'}))


if __name__=='__main__':
    unittest.main()
