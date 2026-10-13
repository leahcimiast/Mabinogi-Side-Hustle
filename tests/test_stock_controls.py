import threading
import unittest
from unittest.mock import Mock, patch
from PIL import Image, ImageDraw

from app.stock_controls import (RARITIES, PLACEHOLDER_ROWS, all_category, filter_open,
                                only_general, rarity_selected, storage_kind, search_empty)
from app.stock_check import StockScanner, StockCell


def storage(kind='shared', all_items=True):
    image = Image.new('RGB', (1280, 960))
    draw = ImageDraw.Draw(image)
    draw.rectangle((1125, 20, 1170, 55), fill=(12, 190, 123))
    draw.rectangle((42, 135, 73, 171), fill=(12, 190, 123))
    draw.rectangle((45, 390, 57, 880), fill=(48, 52, 65))
    draw.rectangle((680, 390, 695, 880), fill=(23, 32, 39))
    if kind == 'shared':
        draw.rectangle((155, 24, 235, 52), fill=(230, 90, 35))
    elif kind == 'normal':
        draw.rectangle((42, 24, 115, 52), fill=(240, 195, 40))
    if all_items:
        draw.rectangle((48, 81, 100, 111), fill=(230, 90, 35))
    return image


def dialog(selected=()):
    image = Image.new('RGB', (1280, 960), (32, 39, 49))
    draw = ImageDraw.Draw(image)
    draw.rectangle((1000, 881, 1195, 922), fill=(12, 190, 123))
    draw.rectangle((800, 159, 1170, 167), fill=(22, 31, 37))
    placeholder = Image.new('RGB',(122,12))
    placeholder.putdata([(110,110,110) if bit=='1' else (22,31,37)
                         for row in PLACEHOLDER_ROWS for bit in format(int(row,16),'0122b')])
    image.paste(placeholder.resize((244,24)),(774,169))
    for index in selected:
        x, y = RARITIES[index]
        draw.rectangle((x-15, y-22, x+15, y-20), fill='white')
        draw.rectangle((x-15, y+19, x+15, y+21), fill='white')
    return image


