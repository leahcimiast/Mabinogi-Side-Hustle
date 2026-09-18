import copy
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import tkinter as tk
from PIL import Image
from app.stock_check import (requirements, StockCell, StockResult, StockVision,
                             StockScanner, displacement, parse_count)
from app.flow_vision import Vision, Label
from app.whitelist import Quest
from app.gui import App


ENTRIES = [Quest('a', '鐵礦石', 20), Quest('b', '蜘蛛網', 10)]


def word(text, x=20, y=20):
    return dict(text=text, x=x, y=y, w=40, h=30)


class StockModelTests(unittest.TestCase):
    def test_cycles_and_shared_materials(self):
        entries = ENTRIES + [Quest('c', '鐵礦石', 5)]
        self.assertEqual(requirements(entries, 1), {'鐵礦石':75, '蜘蛛網':30})
        self.assertEqual(requirements(entries, 6), {'鐵礦石':450, '蜘蛛網':180})
        for invalid in (0, 7, True, 1.5, '2'):
            with self.assertRaises(ValueError): requirements(entries, invalid)

    def test_overlap_not_counted_twice_distinct_identical_stacks_counted(self):
        result = StockResult(complete=True)
        result.add([StockCell(0,346,'鐵礦石',25)], 0)
        result.add([StockCell(0,286,'鐵礦石',25),StockCell(1,409,'鐵礦石',25)], 60)
        self.assertEqual(result.rows(ENTRIES,1), [('鐵礦石',60,50,10),('蜘蛛網',30,0,30)])

    def test_missing_vs_unreadable_vs_partial(self):
        result = StockResult(complete=True)
        result.add([StockCell(0,346,'鐵礦石',None,True)],0)
        self.assertEqual(result.rows(ENTRIES,1)[0][3],None)
        self.assertEqual(result.rows(ENTRIES,1)[1][3],30)
        result.complete=False
        self.assertTrue(all(row[3] is None for row in result.rows(ENTRIES,1)))

    def test_confirmed_stack_keeps_previous_count_despite_later_conflict(self):
        result=StockResult(complete=True)
        result.add([StockCell(0,346,'鐵礦石',300)],0)
        result.add([StockCell(0,286,'鐵礦石',800)],60)
        self.assertEqual(result.rows(ENTRIES,1)[0][2:],(300,0))

    def test_excess_clamped_to_zero_and_cycle_recalculation(self):
        result=StockResult(complete=True)
        result.add([StockCell(0,346,'鐵礦石',300)],0)
        self.assertEqual(result.rows(ENTRIES,1)[0][3],0)
        self.assertEqual(result.rows(ENTRIES,6)[0][3],60)

    def test_count_no_abbreviations_or_blank_default(self):
        for text in ('1k','1,000','0','80?'):
            self.assertIsNone(parse_count([word(text)]))
        self.assertIsNone(parse_count([]))
        self.assertEqual(parse_count([word('1234')]),1234)

    def test_alignment_with_overlapping_views(self):
        # Deterministic textured content with stable viewport background.
        import random
        rng=random.Random(4)
        content=Image.frombytes('RGB',(569,1000),rng.randbytes(569*1000*3))
        before=Image.new('RGB',(1280,960));after=before.copy()
        before.paste(content.crop((0,0,569,675)),(57,275))
        after.paste(content.crop((0,61,569,736)),(57,275))
        self.assertEqual(displacement(before,after,-1),61)
        self.assertEqual(displacement(after,before,1),-61)
        self.assertEqual(displacement(before,before,-1),0)

    def test_blank_panel_cannot_prove_alignment_or_end(self):
        with self.assertRaises(RuntimeError):
            displacement(Image.new('RGB',(1280,960)),Image.new('RGB',(1280,960)),-1)


