"""Run-local single-page evidence, without game input or changes to wheel timing."""
import unittest
from unittest.mock import Mock,patch
from PIL import Image,ImageDraw
from app.automation import Runner,SkipMaterial
from app.flow_vision import Label
import test_fixed_batch as fixtures


class RetrievalSinglePageTests(unittest.TestCase):
    setUp=fixtures.WithdrawalTests.setUp
    tearDown=fixtures.WithdrawalTests.tearDown

    def configure(self):
        from test_stock_controls import storage
        self.screen.image=storage()
        draw=ImageDraw.Draw(self.screen.image)
        for i in range(6):draw.rectangle((80+i*90,310+i*40,120+i*90,335+i*40),fill='white')
        self.runner._retrieval_stable_image=Mock(return_value=self.screen.image)
        self.safety.paused_seconds=0
        self.runner.vision.storage_names.return_value=[]
        self.runner.storage_top=Runner.storage_top.__get__(self.runner)
        self.capture_patch=patch('app.automation.capture.capture',return_value=self.screen.image)
        self.capture_patch.start()
        self.addCleanup(self.capture_patch.stop)

    def missing(self,item=None):
        with self.assertRaises(SkipMaterial):
            self.runner.withdraw_one(item or self.runner.batch.materials[0],self.screen)

    def remember(self):
        self.runner._retrieval_single_page=self.runner._retrieval_page_context(self.screen.image)

    def test_first_bounded_both_direction_probe_is_reused_for_later_missing_items(self):
        self.configure()
        self.missing()
        self.assertIsNotNone(self.runner._retrieval_single_page)
        notches=[c.args[-1] for c in self.safety.scroll.call_args_list if c.args[-1]]
        self.assertEqual(notches,[1]*30+[-1]*30)
        calls=self.safety.scroll.call_count
        for item in self.runner.batch.materials[1:3]:self.missing(item)
        self.assertEqual(self.safety.scroll.call_count,calls)
        self.assertEqual(self.runner.vision.storage_names.call_count,8)
        self.assertEqual(self.runner.vision.storage_names_retry.call_count,8)
        self.runner.click.assert_not_called()
        self.safety.click.assert_not_called()
        self.assertIsNone(self.j.data['pending'])
        self.assertAlmostEqual(sum(c.args[0] for c in self.runner.rest.call_args_list),8.4)

    def test_upward_motion_then_bottom_boundary_is_not_single_page(self):
        self.configure()
        image=self.screen.image
        with patch('app.automation.scroll_page',side_effect=[(image,True),(image,False),(image,False)]):
            self.missing()
        self.assertIsNone(self.runner._retrieval_single_page)

    def test_downward_motion_then_boundary_is_not_single_page(self):
        self.configure()
        image=self.screen.image
        with patch('app.automation.scroll_page',side_effect=[(image,False),(image,True),(image,False)]):
            self.missing()
        self.assertIsNone(self.runner._retrieval_single_page)

    def test_final_storage_validation_failure_stops_without_remembering(self):
        self.configure()
        invalid=Mock();invalid.storage.return_value=False
        self.runner.screen.side_effect=[self.screen,self.screen,self.screen,invalid]
        with self.assertRaisesRegex(RuntimeError,'畫面已變更'):
            self.runner.withdraw_one(self.runner.batch.materials[0],self.screen)
        self.assertIsNone(self.runner._retrieval_single_page)
        self.runner.click.assert_not_called()

    def test_control_change_during_probe_does_not_create_single_page_record(self):
        self.configure()
        changed=Mock();changed.storage.return_value=True
        changed.image=self.screen.image.copy()
        ImageDraw.Draw(changed.image).rectangle((100,100,150,125),fill='white')
        self.runner.screen.side_effect=[self.screen,self.screen,self.screen,changed]
        self.missing()
        self.assertIsNone(self.runner._retrieval_single_page)

    def test_each_control_region_change_invalidates_existing_record(self):
        self.configure()
        for box in ((100,35,120,50),(100,100,120,115),(110,150,120,160)):
            with self.subTest(box=box):
                self.remember()
                changed=self.screen.image.copy()
                ImageDraw.Draw(changed).rectangle(box,fill='white')
                self.assertFalse(self.runner._retrieval_single_page_valid(changed))
                self.assertIsNone(self.runner._retrieval_single_page)

    def test_weight_count_and_selection_changes_do_not_invalidate_single_page(self):
        self.configure();self.remember()
        changed=self.screen.image.copy()
        draw=ImageDraw.Draw(changed)
        for box in ((400,220,580,260),(80,300,150,360),(440,670,520,710)):
            draw.rectangle(box,fill='white')
        self.assertTrue(self.runner._retrieval_single_page_valid(changed))

    def test_pause_resume_invalidates_single_page_record(self):
        self.configure();self.remember()
        self.safety.paused_seconds=1.5
        self.assertFalse(self.runner._retrieval_single_page_valid(self.screen.image))
        self.assertIsNone(self.runner._retrieval_single_page)

    def test_new_withdrawal_call_resets_record_even_on_same_runner(self):
        self.configure();self.remember()
        self.runner.withdraw_one=Mock(side_effect=RuntimeError('stop before search'))
        with self.assertRaisesRegex(RuntimeError,'stop before search'):self.runner.withdrawal()
        self.assertIsNone(self.runner._retrieval_single_page)

    def test_present_item_still_uses_current_ocr_position(self):
        self.configure();self.remember()
        target=Label('鐵礦石',(250,350,340,390))
        self.runner.vision.storage_names.return_value=[target]
        self.runner.withdraw_one(self.runner.batch.materials[0],self.screen)
        self.assertEqual(self.runner.click.call_args_list[0].args,(target.point,))
        self.safety.scroll.assert_not_called()
        self.assertIn('鐵礦石',self.j.data['withdrawn'])

    def test_duplicate_or_plus_conflicting_candidates_still_never_transfer(self):
        self.configure()
        for texts in (('鐵礦石','鐵礦石'),('鐵礦石','鐵礦石+')):
            with self.subTest(texts=texts):
                self.remember()
                boxes=((100,350,180,390),(250,350,330,390)) if texts[0]==texts[1] else ((100,350,180,390),)*2
                self.runner.vision.storage_names.return_value=[Label(t,b) for t,b in zip(texts,boxes)]
                self.missing()
                self.runner.click.assert_not_called()
                self.safety.click.assert_not_called()

    def test_stop_after_ocr_never_uses_cached_state_to_skip_or_transfer(self):
        self.configure();self.remember()
        self.safety.check.side_effect=RuntimeError('focus lost')
        with self.assertRaisesRegex(RuntimeError,'focus lost'):
            self.runner.withdraw_one(self.runner.batch.materials[0],self.screen)
        self.runner.click.assert_not_called()
        self.safety.scroll.assert_not_called()
        self.assertIsNone(self.j.data['pending'])


if __name__=='__main__':unittest.main()
