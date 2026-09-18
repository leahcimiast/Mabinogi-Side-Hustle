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
SPACING = {'page': 12, 'card': 6, 'gap': 6, 'row': 28, 'radius': 8}
WINDOW = {'width': 550, 'expanded': 890, 'height': 850, 'minimum_height': 780}


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

    def rounded(self, fill, border, compact=False):
        size = self.px(28)
        image = Image.new('RGBA', (size * 3, size * 3), COLORS['window'])
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((1, 1, size * 3 - 2, size * 3 - 2),
                               radius=self.px(3 if compact else SPACING['radius']) * 3,
                               fill=fill, outline=border, width=3)
        photo = ImageTk.PhotoImage(image.resize((size, size), Image.Resampling.LANCZOS), master=self.root)
        self.images.append(photo)
        return photo

    def rounded_element(self, name, fill, hover=None, compact=False):
        c = COLORS
        base = self.rounded(fill, c['border'], compact)
        disabled = self.rounded(c['surface'], c['border'], compact)
        focused = self.rounded(fill, c['focus'], compact)
        hovered = self.rounded(hover or fill, c['border'], compact)
        focus_hover = self.rounded(hover or fill, c['focus'], compact)
        pressed = self.rounded(c['selected'], c['focus'], compact)
        self.style.element_create(name, 'image', base,
            ('disabled', disabled), ('pressed', pressed),
            ('focus', 'active', focus_hover), ('focus', focused), ('active', hovered),
            border=self.px(4 if compact else 10), sticky='nsew')

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
            self.rounded_element(element, fill, hover, compact=True)
            s.layout(name, [(element, {'sticky': 'nsew', 'children': [
                ('Button.padding', {'sticky': 'nsew', 'children': [
                    ('Button.label', {'sticky': 'nsew'})]})]})])
            s.configure(name, padding=(self.px(8), self.px(2)), width=0,
                        foreground=c['ink'] if name.startswith('Primary') else c['text'])
            s.map(name, foreground=[('disabled', c['disabled']), ('pressed', c['text'])])
        self.rounded_element('Calm.Entry', c['input'])
        s.layout('TEntry', [('Calm.Entry', {'sticky': 'nsew', 'children': [
            ('Entry.padding', {'sticky': 'nsew', 'children': [('Entry.textarea', {'sticky': 'nsew'})]})]})])
        s.configure('TEntry', fieldbackground=c['input'], foreground=c['text'],
                    insertcolor=c['text'], padding=(self.px(8), self.px(4)), font=(self.en, 10))
        s.map('TEntry', foreground=[('disabled', c['disabled'])])
        # Inline table cells are shorter than the rounded form-entry chrome.
        s.layout('QuestCount.TEntry', [('Entry.field', {'sticky':'nswe','children':[
            ('Entry.padding', {'sticky':'nswe','children':[
                ('Entry.textarea', {'sticky':'nswe'})]})]})])
        s.configure('QuestCount.TEntry', fieldbackground=c['input'], foreground=c['text'],
                    insertcolor=c['text'], padding=0, borderwidth=1, font=(self.zh,10))
        s.configure('TCombobox', fieldbackground=c['input'], background=c['button'],
                    foreground=c['text'], arrowcolor=c['text'], selectbackground=c['input'],
                    selectforeground=c['text'])
        s.map('TCombobox', fieldbackground=[('disabled',c['input']),('readonly',c['input'])],
              foreground=[('disabled',c['text']),('readonly',c['text'])],
              selectbackground=[('disabled',c['input']),('readonly',c['input'])],
              selectforeground=[('disabled',c['text']),('readonly',c['text'])],
              arrowcolor=[('disabled',c['muted'])])
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
                    relief='flat', padding=(self.px(8), self.px(3)), borderwidth=0)
        s.map('Treeview.Heading', background=[('active', c['hover'])])
        s.configure('TNotebook', background=c['window'], borderwidth=0, tabmargins=(0, 4, 0, 8))
        s.configure('TNotebook.Tab', background=c['window'], foreground=c['muted'], padding=(10, 4))
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
        width = min(self.compact_width + (self.px(WINDOW['expanded']-WINDOW['width']) if expanded else 0), self.root.winfo_screenwidth() - 40)
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
                        w.configure(insertbackground=c['text'], padx=8, pady=4, height=15)
                visit(w)
        visit(self.root)
        app.withdraw_button.configure(style='Primary.TButton')
        app.debug.tag_configure('success', foreground=c['success'], background=c['surface'])
        app.debug.tag_configure('failure', foreground=c['danger'], background=c['surface'])
        outer = app.notice.master
        outer.configure(padding=self.px(SPACING['page']))
        app.notice.configure(wraplength=0)
        notice_width=font.Font(root=self.root,font=app.notice.cget('font')).measure(app.notice.cget('text'))
        self.compact_width=max(self.px(WINDOW['width']),notice_width+2*self.px(SPACING['page'])+8)
        self.root.minsize(min(self.compact_width, self.root.winfo_screenwidth() - 40),
                          min(self.px(WINDOW['minimum_height']), self.root.winfo_screenheight() - 80))
        self.root.geometry(f"{min(self.compact_width, self.root.winfo_screenwidth()-40)}x{min(self.px(WINDOW['height']), self.root.winfo_screenheight()-80)}")
        # Existing ttk entry construction (including inline cell editors) inherits TEntry.
        # Wrapping follows the compact window; selecting tabs never resizes it.
        def wrap_labels(event):
            for widget in outer.winfo_children():
                if isinstance(widget, ttk.Label) and widget is not app.notice:
                    widget.configure(wraplength=max(240, event.width-self.px(24)))
        outer.bind('<Configure>', wrap_labels, add='+')
        self.stepper_colors = QuestStepperColors(app.quest_tree, self.zh)
        self.root._desktop_theme = self