class StockVisionTests(unittest.TestCase):
    def reader(self, labels):
        vision=Mock()
        vision.storage_names.return_value=labels
        vision.storage_names_retry.return_value=[]
        vision._storage_boxes=[(57,346,151,376)]
        return StockVision(vision,ENTRIES)

    def test_counts_require_agreement_and_stay_left(self):
        reader=self.reader([Label('鐵礦石',(57,281,151,341))])
        reader.vision.session.recognize_many.return_value=[
            [word('300',20 if i%2==0 else 140)] for i in range(6)]
        cell=reader.cells(Image.new('RGB',(1280,960)))[0]
        self.assertEqual((cell.name,cell.count,cell.uncertain),('鐵礦石',300,False))
        reader.vision.session.recognize_many.return_value=[
            [word('300' if i<3 else '800',20 if i%2==0 else 140)] for i in range(6)]
        self.assertTrue(reader.cells(Image.new('RGB',(1280,960)))[0].uncertain)

    def test_last_fully_visible_name_row_is_counted(self):
        reader=self.reader([Label('鐵礦石',(57,860,151,920))])
        reader.vision._storage_boxes=[(57,925,151,955)]
        reader.vision.session.recognize_many.return_value=[
            [word('80',20 if i%2==0 else 140)] for i in range(6)]
        self.assertEqual(reader.cells(Image.new('RGB',(1280,960)))[0].count,80)

    def test_grade_plus_conflict_never_counted(self):
        for target, other in [('羊毛','高級羊毛'),('高級原木+','高級原木')]:
            reader=self.reader([Label(target,(57,281,151,341)),Label(other,(57,281,151,341))])
            reader.names={target}
            cell=reader.cells(Image.new('RGB',(1280,960)))[0]
            self.assertTrue(cell.uncertain)
            reader.vision.session.recognize_many.assert_not_called()

    def test_actual_helpers_never_ocr_right_half(self):
        image=Image.new('RGB',(1280,960),(130,130,130))
        image.paste((255,0,0),(640,0,1280,960))
        calls=[]
        session=Mock()
        def recognize(images,**kwargs):
            calls.extend(images)
            return [[] for _ in images]
        session.recognize_many.side_effect=recognize
        vision=Vision(session)
        vision._observe_regions(image,[(35,0,285,180)],variant_count=2)
        StockVision(vision,ENTRIES).cells(image)
        self.assertTrue(calls)
        for crop in calls:
            self.assertNotIn((255,0,0),set(crop.convert('RGB').get_flattened_data()))


class StockScannerTests(unittest.TestCase):
    def scanner(self):
        safety=Mock();safety.cancelled=threading.Event()
        scanner=StockScanner(Mock(),safety,Mock(),ENTRIES)
        scanner.screen=Mock(return_value='top')
        scanner.boundary=Mock(side_effect=lambda image,direction:image)
        return scanner

    def test_full_scan_counts_overlap_and_never_clicks_or_keys(self):
        scanner=self.scanner()
        scanner.move=Mock(side_effect=[('top',0),('next',123),('next',0)])
        scanner.reader.cells=Mock(side_effect=[
            [StockCell(0,469,'鐵礦石',25)],
            [StockCell(0,346,'鐵礦石',25),StockCell(1,469,'鐵礦石',15)]])
        result=scanner.run()
        self.assertTrue(result.complete)
        self.assertEqual(result.rows(ENTRIES,1)[0][2:],(40,20))
        scanner.safety.click.assert_not_called()
        scanner.safety.key.assert_not_called()
        scanner.safety.number.assert_not_called()
        self.assertEqual(scanner.boundary.call_count,2)

    def test_failure_publishes_incomplete_result(self):
        scanner=self.scanner()
        scanner.move=Mock(side_effect=[('top',0),RuntimeError('focus lost')])
        scanner.reader.cells=Mock(return_value=[StockCell(0,346,'鐵礦石',20)])
        published=[]
        scanner.publish=lambda result:published.append(copy.deepcopy(result))
        with self.assertRaisesRegex(RuntimeError,'focus lost'):scanner.run()
        self.assertFalse(published[-1].complete)
        self.assertIsNone(published[-1].rows(ENTRIES,1)[0][3])

    def test_unresponsive_wheel_is_not_end(self):
        scanner=self.scanner()
        scanner.boundary=StockScanner.boundary.__get__(scanner)
        scanner.move=Mock(return_value=('same',0))
        with self.assertRaises(RuntimeError):scanner.run()

    def test_f8_or_focus_failure_prevents_capture(self):
        scanner=StockScanner(Mock(),Mock(),Mock(),ENTRIES)
        scanner.safety.check.side_effect=RuntimeError('F8')
        with patch('app.stock_check.capture.capture') as capture:
            with self.assertRaises(RuntimeError):scanner.screen()
        capture.assert_not_called()


class StockUITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict('os.environ',{'LOCALAPPDATA':self.temp.name});self.env.start()
        self.safety_patch=patch('app.gui.Safety');self.safety=self.safety_patch.start().return_value
        self.safety.hotkey_ok=True;self.safety.reason='paused'
        self.safety.cancelled=threading.Event()
        self.root=tk.Tk();self.root.withdraw();self.app=App(self.root)

    def tearDown(self):
        self.app.close();self.safety_patch.stop();self.env.stop();self.temp.cleanup()

    def test_cycle_change_and_tally_do_not_mutate_journal(self):
        before=copy.deepcopy(self.app.journal.data)
        result=StockResult(complete=True)
        result.add([StockCell(0,346,'鐵礦石',300)],0)
        panel=self.app.stock_panel
        panel.set_result(result);panel.cycles.set('6');panel.render()
        first=panel.tree.item(panel.tree.get_children()[0],'values')
        self.assertEqual(first,('鐵礦石','360','300','60'))
        self.assertEqual(self.app.journal.data,before)
        panel.copy()
        self.assertIn('鐵礦石\t360\t300\t60',self.root.clipboard_get())

    def test_stock_updates_follow_new_material_without_resetting_table(self):
        panel=self.app.stock_panel
        before=copy.deepcopy(self.app.journal.data)
        result=StockResult()
        result.add([StockCell(0,346,'小麥',60)],0)
        with patch.object(panel.tree,'see') as see, patch.object(panel.tree,'delete') as delete:
            panel.set_result(copy.deepcopy(result))
            see.assert_called_once_with('小麥')
            see.reset_mock()
            panel.set_result(copy.deepcopy(result));panel.cycles.set('6');panel.render()
            see.assert_not_called();delete.assert_not_called()
        self.assertEqual(panel.tree.item('小麥','values')[2],'60')
        self.assertEqual(self.app.journal.data,before)

    def test_quest_progress_scrolls_to_current_quest(self):
        self.root.after_cancel(self.app.after_id)
        quest=self.app.quests[-1].quest
        self.app.emit('progress',{'step':'交付中','item':quest,'quantity':1})
        with patch.object(self.app.quest_tree,'see') as see:
            self.app.poll()
            see.assert_called_once_with(str(len(self.app.quests)-1))

    def test_stock_colors_and_clean_numbers_follow_cycle_requirement(self):
        panel=self.app.stock_panel
        result=StockResult();result.add([StockCell(0,346,'鐵礦石',60)],0)
        panel.set_result(result)
        self.assertEqual(panel.tree.item('鐵礦石','tags'),('enough',))
        self.assertEqual(panel.tree.item('蜘蛛網','tags'),('missing',))
        self.assertEqual(panel.tree.item('蜘蛛網','values')[-1],'30')
        panel.cycles.set('2');panel.render()
        self.assertEqual(panel.tree.item('鐵礦石','tags'),('missing',))
        self.assertNotIn('待核',panel.text())

    def test_action_timer_freezes_at_worker_end_and_resets_for_next_action(self):
        self.root.after_cancel(self.app.after_id)
        for name in ('素材領取','任務交付','庫存盤點'):
            with patch('app.gui.time.monotonic',return_value=100):self.app.start_timing(name)
            with patch('app.gui.time.monotonic',return_value=165):self.app.emit('done','完成')
            with patch('app.gui.time.monotonic',return_value=200):self.app.poll()
            self.root.after_cancel(self.app.after_id)
            self.assertEqual(self.app.elapsed.get(),f'耗時：{name} 01:05（已結束）')
        with patch('app.gui.time.monotonic',return_value=300):self.app.start_timing('庫存盤點')
        with patch('app.gui.time.monotonic',return_value=309):self.app.update_timing()
        self.assertEqual(self.app.elapsed.get(),'耗時：庫存盤點 00:09（執行中）')

    def test_active_other_worker_disables_scan(self):
        self.app.busy=True;self.app.refresh()
        self.assertEqual(str(self.app.stock_panel.button['state']),'disabled')
        with patch('app.stock_ui.threading.Thread') as thread:
            self.app.stock_panel.start()
        thread.assert_not_called()

    def test_scan_start_does_not_call_journal_or_runner(self):
        self.safety.cancelled.wait=Mock(return_value=False)
        self.safety.prepare.side_effect=self.safety.cancelled.clear
        before=copy.deepcopy(self.app.journal.data)
        result=StockResult(complete=True,note='done')
        with patch('app.stock_ui.focus_game'),patch('app.stock_ui.prepare_game'),patch('app.stock_ui.OcrSession'), \
             patch('app.stock_ui.StockScanner') as scanner,patch('app.gui.Runner') as runner, \
             patch.object(self.app.journal,'ready') as ready:
            scanner.return_value.run.return_value=result
            self.app.stock_panel.start();self.app.worker.join(5)
            self.assertFalse(self.app.worker.is_alive())
            ready.assert_not_called();runner.assert_not_called()
        self.assertEqual(self.app.journal.data,before)



