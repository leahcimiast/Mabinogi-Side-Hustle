import tkinter as tk
from tkinter import ttk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.stock_check import StockCell, StockResult
from app.stock_ui import StockPanel
from app.whitelist import Quest


ENTRIES = [Quest('shell', '貝類', 10), Quest('wheat', '小麥', 10)]


class StockNumericShortageTests(unittest.TestCase):
    def test_partial_and_unknown_cells_keep_numeric_shortages_with_confidence(self):
        result = StockResult()
        result.add([StockCell(0, 346, '貝類', 12), StockCell(1, 346, None, None, True)], 0)
        self.assertEqual(result.rows(ENTRIES, 1), [('貝類', 30, 12, 18), ('小麥', 30, 0, 30)])
        self.assertEqual(result.uncertain_materials(ENTRIES, 1), {'貝類', '小麥'})
        result.complete = True
        self.assertEqual(result.uncertain_materials(ENTRIES, 1), {'貝類', '小麥'})

    def test_sufficient_stock_is_not_uncertain_even_with_unreadable_other_cells(self):
        result = StockResult()
        result.add([StockCell(0, 346, '貝類', 182), StockCell(1, 346, None, None, True)], 0)
        self.assertEqual(result.rows(ENTRIES, 5)[0], ('貝類', 150, 182, 0))
        self.assertNotIn('貝類', result.uncertain_materials(ENTRIES, 5))


class StockPanelV103Tests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = SimpleNamespace(root=self.root, tabs=ttk.Notebook(self.root), quests=ENTRIES,
                                   busy=False, safety=Mock(hotkey_ok=True), footer=tk.StringVar(),
                                   stop_reason=tk.StringVar(), status=tk.StringVar(),
                                   start_timing=Mock(), refresh=Mock(), log=Mock(), emit=Mock(), fail=Mock())
        self.panel = StockPanel(self.app, Path('.'))

    def tearDown(self):
        self.root.destroy()

    def finished(self):
        result = StockResult(complete=True, finished_at='2026-09-23 19:18:46')
        result.add([StockCell(0, 346, '貝類', 12)], 0)
        self.panel.set_result(result)

    def test_toggle_preserves_observed_stock_and_restores_shortage(self):
        self.finished()
        self.panel.tree.selection_set('貝類')
        self.panel.toggle_collected('貝類')
        self.assertFalse(self.panel.tree.selection())
        self.assertEqual(tuple(map(str,self.panel.tree.item('貝類', 'values'))), ('☑', '貝類', '30', '12', '0'))
        self.assertEqual(self.panel.tree.item('貝類', 'tags'), ('enough',))
        self.assertIn('貝類\t30\t12\t0\t是（手動）', self.panel.text())
        self.assertEqual(self.panel.result.rows(ENTRIES, 1)[0], ('貝類', 30, 12, 18))
        self.panel.toggle_collected('貝類')
        self.assertEqual(str(self.panel.tree.item('貝類', 'values')[-1]), '18')

    def test_toggle_blocked_before_scan_and_while_busy(self):
        self.panel.toggle_collected('貝類')
        self.assertFalse(self.panel.collected)
        self.finished()
        self.app.busy = True
        self.panel.toggle_collected('貝類')
        self.assertFalse(self.panel.collected)

    def test_checkbox_click_sets_keyboard_target_to_clicked_row(self):
        self.finished()
        self.panel.tree.focus('貝類')
        with patch.object(self.panel.tree, 'identify_region', return_value='cell'), \
             patch.object(self.panel.tree, 'identify_column', return_value='#1'), \
             patch.object(self.panel.tree, 'identify_row', return_value='小麥'):
            self.panel.click_collected(SimpleNamespace(x=10, y=40))
        self.assertEqual(self.panel.collected, {'小麥'})
        self.panel.key_collected(None)
        self.assertFalse(self.panel.collected)

    def test_cycles_clear_manual_state_and_preserve_scan_timestamp(self):
        self.finished()
        self.panel.toggle_collected('貝類')
        self.panel.cycles.set('5')
        self.panel.change_cycles()
        self.assertFalse(self.panel.collected)
        self.assertEqual(str(self.panel.tree.item('貝類','values')[-1]), '138')
        self.assertIn('2026-09-23 19:18:46', self.panel.status.get())

    def test_new_scan_clears_manual_state_and_waits_for_finish_timestamp(self):
        self.finished()
        self.panel.toggle_collected('貝類')
        with patch('app.stock_ui.threading.Thread'):
            self.panel.start()
        self.assertFalse(self.panel.collected)
        self.assertEqual(self.panel.scanned_at, '')
        self.assertTrue(self.app.busy)

    def test_success_and_stop_stamp_final_result_in_worker(self):
        for error in (None, RuntimeError('F8')):
            with self.subTest(error=error):
                self.app.busy = False
                self.app.emit.reset_mock()
                self.app.safety.cancelled.wait.return_value = False
                self.app.safety.cancelled.is_set.return_value = False
                result = StockResult(complete=error is None)
                scanner = Mock(result=result)
                scanner.run.return_value = result
                scanner.run.side_effect = error
                with patch('app.stock_ui.threading.Thread') as thread, \
                     patch('app.stock_ui.focus_game'), patch('app.stock_ui.prepare_game'), \
                     patch('app.stock_ui.OcrSession'), patch('app.stock_ui.StockScanner',return_value=scanner), \
                     patch('app.stock_ui.time.strftime', return_value='2026-09-23 20:00:00'):
                    self.panel.start()
                    thread.call_args.kwargs['target']()
                final = [call.args[1] for call in self.app.emit.call_args_list if call.args[0]=='stock_result'][-1]
                self.panel.set_result(final)
                self.assertEqual(self.panel.scanned_at, '2026-09-23 20:00:00')
                self.assertIn('盤點完成' if error is None else '盤點未完成', self.panel.status.get())

    def test_columns_fit_compact_window(self):
        widths = [self.panel.tree.column(column,'minwidth') for column in self.panel.tree['columns']]
        self.assertLessEqual(sum(widths), 480)

    def test_countdown_cancel_is_not_a_finished_scan(self):
        self.app.safety.cancelled.wait.return_value = True
        self.app.safety.reason = 'F8'
        with patch('app.stock_ui.threading.Thread') as thread, patch('app.stock_ui.focus_game'):
            self.panel.start()
            thread.call_args.kwargs['target']()
        final = [call.args[1] for call in self.app.emit.call_args_list if call.args[0]=='stock_result'][-1]
        self.panel.set_result(final)
        self.assertEqual(self.panel.scanned_at, '')
        self.assertIn('盤點未開始：F8', self.panel.status.get())


if __name__ == '__main__':
    unittest.main()