class StockControlTests(unittest.TestCase):
    def test_page_requires_panels_live_controls_and_correct_tab_color(self):
        self.assertEqual(storage_kind(storage()), 'shared')
        self.assertEqual(storage_kind(storage('normal')), 'normal')
        self.assertIsNone(storage_kind(storage('unknown')))
        self.assertIsNone(storage_kind(dialog()))
        image = storage(); image.paste('black', (680, 390, 695, 880))
        self.assertIsNone(storage_kind(image))
        self.assertTrue(all_category(storage()))
        self.assertFalse(all_category(storage(all_items=False)))

    def test_selected_outlines_and_multiple_selected_chips(self):
        self.assertTrue(filter_open(dialog()))
        self.assertTrue(only_general(dialog((0,))))
        self.assertFalse(only_general(dialog((0, 2, 6))))
        self.assertEqual([rarity_selected(dialog((0, 2, 6)), i) for i in range(7)],
                         [True, False, True, False, False, False, True])
        image = dialog((0,)); image.paste((32,39,49), (743,315,773,322))
        with self.assertRaisesRegex(RuntimeError, '外框不明確'):
            rarity_selected(image, 0)

    def scanner(self):
        safety = Mock(); safety.cancelled = threading.Event()
        scanner = StockScanner(Mock(), safety, Mock(), [])
        scanner.rest = Mock()
        return scanner

    def run_preparation(self, kind='shared', selected=(0,)):
        scanner = self.scanner()
        state = {'kind': kind, 'open': False, 'selected': set(selected)}
        def capture():
            return dialog(state['selected']) if state['open'] else storage(state['kind'])
        def click(window, x, y):
            if (x, y) == (198, 39): state['kind'] = 'shared'
            elif (x, y) == (55, 153): state['open'] = True
            elif (x, y) in RARITIES:
                index = RARITIES.index((x,y))
                state['selected'].symmetric_difference_update({index})
        def key(window, vk, **kwargs):
            if vk == 0x20: state['open'] = False
        scanner.snapshot = Mock(side_effect=capture)
        scanner.safety.click.side_effect = click
        scanner.safety.key.side_effect = key
        scanner.prepare()
        return scanner, state

    def test_repeat_scan_keeps_general_without_toggling_it(self):
        scanner, state = self.run_preparation()
        self.assertEqual(state['selected'], {0})
        self.assertFalse(any(call.args[1:] in RARITIES for call in scanner.safety.click.call_args_list))
        scanner.vision.session.recognize_many.assert_not_called()
        self.assertEqual([call.args[1] for call in scanner.safety.key.call_args_list], [0x41, 0x08, 0x20])

    def test_normal_storage_switch_and_remove_other_selections(self):
        scanner, state = self.run_preparation('normal', (2, 4, 6))
        self.assertEqual(state['kind'], 'shared')
        self.assertEqual(state['selected'], {0})
        self.assertEqual(scanner.safety.click.call_args_list[0].args[1:], (198,39))

    def test_unknown_screen_does_not_click(self):
        scanner = self.scanner(); scanner.snapshot = Mock(return_value=Image.new('RGB',(1280,960)))
        with self.assertRaisesRegex(RuntimeError, '無法確認保管箱'):
            scanner.prepare()
        scanner.safety.click.assert_not_called()

    def test_failed_filter_open_stops_before_keyboard_actions(self):
        scanner = self.scanner(); scanner.snapshot = Mock(return_value=storage())
        with self.assertRaisesRegex(RuntimeError, '未開啟'):
            scanner.prepare()
        scanner.safety.key.assert_not_called()

    def test_failed_chip_toggle_does_not_apply(self):
        scanner = self.scanner()
        scanner.snapshot = Mock(side_effect=[storage()] + [dialog()] * 20)
        with self.assertRaisesRegex(RuntimeError, '切換結果未確認'):
            scanner.prepare()
        self.assertNotIn(0x20, [call.args[1] for call in scanner.safety.key.call_args_list])

    def test_focus_loss_prevents_capture_and_input(self):
        scanner = self.scanner(); scanner.safety.check.side_effect = RuntimeError('focus lost')
        with patch('app.stock_check.capture.capture') as capture:
            with self.assertRaisesRegex(RuntimeError, 'focus lost'):
                scanner.prepare()
        capture.assert_not_called(); scanner.safety.click.assert_not_called()

    def test_search_needs_positive_placeholder_not_only_no_white_pixels(self):
        self.assertTrue(search_empty(dialog((0,))))
        blank = dialog((0,)); blank.paste((22,31,37),(774,169,1198,196))
        self.assertFalse(search_empty(blank))
        typed = blank.copy(); ImageDraw.Draw(typed).text((780,175),'iron ore',fill='white')
        self.assertFalse(search_empty(typed))
        gray_typed = blank.copy(); ImageDraw.Draw(gray_typed).text((780,175),'iron ore',fill=(100,100,100))
        self.assertFalse(search_empty(gray_typed))
        focused = dialog((0,)); ImageDraw.Draw(focused).rectangle((1015,172,1017,190),fill='white')
        self.assertFalse(search_empty(focused))

    def test_failed_search_clear_or_focus_never_applies(self):
        for white in (True,False):
            scanner = self.scanner()
            typed = dialog((0,)); typed.paste((22,31,37),(774,169,1198,196))
            ImageDraw.Draw(typed).text((780,175),'iron',fill='white' if white else (100,100,100))
            scanner.snapshot = Mock(side_effect=[storage()] + [typed]*20)
            with self.assertRaisesRegex(RuntimeError, '搜尋文字已清空'):
                scanner.prepare()
            self.assertNotIn(0x20,[call.args[1] for call in scanner.safety.key.call_args_list])

    def test_single_page_stock_completes_with_visible_counts(self):
        scanner = self.scanner()
        scanner.prepare = Mock(return_value=storage())
        scanner.screen = Mock(return_value=storage())
        scanner.scroll_batch = Mock(return_value=([],True))
        scanner.move = Mock(return_value=(storage(),0))
        scanner.reader.cells = Mock(return_value=[StockCell(0,346,'貝類',182)])
        scanner.run()
        self.assertTrue(scanner.result.complete)
        self.assertEqual(scanner.result.totals()['貝類'],182)
        self.assertIn('已由頂端掃描到底',scanner.result.note)
        scanner.reader.cells.assert_called_once()

    def test_focus_failure_does_not_enter_partial_page_ocr(self):
        scanner = self.scanner(); scanner.prepare = Mock(return_value=storage())
        scanner.scroll_batch = Mock(return_value=([],True))
        scanner.boundary = Mock(side_effect=RuntimeError('focus lost'))
        scanner.reader.cells = Mock()
        with self.assertRaisesRegex(RuntimeError,'focus lost'):
            scanner.run()
        scanner.reader.cells.assert_not_called()