class StockImprovementTests(unittest.TestCase):
    def test_later_miss_never_erases_tally_and_unknown_can_upgrade(self):
        result=StockResult()
        result.add([StockCell(0,400,'鐵礦石',180),StockCell(1,400,'蜘蛛網',None,True)],0)
        result.add([StockCell(0,350,None,None,True),StockCell(1,350,'蜘蛛網',170)],50)
        self.assertEqual([r[2] for r in result.rows(ENTRIES,1)],[180,170])
        self.assertEqual(len(result.cells),2)

    def test_larger_scroll_and_animation_are_aligned(self):
        import random
        from PIL import ImageDraw
        rng=random.Random(9)
        content=Image.frombytes('RGB',(569,1300),rng.randbytes(569*1300*3))
        before=Image.new('RGB',(1280,960));after=before.copy()
        before.paste(content.crop((0,0,569,675)),(57,275))
        after.paste(content.crop((0,400,569,1075)),(57,275))
        ImageDraw.Draw(after).rectangle((57,350,220,430),fill='lime')
        self.assertEqual(displacement(before,after,-1),400)

    def test_fuzzy_unique_names_preserve_grade_plus_and_material(self):
        from app.whitelist import load
        reader=StockVision(Mock(),load('app/default_whitelist.json'))
        for raw,expected in [('蜘網','蜘蛛網'),('烤整馬薯','烤整顆馬鈴薯'),
                             ('高原木+','高級原木+'),('咻恘蘑菇','咻咻蘑菇'),('馬薯','馬鈴薯')]:
            self.assertEqual(reader.resolve_name({raw}),expected)
        for readings in ({'高級羊毛'},{'級羊毛'},{'高級羊毛','羊毛'},
                         {'高級原木'},{'高級原木+','高級原木'},{'高原木+','高級原木'},
                         {'馬鈴薯','烤整馬薯'},{'白礦石'}):
            self.assertIsNone(reader.resolve_name(readings))

    def test_locked_quantity_is_not_ocr_read_again(self):
        vision=Mock();vision._storage_boxes=[(57,346,151,376)]
        vision.storage_names.return_value=[Label('鐵礦石',(57,281,151,341))]
        vision.storage_names_retry.return_value=[]
        reader=StockVision(vision,ENTRIES)
        cells=reader.cells(Image.new('RGB',(1280,960)),locked={(0,346):StockCell(0,346,'鐵礦石',180)})
        self.assertEqual(cells[0].count,180)
        vision.session.recognize_many.assert_not_called()

    def test_four_notches_are_dispatched_before_item_ocr(self):
        scanner=StockScanner(Mock(),Mock(),Mock(),ENTRIES)
        scanner.rest=Mock();scanner.screen=Mock(return_value='after')
        with patch('app.stock_check.displacement',return_value=300):
            self.assertEqual(scanner.move('before',-1),('after',300))
        self.assertEqual([call.args[-1] for call in scanner.safety.scroll.call_args_list],[-1,-1,-1,-1,0])
        self.assertEqual(scanner.screen.call_count,1)

    def test_later_missed_name_uses_locked_count_without_retry(self):
        vision=Mock();vision._storage_boxes=[(57,346,151,376)]
        vision.storage_names.return_value=[];vision.storage_names_retry.return_value=[]
        reader=StockVision(vision,ENTRIES)
        cells=reader.cells(Image.new('RGB',(1280,960)),locked={(0,346):StockCell(0,346,'鐵礦石',180)})
        self.assertEqual(cells[0].count,180)
        vision.session.recognize_many.assert_not_called()

    def test_known_sufficient_stock_has_zero_shortage_even_if_scan_stops(self):
        result=StockResult()
        result.add([StockCell(0,346,'鐵礦石',180)],0)
        self.assertEqual(result.rows(ENTRIES,1)[0][3],0)
        self.assertIsNone(result.rows(ENTRIES,6)[0][3])


