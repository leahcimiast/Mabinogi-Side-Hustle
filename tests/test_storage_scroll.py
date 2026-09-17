import unittest
from unittest.mock import Mock
from PIL import Image,ImageDraw
from app.storage_scroll import panel_moved,scroll_page
import test_fixed_batch as fixtures
from app.flow_vision import Label

class ScrollMotionTests(unittest.TestCase):
    def images(self):
        before=Image.new('RGB',(1280,960),'#303640');after=before.copy()
        ImageDraw.Draw(after).rectangle((120,400,580,510),fill='white')
        return before,after
    def test_retries_when_first_scroll_did_not_move(self):
        before,after=self.images();wheel=Mock();pause=Mock();read=Mock(side_effect=[before,after])
        result,moved=scroll_page(before,wheel,pause,read)
        self.assertTrue(moved);self.assertIs(result,after)
        self.assertEqual(sum(c.args[2]==-1 for c in wheel.call_args_list),30)
    def test_two_stationary_attempts_before_stopping(self):
        before,_=self.images();read=Mock(return_value=before);wheel=Mock()
        _,moved=scroll_page(before,wheel,Mock(),read)
        self.assertFalse(moved);self.assertEqual(read.call_count,2)
    def test_changes_outside_storage_do_not_count_as_scrolling(self):
        before,_=self.images();after=before.copy();ImageDraw.Draw(after).rectangle((700,0,1279,959),fill='white')
        self.assertFalse(panel_moved(before,after))
    def test_cancel_interrupts_scroll_attempt(self):
        before,_=self.images();wheel=Mock()
        with self.assertRaises(RuntimeError):scroll_page(before,wheel,Mock(side_effect=RuntimeError('paused')),Mock())
        self.assertEqual(wheel.call_count,1)

