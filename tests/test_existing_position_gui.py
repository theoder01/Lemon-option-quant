# Copyright © 2026 Bo Hu. All rights reserved.
# Created: October 1, 2026

from datetime import date
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
import unittest
from unittest.mock import patch

from option_quant.analytics.put_annualized_return import calculate_remaining_annualized_return, RISK_NOTICE
from option_quant.date_picker import DatePicker
from option_quant.gui_i18n import canonical_message, Translator
from option_quant.gui_strings import LANGUAGES
from option_quant.put_gui import AnalysisPage, PutAnalysisWindow
from test_put_preview import NOW, sample_history


class ExistingPositionTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.window = PutAnalysisWindow(self.root, Path('missing-existing-test.db'))
        self.page = self.window.existing_page
        clock = patch('option_quant.put_gui.now_utc', return_value=NOW)
        clock.start()
        self.addCleanup(clock.stop)
        self.window.notebook.select(self.page)
        self.root.update()
        self.fill()

    def fill(self):
        for name, value in dict(underlying='nvda', expiry='2026-10-18', strike='100',
                                close_premium='0.30', contracts='1', spot='110').items():
            getattr(self.page, name).set(value)

    def language(self, code):
        self.window.language.set(LANGUAGES[code])
        self.window.change_language()

    def details(self):
        return self.page.details.get('1.0', 'end')

    def test_calls_remaining_analytics_with_buy_estimator_and_no_history(self):
        with patch('option_quant.put_gui.calculate_remaining_annualized_return',
                   wraps=calculate_remaining_annualized_return) as calculate, \
             patch('option_quant.put_gui.ReadOnlyOptionDatabase.load_underlying') as history:
            self.page.analyze_button.invoke()
            calculate.assert_called_once_with(strike=100, close_premium=0.30, contracts=1,
                as_of=date(2026, 9, 28), expiration=date(2026, 10, 18), closing_fee=None)
            history.assert_not_called()
        result = self.page.result
        self.assertEqual(result.gross_collateral, 10000)
        self.assertAlmostEqual(result.transaction_fee, 2.5075)
        self.assertAlmostEqual(result.potential_profit, 32.5075)
        self.assertAlmostEqual(result.annualized_return, 32.5075 / 10000 * 365 / 20)
        self.assertEqual(self.page.annual_text.get(), '5.93%')
        self.assertEqual(self.page.profit_text.get(), '$32.51')
        self.assertEqual(self.page.collateral_text.get(), '$10,000.00')
        for text in ['US.NVDA', '2026-10-18', '$110.0000', '$100.0000', '$0.3000',
                     'Contracts: 1', '20 calendar days', '$30.00', '$2.5075',
                     'Remaining period return:', 'Fee source:', '2026-09-28', 'avoided']:
            self.assertIn(text, self.details())
        self.assertNotIn('percentile', self.details().lower())
        self.assertEqual(len(self.page.result_cards), 3)

    def test_explicit_fee_financial_example(self):
        result = calculate_remaining_annualized_return(strike=100, close_premium=0.30,
            contracts=1, closing_fee=2.50, as_of=date(2026, 9, 28), expiration=date(2026, 10, 18))
        self.assertEqual(result.gross_collateral, 10000)
        self.assertEqual(result.potential_profit, 32.50)
        self.assertAlmostEqual(result.annualized_return, 0.0593125)

    def test_spot_only_changes_position_context(self):
        results = []
        for spot, state, ratio in [('110', 'OTM', '90.91%'), ('100', 'ATM', '100.00%'), ('90', 'ITM', '111.11%')]:
            with self.subTest(spot=spot):
                self.page.spot.set(spot)
                self.page.calculate()
                self.assertIn('Position status: ' + state, self.details())
                self.assertIn('Moneyness (strike / spot): ' + ratio, self.details())
                results.append(self.page.result)
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])

    def test_multiple_contracts_and_zero_buyback_quote(self):
        self.page.contracts.set('3')
        self.page.close_premium.set('0')
        self.page.calculate()
        self.assertEqual(self.page.result.gross_collateral, 30000)
        self.assertEqual(self.page.result.potential_profit, self.page.result.transaction_fee)
        self.assertIn('Current buyback cost: $0.00', self.details())

    def test_invalid_inputs_clear_stale_results_and_translate(self):
        cases = {
            'strike': ['', '0', '-1', 'nan', 'inf', 'abc'],
            'close_premium': ['', '-1', 'nan', 'inf', 'abc'],
            'contracts': ['', '0', '-1', '1.5', '1.0', 'nan', 'abc'],
            'spot': ['', '0', '-1', 'nan', 'inf', 'abc'],
            'expiry': ['2026-09-28', '2026-09-27', 'invalid'],
            'underlying': [''],
        }
        for code in LANGUAGES:
            self.language(code)
            for field, values in cases.items():
                for value in values:
                    with self.subTest(language=code, field=field, value=value):
                        self.fill()
                        self.page.calculate()
                        self.assertIsNotNone(self.page.result)
                        getattr(self.page, field).set(value)
                        self.assertIsNone(self.page.result)
                        self.page.analyze_button.invoke()
                        self.assertIsNone(self.page.result)
                        self.assertEqual(self.page.annual_text.get(), '—')
                        self.assertEqual(self.page.profit_text.get(), '—')
                        self.assertEqual(self.page.collateral_text.get(), '—')
                        self.assertEqual(self.details().strip(), '')
                        self.assertIn('Unable to calculate' if code == 'en' else '无法计算', self.page.status.get())
                        self.assertNotIn('Unexpected error', self.page.status.get())
                        self.assertNotIn('未知', self.page.status.get())

    def test_language_switch_updates_both_pages_without_recalculation(self):
        self.page.calculate()
        english = self.details()
        inputs = [self.page.strike.get(), self.page.spot.get(), self.page.close_premium.get()]
        result = self.page.result
        with patch.object(self.page, 'calculate') as calculate:
            self.language('zh_CN')
            self.assertEqual(self.window.notebook.tab(self.page, 'text'), '已有仓位')
            self.assertEqual(self.window.notebook.tab(self.window.new_page, 'text'), '新建仓位')
            self.assertIn('剩余潜在收益', self.details())
            self.assertIn('富途香港', self.details())
            self.assertIn('计算剩余收益', self.page.analyze_button['text'])
            self.assertIn('计算百分位', self.window.analyze_button['text'])
            self.language('en')
            calculate.assert_not_called()
        self.assertEqual(self.details(), english)
        self.assertIs(self.page.result, result)
        self.assertEqual(inputs, [self.page.strike.get(), self.page.spot.get(), self.page.close_premium.get()])
        self.page.contracts.set('0')
        self.page.calculate()
        self.language('zh_CN')
        self.assertIn('合约张数必须是正整数', self.page.status.get())

    def test_navigation_preserves_both_pages_and_one_root(self):
        self.page.calculate()
        previous = self.page.result
        children = self.root.winfo_children()
        with patch('option_quant.put_gui.tk.Tk') as new_root, \
             patch('option_quant.put_gui.ReadOnlyOptionDatabase.load_underlying', return_value=sample_history()):
            self.window.notebook.select(self.window.new_page)
            self.root.update()
            self.window.premium.set('2')
            self.window.strike.set('90')
            self.window.spot.set('100')
            self.window.expiry.set('2026-10-28')
            self.window.analyze_button.invoke()
            initial = self.window.annual_text.get()
            self.assertIn('%', initial)
            self.window.notebook.select(self.page)
            self.root.update()
            self.assertIs(self.page.result, previous)
            self.assertEqual(self.page.close_premium.get(), '0.30')
            self.assertEqual(self.root.winfo_children(), children)
            self.window.notebook.select(self.window.new_page)
            self.assertEqual(self.window.premium.get(), '2')
            self.assertEqual(self.window.annual_text.get(), initial)
            new_root.assert_not_called()
        self.assertIs(self.page.tk, self.window.tk)

    def test_enter_routes_only_to_active_page(self):
        with patch.object(self.page, 'calculate') as existing, patch.object(self.window, 'calculate') as initial:
            self.window.on_return(SimpleNamespace(widget=self.page.numeric_entries['contracts']))
            existing.assert_called_once()
            initial.assert_not_called()
            self.window.on_return(SimpleNamespace(widget=self.window.language_box))
            self.assertEqual(existing.call_count, 1)

    def test_reuses_calendar_and_numeric_implementation(self):
        self.assertIs(type(self.page).numeric_entry, AnalysisPage.numeric_entry)
        self.assertIs(type(self.page).edit_numeric, type(self.window).edit_numeric)
        self.assertIs(type(self.page).open_calendar, type(self.window).open_calendar)
        self.page.calendar_button.invoke()
        picker = self.page.calendar_window
        self.assertIsInstance(picker, DatePicker)
        self.language('zh_CN')
        self.assertEqual(picker.title(), '选择到期日')
        picker.day_buttons[19].invoke()
        self.assertEqual(self.page.expiry.get(), '2026-10-19')
        self.assertEqual(self.window.expiry.get(), '')
        self.page.open_calendar()
        self.window.notebook.select(self.window.new_page)
        self.root.update()
        self.assertFalse(self.page.calendar_window.winfo_exists())

    def test_analytics_risk_notice_is_reused_and_translated(self):
        self.assertEqual(Translator().render(canonical_message(RISK_NOTICE)), RISK_NOTICE)
        self.assertIn('每张买入 100 股', Translator('zh_CN').render(canonical_message(RISK_NOTICE)))
        self.assertIn(RISK_NOTICE, [variable.get() for variable, _ in self.window._translated_variables.values()])


if __name__ == '__main__':
    unittest.main()
