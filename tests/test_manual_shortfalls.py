import unittest
from unittest.mock import Mock
import test_fixed_batch as fixtures
from app.automation import SkipMaterial,ScreenTimeout
from app.fixed_batch import Journal

class ShortfallTests(unittest.TestCase):
    setUp=fixtures.WithdrawalTests.setUp
    tearDown=fixtures.WithdrawalTests.tearDown
    def test_skip_continues_next_item_and_is_not_retried(self):
        first,second=self.j.batch.materials[:2]
        self.j.data['withdrawn']=[m.name for m in self.j.batch.materials[2:]]
        calls=[]
        def withdraw(item,screen):
            calls.append(item.name)
            if item==first:raise SkipMaterial('not found')
            self.j.begin('withdraw',item.name);self.j.confirm();return screen
        self.runner.withdraw_one=Mock(side_effect=withdraw)
        self.runner.withdrawal()
        self.assertEqual(calls,[first.name,second.name])
        self.assertNotIn(first.name,self.j.data['withdrawn'])
        self.assertIn(second.name,self.j.data['withdrawn'])
        self.runner.withdrawal();self.assertEqual(calls,[first.name,second.name])
        restored=Journal(self.j.path,self.j.batch)
        self.assertEqual(restored.data['skipped'],{first.name:'not found'})
        self.assertNotIn(first.name,restored.data['withdrawn'])
        self.assertIn(second.name,restored.data['withdrawn'])
    def test_pending_transfer_never_becomes_skipped(self):
        def withdraw(item,screen):
            self.j.begin('withdraw',item.name);raise ScreenTimeout('lost confirmation')
        self.runner.withdraw_one=Mock(side_effect=withdraw)
        with self.assertRaises(ScreenTimeout):self.runner.withdrawal()
        self.assertIsNotNone(self.j.data['pending'])
        self.assertEqual(self.j.data['skipped'],{})
    def test_f8_never_becomes_skipped(self):
        self.runner.withdraw_one=Mock(side_effect=SkipMaterial('not found'))
        self.runner.check=Mock(side_effect=RuntimeError('F8'))
        with self.assertRaisesRegex(RuntimeError,'F8'):self.runner.withdrawal()
        self.assertEqual(self.j.data['skipped'],{})
    def test_cancel_only_recognized_overlay(self):
        overlay=Mock();overlay.storage.return_value=False;overlay.quantity_dialog.return_value=True
        self.runner.screen=Mock(side_effect=[overlay,self.screen])
        self.assertIs(self.runner.restore_storage(),self.screen)
        self.runner.key.assert_called_once_with(0x1B)
    def test_unknown_screen_blocks_recovery_input(self):
        unknown=Mock();unknown.storage.return_value=False;unknown.quantity_dialog.return_value=False
        unknown.tooltip_titles.return_value=[];unknown.has.return_value=False
        self.runner.screen=Mock(return_value=unknown)
        with self.assertRaises(RuntimeError):self.runner.restore_storage()
        self.runner.key.assert_not_called()

    def test_closing_animation_does_not_send_escape_twice(self):
        overlay=Mock();overlay.storage.return_value=False;overlay.quantity_dialog.return_value=True
        transient=Mock();transient.storage.return_value=False;transient.quantity_dialog.return_value=False
        transient.tooltip_titles.return_value=[];transient.has.return_value=False
        self.runner.screen=Mock(side_effect=[overlay,overlay,transient,self.screen])
        self.assertIs(self.runner.restore_storage(),self.screen)
        self.runner.key.assert_called_once_with(0x1B)

    def test_two_distinct_overlays_each_cancelled_once(self):
        quantity=Mock();quantity.storage.return_value=False;quantity.quantity_dialog.return_value=True
        tooltip=Mock();tooltip.storage.return_value=False;tooltip.quantity_dialog.return_value=False
        tooltip.tooltip_titles.return_value=['title']
        self.runner.screen=Mock(side_effect=[quantity,quantity,tooltip,tooltip,self.screen])
        self.assertIs(self.runner.restore_storage(),self.screen)
        self.assertEqual(self.runner.key.call_count,2)

    def test_unchanged_overlay_stops_after_bounded_observations(self):
        overlay=Mock();overlay.storage.return_value=False;overlay.quantity_dialog.return_value=True
        self.runner.screen=Mock(return_value=overlay)
        with self.assertRaisesRegex(RuntimeError,'六次'):self.runner.restore_storage()
        self.assertEqual(self.runner.screen.call_count,6)
        self.runner.key.assert_called_once_with(0x1B)

    def test_recovery_pause_stops_before_another_capture(self):
        overlay=Mock();overlay.storage.return_value=False;overlay.quantity_dialog.return_value=True
        self.runner.screen=Mock(return_value=overlay)
        self.runner.rest.side_effect=RuntimeError('F8')
        with self.assertRaisesRegex(RuntimeError,'F8'):self.runner.restore_storage()
        self.assertEqual(self.runner.screen.call_count,1)
