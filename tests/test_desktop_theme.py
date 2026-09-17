"""Compatibility checks for appearance-only ttk customization."""
import tkinter as tk
from tkinter import ttk
import unittest
from app.desktop_theme import DesktopTheme, COLORS


class ThemeTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.update_idletasks()
        self.root.destroy()

    def test_existing_button_callback_and_disabled_state(self):
        calls = []
        button = ttk.Button(self.root, command=lambda: calls.append('called'))
        command = button.cget('command')
        DesktopTheme(self.root)
        self.assertEqual(button.cget('command'), command)
        button.invoke()
        button['state'] = 'disabled'
        button.invoke()
        self.assertEqual(calls, ['called'])
        self.assertTrue(button.instate(['disabled']))

    def test_dynamic_editor_keeps_variable_bindings_and_selection(self):
        DesktopTheme(self.root)
        value = tk.StringVar(self.root, value='3')
        entry = ttk.Entry(self.root, textvariable=value)
        entry.bind('<Return>', lambda event: None)
        binding = entry.bind('<Return>')
        entry.selection_range(0, 'end')
        self.assertTrue(entry.selection_present())
        value.set('7')
        self.assertEqual(entry.get(), '7')
        self.assertEqual(entry.bind('<Return>'), binding)
        self.assertEqual(ttk.Style(self.root).lookup('TEntry', 'foreground'), COLORS['text'])

    def test_startup_scaling_and_distinct_button_states(self):
        self.root.tk.call('tk', 'scaling', 2.0)
        theme = DesktopTheme(self.root)
        self.assertGreaterEqual(theme.px(34), 50)
        style = ttk.Style(self.root)
        self.assertEqual(style.lookup('TButton', 'foreground', ('disabled',)), COLORS['disabled'])
        self.assertNotEqual(style.lookup('TButton', 'foreground', ('disabled',)), style.lookup('TButton', 'foreground'))
        self.assertEqual(style.lookup('Treeview', 'background', ('selected',)), COLORS['selected'])
        self.assertTrue(theme.images)