class SearchContinuationTests(unittest.TestCase):
    setUp=fixtures.WithdrawalTests.setUp
    tearDown=fixtures.WithdrawalTests.tearDown
    def test_empty_or_repeated_names_do_not_stop_moving_search(self):
        self.runner.vision.storage_names.side_effect=[[],[],[Label('鐵礦石',(250,350,340,390))]]
        self.runner.scroll_storage=Mock(return_value=(self.screen.image,True))
        self.runner.withdrawal()
        self.assertEqual(self.runner.scroll_storage.call_count,1)
        self.runner.storage_top.assert_called_once()
        self.assertIn('鐵礦石',self.j.data['withdrawn'])
    def test_no_movement_blocks_transfer_and_reports_why(self):
        self.runner.vision.storage_names.return_value=[]
        self.runner.scroll_storage=Mock(return_value=(self.screen.image,False))
        self.runner.withdrawal()
        self.assertIn('無法再向下捲動',self.j.data['skipped']['鐵礦石'])
        self.runner.click.assert_not_called()

    def test_truncated_arrowflower_requires_exact_tooltip_before_transfer(self):
        self.j.data['withdrawn']=[m.name for m in self.j.batch.materials if m.name!='箭花']
        candidate=Label('花',(250,350,340,390))
        self.runner.vision.storage_names.return_value=[candidate]
        self.screen.item_title.return_value=None
        self.screen.tooltip_titles.return_value=[]
        self.runner.withdrawal()
        self.assertEqual(self.runner.click.call_args_list[0].args,(candidate.point,))
        self.screen.item_title.assert_called_with('箭花')
        self.assertNotIn(((960,902),),[c.args for c in self.runner.click.call_args_list])
        self.assertIn('箭花',self.j.data['skipped'])
        self.assertIsNone(self.j.data['pending'])

    def test_duplicate_truncated_arrowflower_is_ambiguous(self):
        self.j.data['withdrawn']=[m.name for m in self.j.batch.materials if m.name!='箭花']
        self.runner.vision.storage_names.return_value=[Label('花',(250,350,340,390)),Label('花',(350,350,440,390))]
        self.runner.withdrawal()
        self.assertIn('多個堆疊',self.j.data['skipped']['箭花'])
        self.runner.click.assert_not_called()

    def test_exact_arrowflower_preferred_over_truncated_candidate(self):
        self.j.data['withdrawn']=[m.name for m in self.j.batch.materials if m.name!='箭花']
        exact=Label('箭花',(350,350,440,390))
        self.runner.vision.storage_names.return_value=[Label('花',(250,350,340,390)),exact]
        self.runner.vision.entered_quantity.return_value=next(m.quantity for m in self.j.batch.materials if m.name=='箭花')
        self.runner.withdrawal()
        self.assertEqual(self.runner.click.call_args_list[0].args,(exact.point,))
        self.assertIn('箭花',self.j.data['withdrawn'])

    def test_premium_wool_is_skipped_until_exact_wool_on_later_page(self):
        self.j.data['withdrawn']=[m.name for m in self.j.batch.materials if m.name!='羊毛']
        premium=Label('高級羊毛',(100,350,190,390))
        truncated=Label('級羊毛',(200,350,290,390))
        wool=Label('羊毛',(350,750,440,790))
        self.runner.vision.storage_names.side_effect=[[premium],[truncated],[wool]]
        self.runner.scroll_storage=Mock(return_value=(self.screen.image,True))
        self.runner.withdrawal()
        self.assertEqual(self.runner.scroll_storage.call_count,1)
        self.runner.storage_top.assert_called_once()
        self.assertEqual(self.runner.click.call_args_list[0].args,(wool.point,))
        self.assertNotIn((premium.point,),[c.args for c in self.runner.click.call_args_list])
        self.assertNotIn((truncated.point,),[c.args for c in self.runner.click.call_args_list])
        self.assertIn('羊毛',self.j.data['withdrawn'])
    def test_only_premium_wool_never_opens_tooltip_or_transfers(self):
        self.j.data['withdrawn']=[m.name for m in self.j.batch.materials if m.name!='羊毛']
        self.runner.vision.storage_names.return_value=[Label('級羊毛',(100,350,190,390))]
        self.runner.scroll_storage=Mock(return_value=(self.screen.image,False))
        self.runner.withdrawal()
        self.assertIn('未找到 羊毛',self.j.data['skipped']['羊毛'])
        self.runner.click.assert_not_called();self.safety.number.assert_not_called()
        self.assertIsNone(self.j.data['pending'])

    def test_onion_typo_is_a_candidate_but_requires_name_review(self):
        from app.name_memory import NameMemory,NameReviewRequired
        from pathlib import Path
        self.j.data['withdrawn']=[m.name for m in self.j.batch.materials if m.name!='洋蔥']
        candidate=Label('洋蒽',(250,350,340,390))
        self.runner.vision.storage_names.return_value=[candidate]
        self.screen.item_title.return_value=None
        self.screen.tooltip_titles.return_value=[]
        self.screen.tooltip_titles.return_value=[candidate]
        self.runner.name_memory=NameMemory(Path(self.temp.name)/'names.json',['洋蔥'])
        self.runner.wait.side_effect=lambda predicate,reason:predicate(self.screen)
        with self.assertRaises(NameReviewRequired) as caught:self.runner.withdrawal()
        self.assertEqual(caught.exception.observed,'洋蒽')
        self.assertEqual(caught.exception.expected,'洋蔥')
        self.assertEqual(self.runner.click.call_args_list[0].args,(candidate.point,))
        self.assertNotIn(((960,902),),[c.args for c in self.runner.click.call_args_list])

    def test_ocr_retries_find_target_before_scrolling_past_it(self):
        self.runner.vision.storage_names.return_value=[]
        self.runner.vision.storage_names_retry.return_value=[Label('鐵礦石',(250,350,340,390))]
        self.runner.scroll_storage=Mock()
        self.runner.withdrawal()
        self.runner.scroll_storage.assert_not_called()
        self.assertIn('鐵礦石',self.j.data['withdrawn'])
    def test_wool_retry_cannot_shorten_premium_at_same_location(self):
        self.j.data['withdrawn']=[m.name for m in self.j.batch.materials if m.name!='羊毛']
        self.runner.vision.storage_names.return_value=[Label('高級羊毛',(100,350,190,390))]
        self.runner.vision.storage_names_retry.return_value=[Label('羊毛',(100,350,190,390))]
        self.runner.scroll_storage=Mock(return_value=(self.screen.image,False))
        self.runner.withdrawal();self.runner.click.assert_not_called()
        self.assertIn('羊毛',self.j.data['skipped'])

    def test_all_methods_run_even_when_first_pass_found_target(self):
        self.runner.withdrawal()
        self.runner.vision.storage_names_retry.assert_called_once_with(self.screen.image)

    def test_visible_item_needs_no_rewind_or_redundant_search_capture(self):
        self.runner.withdrawal()
        self.runner.storage_top.assert_not_called()
        # Initial verified storage screen + final quantity/name read only;
        # the two wait checkpoints supply their own observations in production.
        self.assertEqual(self.runner.screen.call_count,2)
        self.assertEqual(self.runner.wait.call_count,2)
