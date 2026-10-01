# Copyright © 2026 Bo Hu. All rights reserved.
"""Small shared light palette and native ttk presentation primitives."""
import tkinter as tk
from tkinter import ttk

COLORS = dict(background='#F6F7F9', surface='#FFFFFF', text='#182230', muted='#667085',
              border='#E4E7EC', accent='#D8E96B', primary='#253344',
              error='#B42318', warning='#805A16', focus='#72852A')
FONT = 'Microsoft YaHei UI'


def scale_for(widget):
    return max(1.0, float(widget.tk.call('tk', 'scaling')) / (96 / 72))


def apply_theme(root):
    style = ttk.Style(root)
    style.theme_use('clam')
    s = scale_for(root)
    pad = lambda n: round(n*s)
    style.configure('.', font=(FONT, 10), background=COLORS['background'], foreground=COLORS['text'])
    style.configure('TFrame', background=COLORS['background'])
    style.configure('Surface.TFrame', background=COLORS['surface'])
    style.configure('TLabel', background=COLORS['background'], foreground=COLORS['text'])
    for name, color, size, weight in [
        ('Body', 'text', 10, 'normal'), ('Muted', 'muted', 9, 'normal'),
        ('Heading', 'text', 12, 'bold'), ('Metric', 'text', 21, 'bold'),
        ('Error', 'error', 9, 'normal'), ('Warning', 'warning', 9, 'normal'),
    ]:
        style.configure(name+'.TLabel', background=COLORS['surface'], foreground=COLORS[color], font=(FONT,size,weight))
    style.configure('Brand.TLabel', font=(FONT,17,'bold'))
    style.configure('Page.TLabel', font=(FONT,16,'bold'))
    style.configure('Accent.TLabel', background=COLORS['accent'], foreground=COLORS['text'], padding=pad(6), font=(FONT,11,'bold'))
    style.configure('TButton', background=COLORS['surface'], bordercolor=COLORS['border'],
                    lightcolor=COLORS['surface'], darkcolor=COLORS['surface'],
                    padding=(pad(12),pad(8)), relief='flat', focusthickness=1, focuscolor=COLORS['focus'])
    style.map('TButton', background=[('active','#EDF0F3')], bordercolor=[('focus',COLORS['focus'])])
    style.configure('Primary.TButton', background=COLORS['primary'], foreground='#FFFFFF', bordercolor=COLORS['primary'])
    style.map('Primary.TButton', background=[('disabled','#D0D5DD'),('active','#36475B')],
              foreground=[('disabled',COLORS['muted']),('!disabled','#FFFFFF')], bordercolor=[('focus',COLORS['focus'])])
    for name in ('TEntry','TCombobox'):
        style.configure(name, fieldbackground=COLORS['surface'], background=COLORS['surface'],
                        foreground=COLORS['text'], bordercolor=COLORS['border'],
                        lightcolor=COLORS['border'], darkcolor=COLORS['border'], padding=pad(7), arrowsize=pad(12))
        style.map(name, bordercolor=[('focus',COLORS['focus'])],
                  fieldbackground=[('disabled','#EFF1F4'),('readonly',COLORS['surface'])],
                  foreground=[('disabled',COLORS['muted'])])
    style.configure('TNotebook', background=COLORS['background'], bordercolor=COLORS['background'], lightcolor=COLORS['background'], darkcolor=COLORS['background'], borderwidth=0, tabmargins=(0,0,0,pad(12)))
    style.configure('TNotebook.Tab', padding=(pad(20),pad(10)), background=COLORS['background'], borderwidth=0)
    style.map('TNotebook.Tab', padding=[('selected',(pad(20),pad(10)))], expand=[('selected',(0,0,0,0))], background=[('selected',COLORS['accent'])], foreground=[('selected',COLORS['text'])])
    style.configure('Vertical.TScrollbar', background='#D0D5DD', troughcolor=COLORS['background'], borderwidth=0, arrowsize=pad(10))
    root.configure(background=COLORS['background'])


class PageViewport(ttk.Frame):
    """Native widgets inside a scrollable, width-limited container; no global bindings."""
    def __init__(self, master):
        super().__init__(master)
        self.scale = scale_for(self)
        self.canvas = tk.Canvas(self, background=COLORS['background'], highlightthickness=0,
                                width=round(1160*self.scale), height=round(690*self.scale))
        self.scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.scrollbar.grid(row=0, column=1, sticky='ns')
        self.body = ttk.Frame(self.canvas)
        self.item = self.canvas.create_window(0,0,anchor='nw',window=self.body)
        self.canvas.bind('<Configure>', self.resize)
        self.body.bind('<Configure>', self.resize)
        self.canvas.bind('<MouseWheel>', self.wheel)
        self._layout = None

    def resize(self, event=None):
        width = max(1, min(self.canvas.winfo_width(), round(1440*self.scale)))
        self.canvas.itemconfigure(self.item,width=width)
        self.canvas.coords(self.item,max(0,(self.canvas.winfo_width()-width)//2),0)
        self.canvas.configure(scrollregion=(0,0,self.canvas.winfo_width(),self.body.winfo_reqheight()))
        if self._layout:
            self._layout(width)

    def wheel(self,event):
        if self.body.winfo_reqheight()>self.canvas.winfo_height():
            self.canvas.yview_scroll(-int(event.delta/120),'units')
        return 'break'

    def bind_content(self):
        def visit(widget):
            # Text owns its scroll wheel; native combobox selection stays native.
            if not isinstance(widget,(tk.Text,ttk.Combobox)):
                widget.bind('<MouseWheel>',self.wheel,add='+')
            if isinstance(widget,(ttk.Entry,ttk.Combobox,ttk.Button,tk.Text)):
                widget.bind('<FocusIn>',self.reveal,add='+')
            elif isinstance(widget,(ttk.Frame,ttk.Label,ttk.Separator)):
                widget.configure(takefocus=False)
            for child in widget.winfo_children(): visit(child)
        visit(self.body)

    def reveal(self,event):
        widget=event.widget
        if not widget.winfo_ismapped(): return
        top=widget.winfo_rooty()-self.canvas.winfo_rooty()
        bottom=top+widget.winfo_height()
        if top<0 or bottom>self.canvas.winfo_height():
            offset=self.canvas.canvasy(0)+top-20*self.scale
            self.canvas.yview_moveto(max(0,offset)/max(1,self.body.winfo_reqheight()))
