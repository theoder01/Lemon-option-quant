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

    def set_details(self, text):
        self._detail_messages = text
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", self.translator.render(text))
        self.details.configure(state="disabled")

    def create_cards(self, parent, specs):
        cards = ttk.Frame(parent)
        self.result_cards = []
        for col, (title, variable, extras, color) in enumerate(specs):
            cards.columnconfigure(col, weight=1, uniform="card")
            frame = ttk.LabelFrame(cards, padding=15)
            self.result_cards.append(frame)
            heading = ttk.Label(frame, textvariable=self.translated(message(title)), wraplength=230)
            frame.configure(labelwidget=heading)
            frame.grid(row=0, column=col, sticky="nsew", padx=(0, 8) if col == 0 else (8, 0))
            value = ttk.Label(frame, textvariable=variable, wraplength=230,
                              font=("Microsoft YaHei UI", 27, "bold"), foreground=color)
            value.pack(anchor="w", fill="x")
            labels = [heading, value]
            for extra in extras:
                label = ttk.Label(frame, textvariable=extra, wraplength=230)
                label.pack(anchor="w", fill="x", pady=(3, 0))
                labels.append(label)
            frame.bind("<Configure>", lambda event, labels=labels: self.wrap_card(event, labels))
        return cards

    def create_details(self, parent, row):
        self.details = tk.Text(parent, height=11, wrap="word", relief="flat", padx=12,
                               pady=10, font=("Microsoft YaHei UI", 10),
                               background="#f3f5f4", state="disabled")
        self.details.grid(row=row, column=0, columnspan=3, sticky="nsew")
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.details.yview)
        scrollbar.grid(row=row, column=3, sticky="ns")
        self.details.configure(yscrollcommand=scrollbar.set)

    def expiry_controls(self, parent):
        controls = ttk.Frame(parent)
        controls.columnconfigure(0, weight=1)
        self.expiry_box = ttk.Combobox(controls, textvariable=self.expiry, width=14)
        self.expiry_box.grid(row=0, column=0, sticky="ew")
        self.calendar_button = ttk.Button(controls,
            textvariable=self.translated(message('calendar_open')), command=self.open_calendar)
        self.calendar_button.grid(row=0, column=1, padx=(6, 0))
        return controls


