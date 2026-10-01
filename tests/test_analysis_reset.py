# Copyright © 2026 Bo Hu. All rights reserved.
"""A ticker change or page entry begins a fresh analysis session."""
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from option_quant.gui_i18n import message, load_language
from option_quant.gui_strings import LANGUAGES
from option_quant.put_gui import PutAnalysisWindow
from test_put_preview import NOW
from test_put_iv_preview import iv_history


class AnalysisResetTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.preferences = Path(temporary.name) / 'preferences.json'
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        for target, value in (
            ('now_utc', NOW),
            ('ReadOnlyOptionDatabase.load_underlying', iv_history()),
            ('ReadOnlyOptionDatabase.underlyings', ['US.IREN', 'US.GOOG']),
        ):
            mock = patch('option_quant.put_gui.' + target, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)
        self.window = PutAnalysisWindow(self.root, Path('reset-fixture.db'), self.preferences)
        self.root.update()

    def select(self, page):
        self.window.notebook.select(self.window.new_page if page is self.window else page)
        self.root.update()

    def fill_and_calculate(self, page):
        page.underlying.set('US.IREN')
        page.expiry.set('2026-10-28')
        page.strike.set('90')
        page.spot.set('100')
        if page is self.window:
            page.premium.set('2')
            page.load_reference()
        else:
            page.close_premium.set('0.30')
            page.contracts.set('3')
        page.calculate()
        self.assertIn('%', page.annual_text.get())
        self.assertTrue(page.details.get('1.0', 'end').strip())

    def assert_clean(self, page, underlying):
        self.assertEqual(page.underlying.get(), underlying)
        fields = ['expiry', 'strike', 'spot']
        fields += ['premium'] if page is self.window else ['close_premium']
        for field in fields:
            self.assertEqual(getattr(page, field).get(), '', field)
        self.assertFalse(page.expiry_box['values'])
        self.assertEqual(page.annual_text.get(), '—')
        self.assertEqual(page.details.get('1.0', 'end').strip(), '')
        self.assertEqual(page._detail_messages, '')
        self.assertEqual(page.empty_label.winfo_manager(), 'grid')
        self.assertEqual(page.details.winfo_manager(), '')
        key = 'initial_status' if page is self.window else 'existing_initial_status'
        self.assertEqual(page.status.get(), page.translator.render(message(key)))
        if page is self.window:
            self.assertEqual(page.percentile_text.get(), '—')
            self.assertEqual(page.iv_percentile_text.get(), '—')
            self.assertEqual(page.iv_current_text.get(), '')
            self.assertEqual(page.iv_status_text.get(), '')
            self.assertFalse(page._historical_spot)
            self.assertEqual(page.spot_source.get(), page.translator.render(message('manual_spot_hint')))
        else:
            self.assertEqual(page.contracts.get(), '1')
            self.assertEqual(page.profit_text.get(), '—')
            self.assertEqual(page.collateral_text.get(), '—')
            self.assertIsNone(page.result)

    def check_underlying_change(self, page):
        self.select(page)
        self.fill_and_calculate(page)
        if page is self.window:
            self.assertEqual(page.percentile_text.get(), '33.3%')
            self.assertEqual(page.iv_percentile_text.get(), '50.0%')
            self.assertTrue(page.expiry_box['values'])
        page.open_calendar()
        calendar = page.calendar_window
        widgets = dict(page.numeric_entries)
        page.underlying.set('US.GOOG')
        self.assert_clean(page, 'US.GOOG')
        self.assertFalse(calendar.winfo_exists())
        self.assertEqual(page.numeric_entries, widgets)
        # Reopening uses clean state, not the previous selected contract.
        page.open_calendar()
        self.assertNotEqual(page.calendar_window, calendar)
        page.calendar_window.destroy()

    def test_new_position_underlying_clears_contract_and_history(self):
        self.check_underlying_change(self.window)

    def test_existing_position_underlying_clears_contract_and_results(self):
        self.check_underlying_change(self.window.existing_page)

    def test_both_navigation_round_trips_reset_and_keep_global_settings(self):
        for language in LANGUAGES:
            self.window.language.set(LANGUAGES[language])
            self.window.change_language()
            saved = self.preferences.read_bytes()
            for page, other in ((self.window, self.window.existing_page),
                                (self.window.existing_page, self.window)):
                with self.subTest(language=language, page=type(page).__name__):
                    self.select(page)
                    self.fill_and_calculate(page)
                    self.select(other)
                    self.fill_and_calculate(other)
                    self.select(page)
                    self.assert_clean(page, 'US.IREN')
                    page.underlying.set('US.GOOG')
                    self.assert_clean(page, 'US.GOOG')
                    self.assertEqual(self.window.language.get(), LANGUAGES[language])
                    self.assertEqual(self.window.translator.language, language)
                    self.assertEqual(self.preferences.read_bytes(), saved)
                    self.assertEqual(load_language(self.preferences), language)
                    self.assertEqual(self.window.database_path.get(), 'reset-fixture.db')
                    self.assertEqual(self.window.database_name.get(), 'reset-fixture.db')

    def test_same_tab_same_ticker_and_language_changes_do_not_reset(self):
        self.fill_and_calculate(self.window)
        before = self.window.annual_text.get()
        self.window.underlying.set(self.window.underlying.get())
        self.select(self.window)
        self.window.page_changed()
        self.window.language.set(LANGUAGES['zh_CN'])
        with patch.object(self.window, 'calculate') as calculate:
            self.window.change_language()
            self.root.update()
            calculate.assert_not_called()
        self.assertEqual(self.window.premium.get(), '2')
        self.assertEqual(self.window.annual_text.get(), before)
        self.assertIn('资金', self.window.details.get('1.0', 'end'))
