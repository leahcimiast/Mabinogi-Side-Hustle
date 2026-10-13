"""Replay transfer fades and guarded fresh snapshots without game input."""
import unittest
from unittest.mock import Mock,patch
from PIL import Image,ImageDraw,ImageEnhance
from app import retrieval_vision
from app.automation import Runner,ScreenTimeout
from app.flow_vision import Label
from app.storage_scroll import panel_moved,scroll_page
from test_stock_controls import storage
import test_fixed_batch as fixtures


def populated():
    image=storage()
    draw=ImageDraw.Draw(image)
    draw.rectangle((58,275,626,950),fill=(48,52,65))
    for row in range(5):
        for col in range(6):
            x=70+col*95;y=290+row*123
            draw.rectangle((x,y,x+15+row*3,y+20+col*2),fill=(60+row*30,80+col*20,160))
            draw.rectangle((x+5,y+60,x+25+col*3,y+66),fill=(160,160,160))
    return image


class RetrievalPixelsTests(unittest.TestCase):
    def test_fade_is_not_ready_and_cannot_be_declared_scrolled_or_single_page(self):
        image=populated();fade=ImageEnhance.Brightness(image).enhance(.65)
        self.assertTrue(panel_moved(fade,image))
        self.assertFalse(retrieval_vision.ready(fade))
        self.assertFalse(retrieval_vision.stable(fade,image))
        with self.assertRaisesRegex(RuntimeError,'轉場'):retrieval_vision.moved(fade,image,-1)

    def test_whole_panel_brightness_change_must_settle(self):
        image=populated();changed=image.copy()
        region=changed.crop((58,275,626,950))
        changed.paste(ImageEnhance.Brightness(region).enhance(.85),(58,275))
        self.assertTrue(retrieval_vision.ready(changed))
        self.assertFalse(retrieval_vision.stable(image,changed))

    def test_local_highlight_is_not_vertical_list_movement(self):
        image=populated();glow=image.copy()
        ImageDraw.Draw(glow).rectangle((75,290,120,340),outline='white',width=5)
        self.assertTrue(retrieval_vision.stable(image,glow))
        self.assertFalse(retrieval_vision.moved(image,glow,-1))

    def test_actual_overlapping_rows_still_count_as_movement(self):
        image=populated();shifted=image.copy()
        shifted.paste(image.crop((57,365,626,950)),(57,275))
        self.assertTrue(retrieval_vision.moved(image,shifted,-1))

    def test_uncertain_alignment_is_error_not_stationary_edge(self):
        image=populated()
        with patch('app.stock_check.displacement',side_effect=RuntimeError('uncertain alignment')):
            with self.assertRaisesRegex(RuntimeError,'uncertain'):retrieval_vision.moved(image,image,-1)

    def test_optional_movement_check_keeps_original_wheel_timing_and_retry_positions(self):
        image=populated();wheel=Mock();pause=Mock();movement=Mock(return_value=False)
        scroll_page(image,wheel,pause,Mock(return_value=image),movement=movement)
        self.assertEqual([c.args[-1] for c in wheel.call_args_list if c.args[-1]],[-1]*30)
        self.assertAlmostEqual(sum(c.args[0] for c in pause.call_args_list),4.2)
        self.assertEqual(movement.call_count,2)