class PutAnalysisWindow(AnalysisPage):
    def __init__(self, master, database_path: Path, preference_path: Path | None = None):
        super().__init__(master, padding=22)
        self.preference_path = preference_path
        self.translator = Translator(load_language(preference_path))
        self._translated_variables = {}
        self._detail_messages = ""
        self.pack(fill="both", expand=True)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(3, weight=1)
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

        ttk.Label(self, textvariable=self.translated(message('app_name')), font=("Microsoft YaHei UI", 20, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=(12, 0))
        self.new_page = ttk.Frame(self.notebook, padding=8)
        self.new_page.columnconfigure(1, weight=1)
        self.new_page.rowconfigure(10, weight=1)
        self.notebook.add(self.new_page, text=self.translator.render(message('new_position')))
        ttk.Label(self.new_page, textvariable=self.translated(message('subtitle'))).grid(row=1, column=0, columnspan=3, sticky="w", pady=(3, 18))
        ttk.Label(self.new_page, textvariable=self.translated(message('database'))).grid(row=2, column=0, sticky="w", padx=(0, 14))
        ttk.Entry(self.new_page, textvariable=self.database_path).grid(row=2, column=1, sticky="ew")
        ttk.Button(self.new_page, textvariable=self.translated(message('choose_file')), command=self.choose_database).grid(row=2, column=2, padx=(8, 0))

        inputs = ttk.LabelFrame(self.new_page, padding=14)
        inputs.configure(labelwidget=ttk.Label(inputs, textvariable=self.translated(message('contract_inputs'))))
        inputs.grid(row=3, column=0, columnspan=3, sticky="ew", pady=14)
        inputs.columnconfigure(1, weight=1)
        inputs.columnconfigure(3, weight=1)
        ttk.Label(inputs, textvariable=self.translated(message('underlying'))).grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.ticker_box = ttk.Combobox(inputs, textvariable=self.underlying, width=20)
        self.ticker_box.grid(row=0, column=1, sticky="ew")
        ttk.Label(inputs, textvariable=self.translated(message('expiry'))).grid(row=0, column=2, padx=(22, 12))
        expiration_controls = self.expiry_controls(inputs)
        expiration_controls.grid(row=0, column=3, sticky="ew")
        ttk.Label(inputs, textvariable=self.translated(message('expiry_hint'))).grid(row=1, column=2, columnspan=2, sticky="w", padx=(22, 0), pady=(4, 8))
        for column, key, variable in [(0, 'premium', self.premium), (2, 'strike', self.strike)]:
            label = message(key)
            ttk.Label(inputs, textvariable=self.translated(label)).grid(row=2, column=column, sticky="w", padx=(0 if column == 0 else 22, 12))
            entry = self.numeric_entry(inputs, key, variable)
            entry.grid(row=2, column=column + 1, sticky="ew")
        ttk.Label(inputs, textvariable=self.translated(message('spot'))).grid(row=3, column=0, sticky="w", pady=(14, 0))
        self.numeric_entry(inputs, 'spot', self.spot).grid(row=3, column=1, sticky="ew", pady=(14, 0))
        self.reference_button = ttk.Button(inputs, textvariable=self.translated(message('load_reference')), command=self.load_reference)
        self.reference_button.grid(row=3, column=2, columnspan=2, sticky="ew", padx=(22, 0), pady=(14, 0))
        ttk.Label(inputs, textvariable=self.spot_source, wraplength=740, foreground="#806019").grid(row=4, column=0, columnspan=4, sticky="w", pady=(10, 0))
        self.analyze_button = ttk.Button(self.new_page, textvariable=self.translated(message('calculate')), command=self.calculate)
        self.analyze_button.grid(row=4, column=0, columnspan=3, sticky="ew", ipady=6)
        ttk.Label(self.new_page, textvariable=self.status, wraplength=820, foreground="#805800").grid(row=5, column=0, columnspan=3, sticky="w", pady=10)

        cards = self.create_cards(self.new_page, [
            ('historical_percentile', self.percentile_text, [], '#186a56'),
            ('net_annualized_return', self.annual_text, [], '#186a56'),
            ('historical_iv_percentile', self.iv_percentile_text,
             [self.iv_current_text, self.translated(message('iv_reference_only')), self.iv_status_text], '#465767'),
        ])
        cards.grid(row=6, column=0, columnspan=3, sticky="ew")
        ttk.Label(self.new_page, textvariable=self.translated(message('comparison')), wraplength=820).grid(row=7, column=0, columnspan=3, sticky="w", pady=(14, 3))
        ttk.Label(self.new_page, textvariable=self.translated(message('percentile_explanation')), wraplength=820).grid(row=8, column=0, columnspan=3, sticky="w")
        ttk.Label(self.new_page, textvariable=self.translated(message('details_heading')), font=("Microsoft YaHei UI", 11, "bold")).grid(row=9, column=0, columnspan=3, sticky="w", pady=(14, 5))
        self.create_details(self.new_page, 10)
        ttk.Label(self.new_page, textvariable=self.translated(message('risk_notice')), wraplength=820, foreground="#805800").grid(row=11, column=0, columnspan=3, sticky="w", pady=(12, 0))

        self.existing_page = ExistingPositionPage(self.notebook, self)
        self.notebook.add(self.existing_page, text=self.translator.render(message('existing_position')))
        self.notebook.bind('<<NotebookTabChanged>>', self.page_changed)

        language_controls = ttk.Frame(self)
        language_controls.grid(row=12, column=0, columnspan=3, sticky="e", pady=(10, 0))
        ttk.Label(language_controls, textvariable=self.translated(message("language"))).pack(side="left", padx=8)
        self.language = tk.StringVar(value=LANGUAGES[self.translator.language])
        self.language_box = ttk.Combobox(language_controls, textvariable=self.language,
                                       values=tuple(LANGUAGES.values()), state="readonly", width=14)
        self.language_box.pack(side="left")
        self.language_box.bind("<<ComboboxSelected>>", self.change_language)
        self.preference_status = self.translated("")
        ttk.Label(self, textvariable=self.preference_status).grid(row=13, column=0, columnspan=3, sticky="e")
        self.winfo_toplevel().title(self.translator.render(message("window_title")))

        self.underlying.trace_add("write", self.ticker_changed)
        self.database_path.trace_add("write", self.database_changed)
        self.spot.trace_add("write", self.spot_changed)
        for var in [self.expiry, self.premium, self.strike]:
            var.trace_add("write", self.invalidate)
        self.reload_symbols()
        self.winfo_toplevel().bind("<Return>", self.on_return)

    def page_changed(self, event=None):
        # A calendar belongs to its page; dismiss it when navigating away.
        for page in (self, self.existing_page):
            if page.calendar_window is not None and page.calendar_window.winfo_exists():
                page.calendar_window.destroy()

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
        self.annual_text.set("—")
        self.set_message(self.percentile_text, "—")
        self.set_message(self.iv_percentile_text, "—")
        self.set_message(self.iv_current_text, "")
        self.set_message(self.iv_status_text, "")
        self.set_details("")
        self.set_message(self.status, message('inputs_updated'))

    def ticker_changed(self, *args):
        self.expiry_box.configure(values=())
        self.spot.set("")
        self._historical_spot = False
        self.set_message(self.spot_source, message('underlying_changed'))
        self.invalidate()

    def database_changed(self, *args):
        self.ticker_changed()
        self.ticker_box.configure(values=())

    def spot_changed(self, *args):
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

    def __init__(self, master, owner):
        super().__init__(master, padding=8)
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
        ttk.Label(self, textvariable=self.translated(message('existing_heading')),
                  font=('Microsoft YaHei UI', 14, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 12))
        inputs = ttk.LabelFrame(self, padding=14)
        inputs.configure(labelwidget=ttk.Label(inputs, textvariable=self.translated(message('contract_inputs'))))
        inputs.grid(row=1, column=0, columnspan=3, sticky='ew')
        inputs.columnconfigure(1, weight=1)
        inputs.columnconfigure(3, weight=1)
        ttk.Label(inputs, textvariable=self.translated(message('underlying'))).grid(row=0, column=0, sticky='w', padx=(0, 12))
        self.ticker_box = ttk.Combobox(inputs, textvariable=self.underlying, width=20,
                                      values=('US.NVDA', 'US.GOOG', 'US.IREN', 'US.SPCX'))
        self.ticker_box.grid(row=0, column=1, sticky='ew')
        ttk.Label(inputs, textvariable=self.translated(message('expiry'))).grid(row=0, column=2, sticky='w', padx=(22, 12))
        self.expiry_controls(inputs).grid(row=0, column=3, sticky='ew')
        for row, col, key, variable in [
            (1, 0, 'strike_per_share', self.strike),
            (1, 2, 'buyback_premium', self.close_premium),
            (2, 0, 'contracts', self.contracts),
            (2, 2, 'current_spot', self.spot),
        ]:
            ttk.Label(inputs, textvariable=self.translated(message(key)), wraplength=200).grid(
                row=row, column=col, sticky='w', padx=(0 if col == 0 else 22, 12), pady=(12, 0))
            self.numeric_entry(inputs, key, variable).grid(row=row, column=col+1, sticky='ew', pady=(12, 0))
        ttk.Label(inputs, textvariable=self.translated(message('buyback_hint')), wraplength=780).grid(
            row=3, column=0, columnspan=4, sticky='w', pady=(12, 0))
        self.analyze_button = ttk.Button(self, textvariable=self.translated(message('calculate_remaining')), command=self.calculate)
        self.analyze_button.grid(row=2, column=0, columnspan=3, sticky='ew', ipady=6, pady=(14, 0))
        ttk.Label(self, textvariable=self.status, wraplength=820, foreground='#805800').grid(
            row=3, column=0, columnspan=3, sticky='w', pady=10)
        self.create_cards(self, [
            ('remaining_annual', self.annual_text, [], '#465767'),
            ('remaining_profit', self.profit_text, [], '#465767'),
            ('gross_collateral', self.collateral_text, [], '#465767'),
        ]).grid(row=4, column=0, columnspan=3, sticky='ew')
        ttk.Label(self, textvariable=self.translated(message('calculation_details')),
                  font=('Microsoft YaHei UI', 11, 'bold')).grid(row=5, column=0, columnspan=3, sticky='w', pady=(14, 5))
        self.create_details(self, 6)
        ttk.Label(self, textvariable=self.translated(canonical_message(RISK_NOTICE)),
                  wraplength=820, foreground='#805800').grid(row=7, column=0, columnspan=3, sticky='w', pady=(12, 0))
        ttk.Label(self, textvariable=self.translated(message('remaining_context_notice')),
                  wraplength=820).grid(row=8, column=0, columnspan=3, sticky='w', pady=(6, 0))
        for variable in (self.underlying, self.expiry, self.strike, self.close_premium, self.contracts, self.spot):
            variable.trace_add('write', self.invalidate)

    def invalidate(self, *args):
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
                message('contract_detail', underlying=underlying, expiry=expiry),
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
    width = min(int(960 * scale), root.winfo_screenwidth() - 80)
    height = min(int(1000 * scale), root.winfo_screenheight() - 100)
    root.geometry(f"{width}x{height}")
    root.minsize(min(int(880 * scale), width), min(int(920 * scale), height))
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", font=("Microsoft YaHei UI", 10))
    style.configure("TButton", padding=7)
    return root


def main(database_path=None):
    root = create_root()
    PutAnalysisWindow(root, Path(database_path) if database_path else Path("data/options.db"),
                      Path(__file__).resolve().parents[2] / "data" / "gui_preferences.json")
    root.mainloop()


if __name__ == "__main__":
    main()