def apply_theme(app):
    theme = DesktopTheme(app.root)
    theme.apply(app)
    return theme


class QuestStepperColors:
    """Paint individual cells; clicks and wheel events use the existing Treeview bindings."""
    def __init__(self, tree, family):
        self.tree, self.family = tree, family
        self.labels = {}
        self.heading_images = []
        for column,color in (('minus','#F07178'),('plus','#78C69B')):
            icon = tk.PhotoImage(master=tree,width=14,height=14)
            icon.put(color,to=(3,6,11,8))
            if column=='plus': icon.put(color,to=(6,3,8,11))
            self.heading_images.append(icon)
            tree.heading(column,text='',image=icon,anchor='center')
        self.pending = None
        tree.bind('<Destroy>', self.destroy, add='+')
        original_scroll = tree.cget('yscrollcommand')
        def scrolled(first, last):
            if original_scroll:
                tree.tk.call(*tree.tk.splitlist(original_scroll), first, last)
            self.schedule()
        tree.configure(yscrollcommand=scrolled)
        for event in ('<Configure>', '<<TreeviewSelect>>', '<Map>'):
            tree.bind(event, lambda event: self.schedule(), add='+')

    def destroy(self, event):
        if event.widget is self.tree and self.pending is not None:
            self.tree.after_cancel(self.pending)
            self.pending = None

    def schedule(self):
        if self.pending is None:
            self.pending = self.tree.after_idle(self.refresh)

    def forward(self, label, event, sequence):
        self.tree.event_generate(sequence,
            x=label.winfo_x()+event.x, y=label.winfo_y()+event.y,
            **({'delta':event.delta} if sequence=='<MouseWheel>' else {}))

    def refresh(self):
        if self.pending is not None:
            self.tree.after_cancel(self.pending)
            self.pending = None
        visible = set()
        selected = set(self.tree.selection())
        for row in self.tree.get_children():
            for column, color in (('minus','#F07178'),('plus','#78C69B')):
                box = self.tree.bbox(row, column)
                if not box:
                    continue
                text = self.tree.set(row, column)
                if not text:
                    continue
                key = (row, column)
                visible.add(key)
                label = self.labels.get(key)
                if label is None:
                    label = tk.Label(self.tree, text=text, foreground=color,
                        font=(self.family,11,'bold'), borderwidth=0, padx=0, pady=0,
                        takefocus=False, cursor='hand2')
                    label.bind('<Button-1>', lambda event, w=label: self.forward(w,event,'<Button-1>'))
                    label.bind('<MouseWheel>', lambda event, w=label: self.forward(w,event,'<MouseWheel>'))
                    self.labels[key] = label
                background = (COLORS['selected'] if row in selected else
                              COLORS['active'] if 'active' in self.tree.item(row,'tags') else COLORS['surface'])
                label.configure(text=text, background=background)
                x,y,width,height = box
                label.place(x=x+1,y=y+1,width=max(1,width-2),height=max(1,height-2))
        for key,label in self.labels.items():
            if key not in visible:
                label.place_forget()