class StockScrollBatchTests(unittest.TestCase):
    def test_four_measured_rows_before_any_ocr_and_redundant_frames_removed(self):
        scanner=StockScanner(Mock(),Mock(),Mock(),ENTRIES)
        scanner.move=Mock(side_effect=[(str(i),90) for i in range(1,7)])
        scanner.reader=Mock()
        frames,at_end=scanner.scroll_batch('start',-1)
        self.assertEqual(frames,[('6',540)])
        self.assertFalse(at_end)
        self.assertGreater(max(call.kwargs['notches'] for call in scanner.move.call_args_list),4)
        self.assertTrue(all(call.kwargs['read_controls'] is False for call in scanner.move.call_args_list))
        scanner.reader.cells.assert_not_called()

    def test_intermediate_frames_prevent_skipping_whole_pages(self):
        scanner=StockScanner(Mock(),Mock(),Mock(),ENTRIES)
        scanner.move=Mock(side_effect=[('1',360),('2',500)])
        frames,_=scanner.scroll_batch('start',-1)
        self.assertEqual(frames,[('1',360),('2',860)])

    def test_boundary_stops_batch_early(self):
        scanner=StockScanner(Mock(),Mock(),Mock(),ENTRIES)
        scanner.move=Mock(side_effect=[('next',150),('end',0)])
        frames,at_end=scanner.scroll_batch('start',-1)
        self.assertTrue(at_end)
        self.assertEqual(frames,[('next',150)])
        self.assertEqual(scanner.move.call_count,2)

    def test_intermediate_capture_has_no_control_or_item_ocr(self):
        scanner=StockScanner(Mock(),Mock(),Mock(),ENTRIES)
        scanner.rest=Mock();scanner.screen=Mock()
        before=Image.new('RGB',(1280,960));after=before.copy()
        with patch('app.stock_check.capture.capture',return_value=after),patch('app.stock_check.displacement',return_value=100):
            scanner.move(before,-1,read_controls=False)
        scanner.screen.assert_not_called()
        scanner.vision.session.recognize_many.assert_not_called()

    def test_changed_header_stops_buffering(self):
        scanner=StockScanner(Mock(),Mock(),Mock(),ENTRIES)
        scanner.rest=Mock();before=Image.new('RGB',(1280,960));after=before.copy()
        after.paste('white',(35,0,285,180))
        with patch('app.stock_check.capture.capture',return_value=after):
            with self.assertRaisesRegex(RuntimeError,'控制區變更'):
                scanner.move(before,-1,read_controls=False)

    def test_half_icon_movements_continue_without_ocr_until_four_rows(self):
        scanner=StockScanner(Mock(),Mock(),Mock(),ENTRIES)
        scanner.move=Mock(side_effect=[(str(i),45) for i in range(1,13)])
        scanner.reader=Mock()
        frames,at_end=scanner.scroll_batch('start',-1)
        self.assertFalse(at_end)
        self.assertEqual(frames,[('12',540)])
        self.assertEqual(scanner.move.call_count,12)
        scanner.reader.cells.assert_not_called()

    def test_tiny_movements_stop_at_bound_without_ocr(self):
        scanner=StockScanner(Mock(),Mock(),Mock(),ENTRIES)
        scanner.move=Mock(return_value=('next',1));scanner.reader=Mock()
        with self.assertRaisesRegex(RuntimeError,'仍未移動 540 px'):
            scanner.scroll_batch('start',-1)
        self.assertEqual(scanner.move.call_count,24)
        scanner.reader.cells.assert_not_called()


