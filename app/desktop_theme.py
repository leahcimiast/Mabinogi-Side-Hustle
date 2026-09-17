"""Dark desktop appearance. Keeps existing widgets, commands and event bindings."""
import tkinter as tk
from tkinter import font, ttk
from PIL import Image, ImageDraw, ImageTk

COLORS = {
    'window': '#242628', 'surface': '#2C2E31', 'input': '#26282B',
    'border': '#45494E', 'text': '#E4E3DE', 'muted': '#B1B5BA',
    'button': '#393D42', 'hover': '#484E55', 'selected': '#414E59',
    'accent': '#B9CBD5', 'accent_hover': '#CBD9E0', 'ink': '#252A2E',
    'disabled': '#898F96', 'focus': '#AACBDD', 'success': '#ABD0BB',
    'warning': '#DEC29A', 'danger': '#E5A9A5', 'active': '#3C4038',
}
SPACING = {'page': 20, 'card': 12, 'gap': 12, 'row': 34, 'radius': 8}
WINDOW = {'width': 860, 'expanded': 1200, 'height': 850, 'minimum_height': 780}


class DesktopTheme:
    def __init__(self, root):
        self.root = root
        available = set(font.families(root))
        self.zh = next((f for f in ('Microsoft JhengHei', 'Microsoft JhengHei UI', 'Segoe UI') if f in available), 'TkDefaultFont')
        self.en = 'Segoe UI' if 'Segoe UI' in available else self.zh
        self.scale = float(root.tk.call('tk', 'scaling')) / (96 / 72)
        self.images = []  # Tcl image elements do not retain Python references.
        self.style = ttk.Style(root)
        self.style.theme_use('clam')
        self.configure_styles()
        root.configure(background=COLORS['window'])
        root.option_add('*Font', (self.zh, 10))

    def px(self, value):
        return max(1, round(value * self.scale))

    def rounded(self, fill, border):
        size = self.px(28)
        image = Image.new('RGBA', (size * 3, size * 3), COLORS['window'])
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((1, 1, size * 3 - 2, size * 3 - 2),
                               radius=self.px(SPACING['radius']) * 3,
                               fill=fill, outline=border, width=3)
        photo = ImageTk.PhotoImage(image.resize((size, size), Image.Resampling.LANCZOS), master=self.root)
        self.images.append(photo)
        return photo

    def rounded_element(self, name, fill, hover=None):
        c = COLORS
        base = self.rounded(fill, c['border'])
        disabled = self.rounded(c['surface'], c['border'])
        focused = self.rounded(fill, c['focus'])
        hovered = self.rounded(hover or fill, c['border'])
        focus_hover = self.rounded(hover or fill, c['focus'])
        pressed = self.rounded(c['selected'], c['focus'])
        self.style.element_create(name, 'image', base,
            ('disabled', disabled), ('pressed', pressed),
            ('focus', 'active', focus_hover), ('focus', focused), ('active', hovered),
            border=self.px(10), sticky='nsew')

    def configure_styles(self):
        s, c = self.style, COLORS
        s.configure('.', background=c['window'], foreground=c['text'],
                    font=(self.zh, 10), bordercolor=c['border'],
                    lightcolor=c['border'], darkcolor=c['border'], troughcolor=c['input'])
        s.configure('TFrame', background=c['window'])
        s.configure('TLabel', background=c['window'], foreground=c['text'])
        s.configure('Muted.TLabel', foreground=c['muted'])
        self.rounded_element('Calm.Card', c['window'])
        s.layout('TLabelframe', [('Calm.Card', {'sticky': 'nsew'})])
        s.configure('TLabelframe', background=c['window'], borderwidth=1, relief='flat')
        s.configure('TLabelframe.Label', foreground=c['muted'], background=c['window'])
        for name, fill, hover in [('TButton', c['button'], c['hover']),
                                  ('Primary.TButton', c['accent'], c['accent_hover'])]:
            element = 'Calm.' + name
            self.rounded_element(element, fill, hover)
            s.layout(name, [(element, {'sticky': 'nsew', 'children': [
                ('Button.padding', {'sticky': 'nsew', 'children': [
                    ('Button.label', {'sticky': 'nsew'})]})]})])
            s.configure(name, padding=(self.px(12), self.px(5)), width=0,
                        foreground=c['ink'] if name.startswith('Primary') else c['text'])
            s.map(name, foreground=[('disabled', c['disabled']), ('pressed', c['text'])])
        self.rounded_element('Calm.Entry', c['input'])
        s.layout('TEntry', [('Calm.Entry', {'sticky': 'nsew', 'children': [
            ('Entry.padding', {'sticky': 'nsew', 'children': [('Entry.textarea', {'sticky': 'nsew'})]})]})])
        s.configure('TEntry', fieldbackground=c['input'], foreground=c['text'],
                    insertcolor=c['text'], padding=(self.px(8), self.px(4)), font=(self.en, 10))
        s.map('TEntry', foreground=[('disabled', c['disabled'])])
        s.configure('TSpinbox', fieldbackground=c['input'], foreground=c['text'], arrowsize=self.px(12))
        s.configure('TCheckbutton', background=c['window'], foreground=c['text'],
                    indicatorbackground=c['input'], indicatorforeground=c['ink'],
                    indicatormargin=(0, 0, self.px(8), 0), padding=3)
        s.map('TCheckbutton', background=[('active', c['surface'])],
              foreground=[('disabled', c['disabled'])],
              indicatorbackground=[('disabled', c['button']), ('selected', c['accent'])],
              bordercolor=[('focus', c['focus'])])
        s.configure('Treeview', background=c['surface'], fieldbackground=c['surface'],
                    foreground=c['text'], borderwidth=0, bordercolor=c['surface'],
                    lightcolor=c['surface'], darkcolor=c['surface'], relief='flat',
                    rowheight=self.px(SPACING['row']))
        s.map('Treeview', background=[('selected', c['selected'])],
              foreground=[('selected', c['text'])], bordercolor=[('focus', c['focus'])])
        s.configure('Treeview.Heading', background=c['button'], foreground=c['muted'],
                    relief='flat', padding=(self.px(10), self.px(8)), borderwidth=0)
        s.map('Treeview.Heading', background=[('active', c['hover'])])
        s.configure('TNotebook', background=c['window'], borderwidth=0, tabmargins=(0, 4, 0, 8))
        s.configure('TNotebook.Tab', background=c['window'], foreground=c['muted'], padding=(16, 8))
        s.map('TNotebook.Tab', background=[('selected', c['selected']), ('active', c['hover'])],
              foreground=[('selected', c['text'])], lightcolor=[('focus', c['focus'])])
        s.layout('Horizontal.TProgressbar', [('Horizontal.Progressbar.trough', {'sticky': 'nswe', 'children': [('Horizontal.Progressbar.pbar', {'side': 'left', 'sticky': 'ns'})]})])
        s.configure('Horizontal.TProgressbar', background=c['accent'], troughcolor=c['button'],
                    borderwidth=0, lightcolor=c['accent'], darkcolor=c['accent'], thickness=self.px(5))
        for direction in ('Vertical', 'Horizontal'):
            name = direction + '.TScrollbar'
            s.configure(name, background=c['border'], troughcolor=c['surface'],
                        borderwidth=0, arrowsize=self.px(12), arrowcolor=c['muted'])
            s.map(name, background=[('active', c['hover']), ('pressed', c['selected'])])
        s.configure('TPanedwindow', background=c['window'])

    def resize(self, expanded=False):
        width = min(self.px(WINDOW['expanded' if expanded else 'width']), self.root.winfo_screenwidth() - 40)
        height = self.root.winfo_height()
        if height < 100:
            height = min(self.px(WINDOW['height']), self.root.winfo_screenheight() - 80)
        self.root.geometry(f'{width}x{height}')

    def apply(self, app):
        c = COLORS
        def visit(parent):
            for w in parent.winfo_children():
                if isinstance(w, ttk.Label):
                    old = str(w.cget('foreground'))
                    if old in ('#c62828', '#a03224'):
                        w.configure(foreground=c['warning' if old == '#c62828' else 'danger'])
                    if w.cget('font'):
                        previous = font.Font(root=self.root, font=w.cget('font'))
                        w.configure(font=(self.zh, previous.actual('size'), previous.actual('weight')))
                elif isinstance(w, ttk.Treeview):
                    w.configure(height=5)
                    w.tag_configure('active', background=c['active'])
                    w.tag_configure('done', foreground=c['success'])
                elif isinstance(w, (tk.Text, tk.Listbox)):
                    w.configure(background=c['input'], foreground=c['text'], relief='flat',
                                borderwidth=0, highlightthickness=1, highlightbackground=c['border'],
                                highlightcolor=c['focus'], selectbackground=c['selected'],
                                selectforeground=c['text'], font=(self.zh, 10))
                    if isinstance(w, tk.Text):
                        w.configure(insertbackground=c['text'], padx=10, pady=8, height=6)
                visit(w)
        visit(self.root)
        # Keep debug actions visible when recovery leaves a short log pane.
        for w in app.debug_panel.winfo_children():
            if isinstance(w, ttk.Button) and str(w.cget('text')) == '清除已記住的名稱':
                w.pack_configure(side='bottom', before=app.debug_panel.pack_slaves()[0])
        app.withdraw_button.configure(style='Primary.TButton')
        app.debug.tag_configure('success', foreground=c['success'], background=c['surface'])
        app.debug.tag_configure('failure', foreground=c['danger'], background=c['surface'])
        outer = app.notice.master
        outer.configure(padding=self.px(SPACING['page']))
        # Pack fixed footer first so resizing/recovery panels cannot push it offscreen.
        footer = [w for w in outer.winfo_children() if isinstance(w, ttk.Label)
                  and (str(w.cget('textvariable')) == str(app.footer) or str(w.cget('text')).startswith('紀錄檔：'))]
        for w in reversed(footer):
            w.pack_configure(side='bottom', fill='x', before=app.notice)
            w.configure(style='Muted.TLabel')
        self.root.minsize(min(self.px(800), self.root.winfo_screenwidth() - 40),
                          min(self.px(WINDOW['minimum_height']), self.root.winfo_screenheight() - 80))
        self.root.geometry(f"{min(self.px(WINDOW['width']), self.root.winfo_screenwidth()-40)}x{min(self.px(WINDOW['height']), self.root.winfo_screenheight()-80)}")
        # Existing ttk entry construction (including inline cell editors) inherits TEntry.
        self.root._desktop_theme = self


def apply_theme(app):
    theme = DesktopTheme(app.root)
    theme.apply(app)
    return theme
