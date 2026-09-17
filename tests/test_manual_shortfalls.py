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
        restored.confirm_manual(first.name)
        self.assertIn(first.name,restored.data['manual'])
        self.assertEqual(len(restored.data['withdrawn']),19)
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
    def test_manual_confirmation_blocked_by_unresolved_transfer(self):
        self.j.skip('鐵礦石','missing');self.j.begin('withdraw','鐵礦石')
        with self.assertRaises(RuntimeError):self.j.confirm_manual('鐵礦石')