class StockLabelRegressionTests(unittest.TestCase):
    def test_reproduced_full_label_confusions_keep_short_names_ambiguous(self):
        from app.whitelist import load
        reader=StockVision(Mock(),load('app/default_whitelist.json'))
        self.assertEqual(reader.resolve_name({'洋', '洋蒽'}),'洋蔥')
        self.assertEqual(reader.resolve_name({'恘恘菇'}),'咻咻蘑菇')
        self.assertEqual(reader.resolve_name({'洋'}),'洋蔥')
        for readings in ({'洋蒽+'}, {'高級洋蒽'}, {'洋蒽','小麥'}):
            self.assertIsNone(reader.resolve_name(readings))


class AdaptiveStockScrollTests(unittest.TestCase):
    def test_adaptive_bursts_keep_one_ocr_page_with_measured_wheel_response(self):
        scanner=StockScanner(Mock(),Mock(),Mock(),ENTRIES)
        position=0
        def move(before,direction,notches,read_controls):
            nonlocal position
            position+=25*notches
            return str(position),25*notches
        scanner.move=Mock(side_effect=move)
        frames,end=scanner.scroll_batch('0',-1)
        self.assertFalse(end)
        self.assertEqual(frames,[('525',525)])
        self.assertEqual(scanner.move.call_count,3)
        self.assertEqual([c.kwargs['notches'] for c in scanner.move.call_args_list],[4,12,5])

class MissingStockCountRetryTests(unittest.TestCase):
    def readings(self, value):
        return [[word(str(value),140 if i<6 and i%2 else 20)] for i in range(8)]

    def reader(self):
        vision=Mock()
        vision.storage_names.return_value=[Label('貝類',(152,753,246,813))]
        vision.storage_names_retry.return_value=[]
        vision._storage_boxes=[(152,818,246,848)]
        return StockVision(vision,[Quest('shell','貝類',10)])

    def test_empty_quantity_recovers_only_from_two_agreeing_positions(self):
        reader=self.reader()
        reader.vision.session.recognize_many.side_effect=[
            [[] for _ in range(8)],self.readings(58),self.readings(58),[[] for _ in range(8)]]
        cell=reader.cells(Image.new('RGB',(1280,960)))[0]
        self.assertEqual((cell.name,cell.count,cell.uncertain),('貝類',58,False))
        self.assertEqual(reader.vision.session.recognize_many.call_count,4)

    def test_single_position_or_disagreement_stays_unknown(self):
        for values in ((58,None,None),(58,59,None),(None,None,None)):
            reader=self.reader()
            reader.vision.session.recognize_many.side_effect=[
                self.readings(value) if value else [[] for _ in range(8)] for value in values]
            self.assertIsNone(reader.retry_missing_count(Image.new('RGB',(1280,960)),(177,778,246,813),lambda:None))

    def test_conflicting_methods_do_not_trigger_crop_retry(self):
        reader=self.reader()
        reader.vision.session.recognize_many.return_value=self.readings(58)[:4]+self.readings(59)[4:]
        cell=reader.cells(Image.new('RGB',(1280,960)))[0]
        self.assertIsNone(cell.count)
        self.assertEqual(reader.vision.session.recognize_many.call_count,1)

    def test_confirmed_count_never_triggers_extra_ocr(self):
        reader=self.reader();reader.vision.session.recognize_many.return_value=self.readings(58)
        self.assertEqual(reader.cells(Image.new('RGB',(1280,960)))[0].count,58)
        self.assertEqual(reader.vision.session.recognize_many.call_count,1)

    def test_cancel_after_retry_ocr_prevents_acceptance_or_more_reads(self):
        reader=self.reader();reader.vision.session.recognize_many.return_value=self.readings(58)
        check=Mock(side_effect=[None,RuntimeError('F8')])
        with self.assertRaisesRegex(RuntimeError,'F8'):
            reader.retry_missing_count(Image.new('RGB',(1280,960)),(177,778,246,813),check)
        self.assertEqual(reader.vision.session.recognize_many.call_count,1)
