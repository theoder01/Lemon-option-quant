# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 28, 2026

"""Offline Tk application for new and existing cash-secured Put analysis."""

from datetime import date
from pathlib import Path
import sys
import math
import tkinter as tk
from tkinter import filedialog, ttk

import pandas as pd

from option_quant.gui_i18n import (
    LANGUAGES, Translator, JoinedMessages, message, error_message,
    canonical_message, load_language, save_language,
)
from option_quant.date_picker import DatePicker
from option_quant.gui_branding import apply_branding
from option_quant.runtime_paths import default_database_path, preference_path
from option_quant.gui_theme import COLORS, FONT, PageViewport, apply_theme, scale_for

from option_quant.analytics.put_preview import (
    ReadOnlyOptionDatabase,
    analyze_put_preview,
    latest_reference,
    normalize_underlying,
)
from option_quant.analytics.put_annualized_return import calculate_remaining_annualized_return, RISK_NOTICE
from option_quant.analytics.moneyness import calculate_moneyness
from option_quant.time_utils import now_utc, get_trading_date


class AnalysisPage(ttk.Frame):
    """Shared editing, date selection, translation and result presentation."""

    def close_calendar(self):
        if self.calendar_window is not None and self.calendar_window.winfo_exists():
            self.calendar_window.destroy()

    def reset_analysis(self):
        """Start a fresh contract session without replacing widgets or settings."""
        self.close_calendar()
        self._resetting = True
        try:
            for name, default in self.contract_defaults:
                getattr(self, name).set(default)
            self.expiry_box.configure(values=())
            self.reset_reference_context()
        finally:
            self._resetting = False
        self.invalidate()
        self.set_message(self.status, message(self.initial_status_key))
        self.viewport.canvas.yview_moveto(0)

    def reset_reference_context(self):
        """Page-specific reference state, if any."""

    def ticker_changed(self, *args):
        underlying = self.underlying.get()
        if underlying != self._analysis_underlying:
            self._analysis_underlying = underlying
            self.reset_analysis()

    def numeric_entry(self, master, key, variable):
        # Editing must allow empty/partial text. Existing analysis validates only
        # when Calculate is invoked. Keep native text editing where possible.
        entry = ttk.Entry(master, textvariable=variable, validate="none")
        for sequence in ('<Control-a>', '<Control-A>'):
            entry.bind(sequence, self.select_all_numeric)
        for sequence, action in (
            ('<BackSpace>', 'Backspace'), ('<Delete>', 'Delete'),
            ('<<PrevChar>>', 'prevchar'), ('<<NextChar>>', 'nextchar'),
            ('<<SelectPrevChar>>', 'selectprevchar'),
            ('<<SelectNextChar>>', 'selectnextchar'),
        ):
            entry.bind(sequence, lambda event, action=action: self.edit_numeric(event, action))
        self.numeric_entries[key] = entry
        return entry

    @staticmethod
    def edit_numeric(event, action):
        entry = event.widget
        selecting = action.startswith('select')
        direction = action.removeprefix('select')
        try:
            if action in ('Backspace', 'Delete'):
                entry.tk.call(f'ttk::entry::{action}', str(entry))
            else:
                entry.tk.call('ttk::entry::Extend' if selecting else 'ttk::entry::Move',
                              str(entry), direction)
        except tk.TclError as error:
            if 'cannot open ICU iterator' not in str(error):
                raise
            # Tk 9 can fail before deleting/moving when its ICU iterator cannot
            # open. Numeric text can still be edited using entry character
            # indices. Do not change Tk's global bindings or parse the value.
            if entry.instate(('disabled',)) or entry.instate(('readonly',)):
                return 'break'
            cursor = entry.index('insert')
            if action in ('Backspace', 'Delete'):
                if entry.selection_present():
                    entry.delete('sel.first', 'sel.last')
                elif action == 'Backspace' and cursor > 0:
                    entry.delete(cursor - 1, cursor)
                elif action == 'Delete':
                    entry.delete(cursor, cursor + 1)
            else:
                target = max(0, min(entry.index('end'),
                                    cursor + (-1 if direction == 'prevchar' else 1)))
                if selecting:
                    entry.tk.call('ttk::entry::ExtendTo', str(entry), target)
                else:
                    entry.icursor(target)
                    entry.selection_clear()
            entry.tk.call('ttk::entry::See', str(entry))
        return 'break'

    @staticmethod
    def select_all_numeric(event):
        event.widget.selection_range(0, 'end')
        event.widget.icursor('end')
        return 'break'

    def open_calendar(self):
        if self.calendar_window is not None and self.calendar_window.winfo_exists():
            self.calendar_window.lift()
            return
        today = get_trading_date(now_utc())
        try:
            selected = date.fromisoformat(self.expiry.get().strip())
        except ValueError:
            selected = today
        self.calendar_window = DatePicker(
            self.winfo_toplevel(), selected=selected, today=today,
            translator=self.translator, on_select=self.expiry.set,
        )

    @staticmethod
    def wrap_card(event, labels):
        for label in labels:
            label.configure(wraplength=max(80, event.width - 34))

    def translated(self, value):
        variable = tk.StringVar(master=self)
        self.set_message(variable, value)
        return variable

    def set_message(self, variable, value):
        self._translated_variables[str(variable)] = (variable, value)
        variable.set(self.translator.render(value))
        if hasattr(self,'status_label') and variable is self.status:
            self.refresh_status_style()


    def expiry_controls(self, parent):
        controls = ttk.Frame(parent, style="Surface.TFrame")
        controls.columnconfigure(0, weight=1)
        self.expiry_box = ttk.Combobox(controls, textvariable=self.expiry, width=14)
        self.expiry_box.grid(row=0, column=0, sticky="ew")
        self.calendar_button = ttk.Button(controls,
            textvariable=self.translated(message('calendar_open')), command=self.open_calendar)
        self.calendar_button.grid(row=0, column=1, padx=(6, 0))
        return controls


    def px(self, value):
        return round(value * scale_for(self))

    def label(self, parent, value, style='Body.TLabel'):
        label = ttk.Label(parent, textvariable=self.translated(value), style=style,
                          wraplength=self.px(270), justify='left')
        label.bind('<Configure>', lambda e: label.configure(wraplength=max(60, e.width)))
        return label

    def build_workspace(self, viewport, heading, caption):
        self.viewport = viewport
        body = viewport.body
        self.label(body, message(heading), 'Page.TLabel').grid(row=0,column=0,sticky='ew',pady=(self.px(12),self.px(4)))
        self.label(body, message(caption), 'TLabel').grid(row=1,column=0,sticky='ew',pady=(0,self.px(20)))
        body.columnconfigure(0,weight=1)
        self.columns = ttk.Frame(body)
        self.columns.grid(row=2,column=0,sticky='nsew')
        self.input_panel = ttk.Frame(self.columns,style='Surface.TFrame',padding=self.px(20))
        self.output_panel = ttk.Frame(self.columns)
        self.input_panel.columnconfigure(0,weight=1)
        self.output_panel.columnconfigure(0,weight=1)
        self.input_panel.grid(row=0,column=0,sticky='new',padx=(0,self.px(20)))
        self.output_panel.grid(row=0,column=1,sticky='new')
        self._stacked = None
        def arrange(width):
            stacked = width < self.px(980)
            if stacked == self._stacked: return
            self._stacked = stacked
            self.columns.columnconfigure(0,weight=1 if stacked else 0,minsize=0 if stacked else self.px(320))
            self.columns.columnconfigure(1,weight=0 if stacked else 1)
            self.input_panel.grid_configure(row=0,column=0,sticky='new',padx=(0,0 if stacked else self.px(20)))
            self.output_panel.grid_configure(row=1 if stacked else 0,column=0 if stacked else 1,
                                            pady=(self.px(20) if stacked else 0,0))
        viewport._layout = arrange
        self.label(self.input_panel,message('contract_inputs'),'Heading.TLabel').grid(row=0,column=0,sticky='ew',pady=(0,self.px(16)))

    def field(self, row, key, variable=None, kind='number'):
        frame = ttk.Frame(self.input_panel,style='Surface.TFrame')
        frame.grid(row=row,column=0,sticky='ew',pady=(0,self.px(12)))
        frame.columnconfigure(0,weight=1)
        self.label(frame,message(key),'Muted.TLabel').grid(row=0,column=0,sticky='ew',pady=(0,self.px(5)))
        if kind=='expiry':
            widget=self.expiry_controls(frame)
        elif kind=='ticker':
            widget=ttk.Combobox(frame,textvariable=variable,width=18)
            self.ticker_box=widget
        else:
            widget=self.numeric_entry(frame,key,variable)
            widget.configure(width=18)
        widget.grid(row=1,column=0,sticky='ew')
        return widget

    def build_results(self, specs, existing=False):
        out=self.output_panel
        self.create_cards(out,specs).grid(row=0,column=0,sticky='ew')
        status_frame=ttk.Frame(out,style='Surface.TFrame',padding=self.px(12))
        status_frame.grid(row=1,column=0,sticky='ew',pady=(self.px(12),self.px(12)))
        self.status_label=ttk.Label(status_frame,textvariable=self.status,style='Muted.TLabel',wraplength=self.px(600))
        self.status_label.pack(fill='x')
        self.status_label.bind('<Configure>',lambda e:self.status_label.configure(wraplength=max(60,e.width)))
        self.details_panel=ttk.Frame(out,style='Surface.TFrame',padding=self.px(20))
        self.details_panel.grid(row=2,column=0,sticky='ew')
        self.details_panel.columnconfigure(0,weight=1)
        self.label(self.details_panel,message('calculation_details'),'Heading.TLabel').grid(row=0,column=0,sticky='ew',pady=(0,self.px(12)))
        self.empty_label=self.label(self.details_panel,message('results_empty'),'Muted.TLabel')
        self.empty_label.grid(row=1,column=0,sticky='ew',pady=(self.px(20),self.px(20)))
        self.create_details(self.details_panel,2)
        self.details.grid_remove()
        self.detail_scrollbar.grid_remove()
        risk=ttk.Frame(out,style='Surface.TFrame',padding=self.px(16))
        risk.grid(row=3,column=0,sticky='ew',pady=self.px(12))
        self.label(risk,message('risk_heading'),'Heading.TLabel').pack(fill='x',pady=(0,self.px(6)))
        self.label(risk,canonical_message(RISK_NOTICE),'Muted.TLabel').pack(fill='x')
        if existing:
            self.label(risk,message('remaining_context_notice'),'Muted.TLabel').pack(fill='x',pady=(self.px(8),0))
        else:
            self.label(risk,message('comparison'),'Muted.TLabel').pack(fill='x',pady=(self.px(8),0))
            self.label(risk,message('percentile_explanation'),'Muted.TLabel').pack(fill='x',pady=(self.px(4),0))

    def create_cards(self, parent, specs):
        cards=ttk.Frame(parent)
        self.result_cards=[]
        for col,(title,variable,extras,*unused) in enumerate(specs):
            cards.columnconfigure(col,weight=1,uniform='card')
            frame=ttk.Frame(cards,style='Surface.TFrame',padding=self.px(12))
            frame.grid(row=0,column=col,sticky='nsew',padx=(0,self.px(8)) if col<2 else 0)
            frame.columnconfigure(0,weight=1)
            self.result_cards.append(frame)
            heading=self.label(frame,message(title),'Muted.TLabel')
            heading.grid(row=0,column=0,sticky='ew')
            value=ttk.Label(frame,textvariable=variable,style='Metric.TLabel',wraplength=self.px(180))
            value.grid(row=1,column=0,sticky='ew',pady=(self.px(12),self.px(4)))
            value.bind('<Configure>',lambda e,w=value:w.configure(wraplength=max(60,e.width)))
            # Reserve equal title height while permitting natural value wrapping.
            frame.rowconfigure(0,minsize=self.px(32))
            for index,extra in enumerate(extras):
                label=ttk.Label(frame,textvariable=extra,style='Muted.TLabel',wraplength=self.px(180))
                label.grid(row=index+2,column=0,sticky='ew',pady=(self.px(4),0))
                label.bind('<Configure>',lambda e,w=label:w.configure(wraplength=max(60,e.width)))
        return cards

    def create_details(self,parent,row):
        self.details=tk.Text(parent,height=11,width=1,wrap='word',relief='flat',borderwidth=0,
                             font=(FONT,10),background=COLORS['surface'],foreground=COLORS['text'],
                             padx=0,pady=self.px(4),state='disabled',takefocus=True,
                             highlightthickness=1,highlightbackground=COLORS['surface'],highlightcolor=COLORS['focus'])
        self.details.grid(row=row,column=0,sticky='ew')
        self.detail_scrollbar=ttk.Scrollbar(parent,orient='vertical',command=self.details.yview)
        self.detail_scrollbar.grid(row=row,column=1,sticky='ns')
        self.details.configure(yscrollcommand=self.detail_scrollbar.set)
        self.details.tag_configure('group',font=(FONT,10,'bold'),foreground=COLORS['text'],spacing1=self.px(16),spacing3=self.px(8))
        self.details.tag_configure('label',foreground=COLORS['muted'])
        self.details.tag_configure('value',foreground=COLORS['text'])
        self.details.tag_configure('row',spacing3=self.px(9))
        self.details.tag_configure('note',foreground=COLORS['muted'],spacing3=self.px(10))
        self.details.configure(tabs=(self.px(210),))

    def set_details(self,text):
        self._detail_messages=text
        self.details.configure(state='normal')
        self.details.delete('1.0','end')
        items=text.messages if isinstance(text,JoinedMessages) else (text,)
        groups={name: [] for name in ('detail_returns','detail_contract','detail_history')}
        for item in items:
            key=getattr(item,'key','')
            group=('detail_history' if key.startswith(('iv_','sample_','history_','ratio_','historical_'))
                   else 'detail_returns' if key in ('capital_detail','premium_detail','existing_cash','existing_returns','existing_fee_source','fees_explanation','annual_formula','avoided_fee_explanation')
                   else 'detail_contract')
            rendered=self.translator.render(item)
            if rendered: groups[group].append(rendered)
        for group,paragraphs in groups.items():
            if not paragraphs: continue
            self.details.insert('end',self.translator.render(message(group))+'\n','group')
            for paragraph in paragraphs:
                for line in paragraph.replace(' | ','\n').splitlines():
                    separator='：' if '：' in line else ': '
                    if separator in line and len(line.split(separator,1)[0])<45:
                        label,value=line.split(separator,1)
                        self.details.insert('end',label+separator,'label')
                        self.details.insert('end','\t'+value+'\n',('value','row'))
                    else:
                        self.details.insert('end',line+'\n','note')
        self.details.configure(state='disabled')
        self.details.yview_moveto(0)
        if self.translator.render(text):
            self.empty_label.grid_remove()
            self.details.grid()
            self.detail_scrollbar.grid()
        else:
            self.details.grid_remove()
            self.detail_scrollbar.grid_remove()
            self.empty_label.grid()

    def refresh_status_style(self):
        def keys(value):
            if isinstance(value,JoinedMessages):
                return {key for part in value.messages for key in keys(part)}
            return {getattr(value,'key','')}
        value=self._translated_variables.get(str(self.status),(None,''))[1]
        names=keys(value)
        style=('Error.TLabel' if names & {'calculation_failed','reference_failed'} else
               'Warning.TLabel' if any('unavailable' in k or 'limited' in k or 'insufficient' in k for k in names) else 'Muted.TLabel')
        self.status_label.configure(style=style)

    def toggle_database_path(self):
        if self.database_entry.winfo_manager(): self.database_entry.grid_remove()
        else: self.database_entry.grid()