class RetrievalReadinessTests(unittest.TestCase):
    setUp=fixtures.WithdrawalTests.setUp
    tearDown=fixtures.WithdrawalTests.tearDown

    def configure(self):
        self.safety.paused_seconds=0
        self.image=populated()
        self.runner.retrieval_storage_screen=Runner.retrieval_storage_screen.__get__(self.runner)
        self.elapsed=0
        self.runner.clock=lambda:self.elapsed
        def rest(seconds=.3):
            self.elapsed+=seconds
            self.runner.check()
        self.runner.rest=Mock(side_effect=rest)

    def test_fade_is_discarded_before_storage_ocr_and_fresh_frame_is_returned(self):
        self.configure()
        fade=ImageEnhance.Brightness(self.image).enhance(.65)
        frames=[fade,self.image.copy(),self.image.copy(),self.image.copy()]
        screen=Mock(image=frames[-1]);screen.storage.return_value=True
        self.runner.vision.observe_storage=Mock(return_value=screen)
        with patch('app.automation.capture.capture',side_effect=frames) as capture:
            result=self.runner.retrieval_storage_screen()
        self.assertIs(result,screen)
        self.assertEqual(capture.call_count,4)
        self.runner.vision.observe_storage.assert_called_once_with(frames[-1])
        self.safety.scroll.assert_not_called()

    def test_readiness_timeout_has_no_mouse_or_keyboard_input(self):
        self.configure()
        with patch('app.automation.capture.capture',return_value=Image.new('RGB',(1280,960))):
            with self.assertRaises(ScreenTimeout):self.runner._retrieval_stable_image(.3)
        self.safety.scroll.assert_not_called();self.safety.click.assert_not_called()
        self.safety.key.assert_not_called()

    def test_focus_loss_prevents_capture(self):
        self.configure();self.safety.check.side_effect=RuntimeError('focus lost')
        with patch('app.automation.capture.capture') as capture:
            with self.assertRaisesRegex(RuntimeError,'focus lost'):self.runner._retrieval_stable_image()
        capture.assert_not_called()

    def test_pause_during_capture_discards_pre_pause_frame(self):
        self.configure()
        frames=[self.image.copy() for _ in range(4)]
        def capture(window):
            frame=frames.pop(0)
            if len(frames)==3:self.safety.paused_seconds=1
            return frame
        with patch('app.automation.capture.capture',side_effect=capture) as read:
            result=self.runner._retrieval_stable_image()
        self.assertEqual(read.call_count,4)
        self.assertIsInstance(result,Image.Image)

    def test_pause_during_control_ocr_requires_another_fresh_snapshot(self):
        self.configure()
        self.runner._retrieval_stable_image=Mock(side_effect=[self.image.copy(),self.image.copy()])
        screen=Mock();screen.storage.return_value=True
        def observe(image):
            if self.runner.vision.observe_storage.call_count==1:self.safety.paused_seconds=2
            screen.image=image
            return screen
        self.runner.vision.observe_storage=Mock(side_effect=observe)
        self.runner.retrieval_storage_screen()
        self.assertEqual(self.runner._retrieval_stable_image.call_count,2)


class RetrievalFreshSearchTests(unittest.TestCase):
    setUp=fixtures.WithdrawalTests.setUp
    tearDown=fixtures.WithdrawalTests.tearDown

    def test_empty_first_read_retries_fresh_screen_without_scrolling(self):
        target=Label('鐵礦石',(250,350,340,390))
        self.runner.vision.storage_names.side_effect=[[],[target]]
        self.runner.withdraw_one(self.runner.batch.materials[0],self.screen)
        self.runner.retrieval_storage_screen.assert_called_once()
        self.runner.storage_top.assert_not_called();self.safety.scroll.assert_not_called()
        self.assertEqual(self.runner.vision.storage_names_retry.call_count,2)
        self.assertIn('鐵礦石',self.j.data['withdrawn'])

    def test_failed_fresh_readiness_never_scrolls_or_transfers(self):
        self.runner.vision.storage_names.return_value=[]
        self.runner.retrieval_storage_screen.side_effect=ScreenTimeout('transition')
        with self.assertRaises(ScreenTimeout):self.runner.withdraw_one(self.runner.batch.materials[0],self.screen)
        self.runner.storage_top.assert_not_called();self.safety.click.assert_not_called()
        self.assertIsNone(self.j.data['pending'])

    def test_pause_during_name_ocr_discards_old_item_coordinates(self):
        self.screen.image=populated();self.safety.paused_seconds=0
        old=Label('鐵礦石',(100,300,180,340));fresh=Label('鐵礦石',(250,350,340,390))
        def read(*args,**kwargs):
            if self.runner.vision.storage_names.call_count==1:
                self.safety.paused_seconds=1
                return [old]
            return [fresh]
        self.runner.vision.storage_names.side_effect=read
        self.runner.withdraw_one(self.runner.batch.materials[0],self.screen)
        self.assertEqual(self.runner.click.call_args_list[0].args,(fresh.point,))
        self.runner.retrieval_storage_screen.assert_called_once()
        self.safety.click.assert_called_once()

    def test_repeated_pause_during_name_ocr_stops_without_selection(self):
        self.screen.image=populated();self.safety.paused_seconds=0
        def read(*args,**kwargs):
            self.safety.paused_seconds+=1
            return [Label('鐵礦石',(100,300,180,340))]
        self.runner.vision.storage_names.side_effect=read
        with self.assertRaisesRegex(RuntimeError,'再次改變'):
            self.runner.withdraw_one(self.runner.batch.materials[0],self.screen)
        self.runner.click.assert_not_called();self.safety.click.assert_not_called()

    def test_post_claim_wait_uses_readiness_reader_without_replaying_transfer(self):
        self.runner.withdraw_one(self.runner.batch.materials[0],self.screen)
        self.assertIs(self.runner.wait.call_args.kwargs['reader'],self.runner.retrieval_storage_screen)
        self.safety.click.assert_called_once_with(self.runner.window,960,902)
        self.assertIn('鐵礦石',self.j.data['withdrawn'])


if __name__=='__main__':unittest.main()
