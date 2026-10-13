"""First-tab preparation uses the existing verified stock-control workflow only."""
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from PIL import Image,ImageDraw
from app.automation import Runner
from app.stock_controls import RARITIES
from test_stock_controls import storage,dialog
import test_fixed_batch as fixtures


class RetrievalPreparationTests(unittest.TestCase):
    def runner(self):
        safety=Mock();safety.cancelled=threading.Event()
        journal=Mock();journal.batch=Mock()
        return Runner(Mock(),safety,Mock(),journal,[],Path('scripts/ocr.ps1'))

    def prepare(self,kind='normal',selected=(2,4,6),fail=None):
        runner=self.runner()
        state=dict(kind=kind,selected=set(selected),open=False,all=False,text=True)
        def snapshot(window):
            if not state['open']:return storage(state['kind'],all_items=state['all'])
            image=dialog(state['selected'])
            if state['text']:
                ImageDraw.Draw(image).rectangle((780,175,810,188),fill='white')
            return image
        def click(window,x,y):
            if (x,y)==(198,39) and fail!='shared':state['kind']='shared'
            elif (x,y)==(76,96) and fail!='category':state['all']=True
            elif (x,y)==(55,153) and fail!='filter':state['open']=True
            elif (x,y) in RARITIES and fail!='rarity':
                state['selected'].symmetric_difference_update({RARITIES.index((x,y))})
        def key(window,vk,**kwargs):
            if vk==0x08 and fail!='search':state['text']=False
            elif vk==0x20:state['open']=False
        runner.safety.click.side_effect=click
        runner.safety.key.side_effect=key
        with patch('app.stock_check.capture.capture',side_effect=snapshot),patch('app.stock_check.StockScanner.rest'):
            if fail:
                with self.assertRaises(RuntimeError):runner.prepare_retrieval_storage()
            else:runner.prepare_retrieval_storage()
        return runner,state

    def test_normal_storage_switches_category_clears_search_and_sets_general(self):
        runner,state=self.prepare()
        self.assertEqual(state,dict(kind='shared',selected={0},open=False,all=True,text=False))
        clicks=[c.args[1:] for c in runner.safety.click.call_args_list]
        self.assertEqual(clicks[:3],[(198,39),(76,96),(55,153)])
        self.assertEqual([c.args[1] for c in runner.safety.key.call_args_list],[0x41,0x08,0x20])
        runner.safety.key.assert_any_call(runner.window,0x41,control=True)
        runner.session.recognize_many.assert_not_called()
        self.assertEqual(runner.journal.mock_calls,[])

    def test_shared_general_filter_does_not_toggle_selected_rarity(self):
        runner,state=self.prepare('shared',(0,))
        self.assertEqual(state['selected'],{0})
        clicks=[c.args[1:] for c in runner.safety.click.call_args_list]
        self.assertNotIn((198,39),clicks)
        self.assertFalse(any(point in RARITIES for point in clicks))

    def test_failed_steps_stop_before_applying_filter(self):
        for fail in ('shared','category','filter','rarity','search'):
            with self.subTest(fail=fail):
                runner,_=self.prepare(fail=fail)
                self.assertNotIn(0x20,[c.args[1] for c in runner.safety.key.call_args_list])

    def test_unknown_screen_never_clicks(self):
        runner=self.runner()
        with patch('app.stock_check.capture.capture',return_value=Image.new('RGB',(1280,960))):
            with self.assertRaisesRegex(RuntimeError,'無法確認保管箱'):
                runner.prepare_retrieval_storage()
        runner.safety.click.assert_not_called()

    def test_focus_loss_prevents_capture_and_preparation_inputs(self):
        runner=self.runner();runner.safety.check.side_effect=RuntimeError('focus lost')
        with patch('app.stock_check.capture.capture') as capture:
            with self.assertRaisesRegex(RuntimeError,'focus lost'):runner.prepare_retrieval_storage()
        capture.assert_not_called();runner.safety.click.assert_not_called()


class RetrievalPreparationOrderTests(unittest.TestCase):
    setUp=fixtures.WithdrawalTests.setUp
    tearDown=fixtures.WithdrawalTests.tearDown

    def test_preparation_runs_before_storage_ocr_or_material_selection(self):
        events=Mock()
        events.attach_mock(self.runner.prepare_retrieval_storage,'prepare')
        events.attach_mock(self.runner.screen,'screen')
        self.runner.withdrawal()
        self.assertEqual(events.mock_calls[0][0],'prepare')
        self.runner.prepare_retrieval_storage.assert_called_once_with()

    def test_failed_preparation_never_starts_material_search_or_transfer(self):
        self.runner.prepare_retrieval_storage.side_effect=RuntimeError('filter failed')
        with self.assertRaisesRegex(RuntimeError,'filter failed'):self.runner.withdrawal()
        self.runner.vision.storage_names.assert_not_called()
        self.runner.click.assert_not_called();self.safety.click.assert_not_called()
        self.assertIsNone(self.j.data['pending'])

    def test_pending_journal_blocks_preparation_inputs(self):
        self.j.begin('withdraw','鐵礦石')
        with self.assertRaises(RuntimeError):self.runner.withdrawal()
        self.runner.prepare_retrieval_storage.assert_not_called()