class PutAnalysisWindow(AnalysisPage):
    contract_defaults = (('expiry', ''), ('premium', ''), ('strike', ''), ('spot', ''))
    initial_status_key = 'initial_status'

    def __init__(self, master, database_path: Path, preference_path: Path | None = None):
        super().__init__(master, padding=0)
        apply_theme(self.winfo_toplevel())
        self.preference_path = preference_path
        self.translator = Translator(load_language(preference_path))
        self._translated_variables = {}
        self._detail_messages = ""
        self.pack(fill="both", expand=True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.database_path = tk.StringVar(value=str(database_path))
        self.underlying = tk.StringVar(value="US.IREN")
        self.expiry = tk.StringVar()
        self.premium = tk.StringVar()
        self.strike = tk.StringVar()
        self.spot = tk.StringVar()
        self.spot_source = self.translated(message('manual_spot_hint'))
        self.status = self.translated(message('initial_status'))
        self.annual_text = tk.StringVar(value="—")
        self.percentile_text = tk.StringVar(value="—")
        self.iv_percentile_text = self.translated("—")
        self.iv_current_text = self.translated("")
        self.iv_status_text = self.translated("")
        self._loading = False
        self._historical_spot = False
        self.calendar_window = None
        self.numeric_entries = {}

        header=ttk.Frame(self,padding=(self.px(24),self.px(12)))
        header.grid(row=0,column=0,sticky='ew')
        header.columnconfigure(1,weight=1)
        self.brand_image = apply_branding(self.winfo_toplevel(), self.px(32))
        self.brand_label = ttk.Label(header, image=self.brand_image)
        self.brand_label.grid(row=0,column=0,padx=(0,self.px(12)))
        ttk.Label(header,textvariable=self.translated(message('app_name')),style='Brand.TLabel').grid(row=0,column=1,sticky='w')
        ttk.Label(header,textvariable=self.translated(message('language'))).grid(row=0,column=2,padx=self.px(12))
        self.language=tk.StringVar(value=LANGUAGES[self.translator.language])
        self.language_box=ttk.Combobox(header,textvariable=self.language,values=tuple(LANGUAGES.values()),state='readonly',width=10)
        self.language_box.grid(row=0,column=3)
        self.language_box.bind('<<ComboboxSelected>>',self.change_language)
        self.preference_status=self.translated('')
        ttk.Label(self,textvariable=self.preference_status).grid(row=1,column=0,sticky='e')
        self.notebook=ttk.Notebook(self)
        self.notebook.grid(row=2,column=0,sticky='nsew',padx=self.px(24),pady=(0,self.px(16)))
        self.new_page=PageViewport(self.notebook)
        self.notebook.add(self.new_page,text=self.translator.render(message('new_position')))
        self.build_workspace(self.new_page,'new_heading','new_caption')
        self.field(1,'underlying',self.underlying,'ticker')
        self.field(2,'expiry',kind='expiry')
        self.field(3,'premium',self.premium)
        self.field(4,'strike',self.strike)
        self.field(5,'spot',self.spot)
        self.reference_button=ttk.Button(self.input_panel,textvariable=self.translated(message('load_reference')),command=self.load_reference)
        self.reference_button.grid(row=6,column=0,sticky='ew',pady=(self.px(4),self.px(8)))
        spot_label=ttk.Label(self.input_panel,textvariable=self.spot_source,style='Muted.TLabel',wraplength=self.px(270))
        spot_label.grid(row=7,column=0,sticky='ew',pady=(0,self.px(12)))
        spot_label.bind('<Configure>',lambda e:spot_label.configure(wraplength=max(60,e.width)))
        self.analyze_button=ttk.Button(self.input_panel,textvariable=self.translated(message('calculate')),style='Primary.TButton',command=self.calculate)
        self.analyze_button.grid(row=8,column=0,sticky='ew',pady=(0,self.px(20)))
        ttk.Separator(self.input_panel).grid(row=9,column=0,sticky='ew',pady=(0,self.px(16)))
        self.label(self.input_panel,message('local_data'),'Muted.TLabel').grid(row=10,column=0,sticky='ew')
        self.database_name=tk.StringVar(value=Path(self.database_path.get()).name)
        name_label=ttk.Label(self.input_panel,textvariable=self.database_name,style='Body.TLabel',wraplength=self.px(270))
        name_label.grid(row=11,column=0,sticky='ew',pady=(self.px(4),self.px(8)))
        name_label.bind('<Configure>',lambda e:name_label.configure(wraplength=max(60,e.width)))
        actions=ttk.Frame(self.input_panel,style='Surface.TFrame')
        actions.grid(row=12,column=0,sticky='ew')
        self.database_button=ttk.Button(actions,textvariable=self.translated(message('choose_file')),command=self.choose_database)
        self.database_button.pack(side='left')
        self.path_button=ttk.Button(actions,textvariable=self.translated(message('show_path')),command=self.toggle_database_path)
        self.path_button.pack(side='left',padx=(self.px(8),0))
        self.database_entry=ttk.Entry(self.input_panel,textvariable=self.database_path,width=18,state='readonly')
        self.database_entry.grid(row=13,column=0,sticky='ew',pady=(self.px(8),0))
        self.database_entry.grid_remove()
        self.database_path.trace_add('write',lambda *args:self.database_name.set(Path(self.database_path.get()).name))
        self.build_results([
            ('historical_percentile',self.percentile_text,[]),
            ('net_annualized_return',self.annual_text,[]),
            ('historical_iv_percentile',self.iv_percentile_text,[self.iv_current_text,self.translated(message('iv_reference_only')),self.iv_status_text]),
        ])
        self.new_page.bind_content()
        self.existing_page=ExistingPositionPage(self.notebook,self)
        self.notebook.add(self.existing_page,text=self.translator.render(message('existing_position')))
        self._active_tab = self.notebook.select()
        self.notebook.bind('<<NotebookTabChanged>>',self.page_changed)
        self.winfo_toplevel().title(self.translator.render(message("window_title")))

        self._analysis_underlying = self.underlying.get()
        self.underlying.trace_add("write", self.ticker_changed)
        self.database_path.trace_add("write", self.database_changed)
        self.spot.trace_add("write", self.spot_changed)
        for var in [self.expiry, self.premium, self.strike]:
            var.trace_add("write", self.invalidate)
        self.reload_symbols()
        self.winfo_toplevel().bind("<Return>", self.on_return)

    def page_changed(self, event=None):
        selected = self.notebook.select()
        if selected == self._active_tab:
            return
        self._active_tab = selected
        # A calendar belongs to its page; dismiss it when navigating away.
        for page in (self, self.existing_page):
            page.close_calendar()
        page = self.existing_page if selected == str(self.existing_page) else self
        page.reset_analysis()

    def on_return(self, event):
        # Confirming a language choice must never trigger a calculation.
        if event.widget is self.language_box:
            return "break"
        page = self.existing_page if self.notebook.select() == str(self.existing_page) else self
        if event.widget is page.calendar_button:
            page.open_calendar()
            return "break"
        page.calculate()

    def change_language(self, event=None):
        language = next(code for code, name in LANGUAGES.items()
                        if name == self.language.get())
        self.translator.language = language
        self.winfo_toplevel().title(self.translator.render(message("window_title")))
        for variable, value in self._translated_variables.values():
            variable.set(self.translator.render(value))
        self.set_details(self._detail_messages)
        self.existing_page.set_details(self.existing_page._detail_messages)
        self.notebook.tab(self.new_page, text=self.translator.render(message('new_position')))
        self.notebook.tab(self.existing_page, text=self.translator.render(message('existing_position')))
        if self.existing_page.calendar_window is not None and self.existing_page.calendar_window.winfo_exists():
            self.existing_page.calendar_window.refresh_language()
        if self.calendar_window is not None and self.calendar_window.winfo_exists():
            self.calendar_window.refresh_language()
        if not save_language(self.preference_path, language):
            self.set_message(self.preference_status, message("preference_not_saved"))
        else:
            self.set_message(self.preference_status, "")

    def invalidate(self, *args):
        if getattr(self, '_resetting', False):
            return
        self.annual_text.set("—")
        self.set_message(self.percentile_text, "—")
        self.set_message(self.iv_percentile_text, "—")
        self.set_message(self.iv_current_text, "")
        self.set_message(self.iv_status_text, "")
        self.set_details("")
        self.set_message(self.status, message('inputs_updated'))

    def reset_reference_context(self):
        self._loading = False
        self._historical_spot = False
        self.set_message(self.spot_source, message('manual_spot_hint'))

    def database_changed(self, *args):
        # Preserve the existing database-change behavior independently of ticker resets.
        self.expiry_box.configure(values=())
        self.spot.set("")
        self._historical_spot = False
        self.set_message(self.spot_source, message('underlying_changed'))
        self.invalidate()
        self.ticker_box.configure(values=())

    def spot_changed(self, *args):
        if getattr(self, '_resetting', False):
            return
        if not self._loading:
            self._historical_spot = False
            self.set_message(self.spot_source, message('manual_spot_source'))
        self.invalidate()

    def choose_database(self):
        path = filedialog.askopenfilename(title=self.translator.render(message('choose_database')), filetypes=[(self.translator.render(message("sqlite_files")), "*.db"), (self.translator.render(message("all_files")), "*.*")])
        if path:
            self.database_path.set(path)
            self.reload_symbols()

    def reload_symbols(self):
        try:
            symbols = ReadOnlyOptionDatabase(self.database_path.get()).underlyings()
            self.ticker_box.configure(values=symbols)
        except Exception as error:
            self.set_message(self.status, message('database_temporarily_unavailable', error=error_message(error)))

    def load_reference(self):
        try:
            underlying = normalize_underlying(self.underlying.get())
            history = ReadOnlyOptionDatabase(self.database_path.get()).load_underlying(underlying)
            price, timestamp, expirations = latest_reference(history, underlying, now_utc())
            self.expiry_box.configure(values=expirations)
            if not self.expiry.get() and expirations:
                self.expiry.set(expirations[0])
            self._loading = True
            self.spot.set("" if price is None else f"{price:g}")
            self._historical_spot = price is not None
            self.set_message(self.spot_source, message('historical_reference', underlying=underlying, timestamp=timestamp) if price is not None else message('no_historical_price'))
            self.set_message(self.status, message('reference_loaded'))
        except Exception as error:
            self.invalidate()
            self.spot.set("")
            self.expiry_box.configure(values=())
            self.set_message(self.status, message('reference_failed', error=error_message(error)))
        finally:
            self._loading = False

    def calculate(self):
        self.invalidate()
        try:
            underlying = normalize_underlying(self.underlying.get())
            try:
                expiry = date.fromisoformat(self.expiry.get().strip())
            except ValueError as error:
                raise ValueError(Translator().render(message("invalid_expiry_format"))) from error
            database_note = ""
            try:
                history = ReadOnlyOptionDatabase(self.database_path.get()).load_underlying(underlying)
            except Exception as error:
                history = pd.DataFrame()
                database_note = message('database_unavailable', error=error_message(error))
            as_of = now_utc()
            result = analyze_put_preview(
                underlying=underlying, expiry=expiry, premium=self.premium.get(),
                strike=self.strike.get(), spot=self.spot.get() if self.spot.get().strip() else None,
                as_of=as_of, history=history,
            )
            annual = result.annual
            self.annual_text.set(f"{annual.annualized_return:.2%}")
            self.set_message(self.percentile_text, f"{result.premium.premium_percentile:.1f}%" if result.premium else message('no_comparable_data'))
            lines = [
                message('contract_detail', underlying=underlying, expiry=expiry),
                message('valuation_detail', as_of=as_of.isoformat(), trading_date=get_trading_date(as_of)),
                message('capital_detail', remaining_days=annual.remaining_days, capital=annual.gross_collateral),
                message('premium_detail', premium_income=float(self.premium.get()) * 100, transaction_fee=annual.transaction_fee, net_premium=annual.potential_profit),
                message('fees_explanation'),
                message('annual_formula'),
            ]
            if result.moneyness is not None:
                lines.append(message('moneyness_detail', moneyness=result.moneyness))
            if result.premium:
                p = result.premium
                lines += [
                    message('sample_detail', sample_count=p.sample_count, trading_days=result.trading_days),
                    message('history_range', start=result.sample_start, end=result.sample_end),
                    message('ratio_detail', current=p.current_premium_ratio, median=p.median_premium_ratio, minimum=p.min_premium_ratio, maximum=p.max_premium_ratio),
                    message('historical_quote_basis'),
                ]
            self.show_iv_reference(result.iv, lines)
            notes = [canonical_message(note) for note in result.notes]
            if database_note:
                notes.append(database_note)
            if self._historical_spot:
                notes.append(message('historical_spot_note'))
            self.set_message(self.status, JoinedMessages(tuple(notes), "message_separator") if notes else message('calculation_complete'))
            self.set_details(JoinedMessages(tuple(lines)))
        except Exception as error:
            self.set_message(self.status, message('calculation_failed', error=error_message(error)))

    def show_iv_reference(self, iv, lines):
        states = {
            "current_unavailable": "iv_current_unavailable",
            "invalid_current": "iv_invalid_current",
            "ambiguous_current": "iv_ambiguous_current",
            "comparison_unavailable": "iv_comparison_unavailable",
            "history_insufficient": "iv_history_insufficient",
        }
        lines.extend([message('iv_details_heading'), message('iv_reference_explanation')])
        if iv.current_iv is not None:
            current = message('iv_current', value=iv.current_iv)
            self.set_message(self.iv_current_text, current)
            lines.append(current)
        if iv.snapshot_time is not None:
            lines.append(message('iv_source', option_code=iv.option_code, timestamp=iv.snapshot_time))
        if iv.status in ("available", "history_insufficient"):
            lines.append(message('iv_sample_count', count=iv.sample_count, days=iv.trading_days))
        else:
            lines.append(message('iv_coverage_unavailable'))
        if iv.analysis is not None:
            self.set_message(self.iv_percentile_text, f"{iv.analysis.iv_percentile:.1f}%")
            lines.extend([
                message('iv_percentile_detail', percentile=iv.analysis.iv_percentile),
                message('iv_statistics', median=iv.analysis.median_iv,
                        minimum=iv.analysis.min_iv, maximum=iv.analysis.max_iv),
            ])
            if iv.limited_history:
                self.set_message(self.iv_status_text, message('iv_limited_history'))
                lines.append(message('iv_limited_history'))
        else:
            note = message(states[iv.status])
            self.set_message(self.iv_status_text, note)
            lines.append(note)
        lines.extend([message('iv_comparison_criteria'), message('iv_percentile_definition')])


class ExistingPositionPage(AnalysisPage):
    """Current-position inputs and presentation; financial values come from analytics."""
    contract_defaults = (('expiry', ''), ('strike', ''), ('close_premium', ''),
                         ('contracts', '1'), ('spot', ''))
    initial_status_key = 'existing_initial_status'

    def __init__(self, master, owner):
        super().__init__(master, padding=0)
        self.translator = owner.translator
        self._translated_variables = owner._translated_variables
        self._detail_messages = ''
        self.numeric_entries = {}
        self.calendar_window = None
        self.result = None
        self.columnconfigure(1, weight=1)
        self.rowconfigure(6, weight=1)
        self.underlying = tk.StringVar(self, value='US.IREN')
        self.expiry = tk.StringVar(self)
        self.strike = tk.StringVar(self)
        self.close_premium = tk.StringVar(self)
        self.contracts = tk.StringVar(self, value='1')
        self.spot = tk.StringVar(self)
        self.annual_text = tk.StringVar(self, value='—')
        self.profit_text = tk.StringVar(self, value='—')
        self.collateral_text = tk.StringVar(self, value='—')
        self.status = self.translated(message('existing_initial_status'))
        viewport=PageViewport(self)
        viewport.pack(fill='both',expand=True)
        self.build_workspace(viewport,'existing_heading','existing_caption')
        self.field(1,'underlying',self.underlying,'ticker').configure(values=('US.NVDA','US.GOOG','US.IREN','US.SPCX'))
        self.field(2,'expiry',kind='expiry')
        for row,key,variable in [(3,'strike_per_share',self.strike),(4,'buyback_premium',self.close_premium),
                                 (5,'contracts',self.contracts),(6,'current_spot',self.spot)]:
            self.field(row,key,variable)
        self.label(self.input_panel,message('buyback_hint'),'Muted.TLabel').grid(row=7,column=0,sticky='ew',pady=(0,self.px(16)))
        self.analyze_button=ttk.Button(self.input_panel,textvariable=self.translated(message('calculate_remaining')),style='Primary.TButton',command=self.calculate)
        self.analyze_button.grid(row=8,column=0,sticky='ew')
        self.build_results([
            ('remaining_annual',self.annual_text,[]),('remaining_profit',self.profit_text,[]),
            ('gross_collateral',self.collateral_text,[]),
        ],existing=True)
        viewport.bind_content()
        self._analysis_underlying = self.underlying.get()
        self.underlying.trace_add('write', self.ticker_changed)
        for variable in (self.expiry, self.strike, self.close_premium, self.contracts, self.spot):
            variable.trace_add('write', self.invalidate)

    def invalidate(self, *args):
        if getattr(self, '_resetting', False):
            return
        self.result = None
        for variable in (self.annual_text, self.profit_text, self.collateral_text):
            variable.set('—')
        self.set_details('')
        self.set_message(self.status, message('inputs_updated'))

    @staticmethod
    def number(value, error_key, *, positive=False):
        try:
            number = float(value)
        except (ValueError, TypeError, OverflowError):
            number = float('nan')
        if not math.isfinite(number) or number < 0 or (positive and number == 0):
            raise ValueError(Translator().render(message(error_key)))
        return number

    def calculate(self):
        self.invalidate()
        try:
            underlying = normalize_underlying(self.underlying.get())
            try:
                expiry = date.fromisoformat(self.expiry.get().strip())
            except ValueError as error:
                raise ValueError(Translator().render(message('invalid_expiry_format'))) from error
            today = get_trading_date(now_utc())
            if expiry <= today:
                raise ValueError(Translator().render(message('future_expiry_required')))
            strike = self.number(self.strike.get(), 'strike_positive', positive=True)
            premium = self.number(self.close_premium.get(), 'buyback_valid')
            spot = self.number(self.spot.get(), 'spot_positive', positive=True)
            count = self.contracts.get().strip()
            if not count.isascii() or not count.isdecimal() or int(count) <= 0:
                raise ValueError(Translator().render(message('contracts_valid')))
            contracts = int(count)
            result = calculate_remaining_annualized_return(
                strike=strike, close_premium=premium, contracts=contracts,
                as_of=today, expiration=expiry, closing_fee=None,
            )
            moneyness = calculate_moneyness(strike, spot)
            position = 'OTM' if spot > strike else 'ATM' if spot == strike else 'ITM'
            self.result = result
            self.annual_text.set(f'{result.annualized_return:.2%}')
            self.profit_text.set(f'${result.potential_profit:,.2f}')
            self.collateral_text.set(f'${result.gross_collateral:,.2f}')
            lines = [
                message('existing_contract_detail', underlying=underlying, expiry=expiry),
                message('existing_prices', spot=spot, strike=strike, premium=premium),
                message('existing_size', contracts=result.contracts, days=result.remaining_days),
                message('existing_cash', collateral=result.gross_collateral,
                        buyback=premium * 100 * result.contracts, fee=result.transaction_fee),
                message('existing_returns', profit=result.potential_profit, period=result.period_return,
                        annual=result.annualized_return),
                message('existing_fee_source', source=canonical_message(result.fee_source)),
                message('avoided_fee_explanation'),
                message('position_context', status=position, moneyness=moneyness),
            ]
            self.set_details(JoinedMessages(tuple(lines)))
            self.set_message(self.status, message('existing_complete'))
        except Exception as error:
            self.set_message(self.status, message('calculation_failed', error=error_message(error)))


def create_root():
    # Keep Windows coordinates consistent with screen pixels on high-DPI displays.
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    root = tk.Tk()
    root.title(Translator().render(message("window_title")))
    scale = max(1, float(root.tk.call("tk", "scaling")) / (96 / 72))
    width = min(int(1280 * scale), root.winfo_screenwidth() - 80)
    height = min(int(940 * scale), root.winfo_screenheight() - 100)
    root.geometry(f"{width}x{height}")
    root.minsize(min(int(760 * scale), width), min(int(620 * scale), height))
    apply_theme(root)
    return root


def main(database_path=None):
    root = create_root()
    PutAnalysisWindow(root, Path(database_path) if database_path else default_database_path(),
                      preference_path())
    root.mainloop()


if __name__ == "__main__":
    main()
