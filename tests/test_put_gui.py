# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 28, 2026

from pathlib import Path
from contextlib import closing
import sqlite3
import tempfile
from types import SimpleNamespace
import tkinter as tk
import unittest
from unittest.mock import patch

from option_quant.put_gui import PutAnalysisWindow
from option_quant.gui_strings import LANGUAGES
from test_put_preview import NOW, sample_history
from test_put_iv_preview import iv_history


class PutGuiTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.window = PutAnalysisWindow(self.root, Path('missing-for-gui-test.db'))

    def fill(self):
        self.window.premium.set('2')
        self.window.strike.set('90')
        self.window.spot.set('100')
        self.window.expiry.set('2026-10-28')

    @patch('option_quant.put_gui.now_utc', return_value=NOW)
    @patch('option_quant.put_gui.ReadOnlyOptionDatabase.load_underlying', return_value=sample_history())
    def test_button_results_and_invalid_input_clear_stale_output(self, *mocks):
        self.fill()
        self.window.analyze_button.invoke()
        self.assertEqual(self.window.percentile_text.get(), '33.3%')
        self.assertIn('%', self.window.annual_text.get())
        self.window.premium.set('not a price')
        self.assertEqual(self.window.annual_text.get(), '—')
        self.window.analyze_button.invoke()
        self.assertIn('Unable to calculate', self.window.status.get())
        self.assertEqual(self.window.percentile_text.get(), '—')

    @patch('option_quant.put_gui.now_utc', return_value=NOW)
    @patch('option_quant.put_gui.ReadOnlyOptionDatabase.load_underlying', return_value=sample_history())
    def test_reference_price_timestamp_expiries_and_ticker_change(self, *mocks):
        self.window.reference_button.invoke()
        self.assertEqual(self.window.spot.get(), '100')
        self.assertIn('2026-09-23', self.window.spot_source.get())
        self.assertIn('2026-10-28', self.window.expiry_box['values'])
        self.assertTrue(self.window._historical_spot)
        self.window.spot.set('101')
        self.assertFalse(self.window._historical_spot)
        self.window.underlying.set('US.NVDA')
        self.assertEqual(self.window.spot.get(), '')

    @patch('option_quant.put_gui.now_utc', return_value=NOW)
    def test_missing_database_keeps_annual_available(self, *mocks):
        self.fill()
        self.window.analyze_button.invoke()
        self.assertIn('%', self.window.annual_text.get())
        self.assertEqual(self.window.percentile_text.get(), 'No Comparable Data')
        self.assertIn('History database unavailable', self.window.status.get())

    def switch_language(self, language):
        self.window.language.set(LANGUAGES[language])
        self.window.language_box.event_generate('<<ComboboxSelected>>')
        self.root.update_idletasks()

    @patch('option_quant.put_gui.now_utc', return_value=NOW)
    def test_switch_preserves_inputs_results_database_and_widget_identity(self, *mocks):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / 'history.db'
            with closing(sqlite3.connect(database)) as connection:
                iv_history().to_sql('option_snapshots', connection, index=False)
            self.window.database_path.set(str(database))
            self.window.load_reference()
            self.fill()
            self.window.calculate()
            inputs = [self.window.underlying, self.window.expiry, self.window.premium,
                      self.window.strike, self.window.spot, self.window.database_path]
            before_inputs = [variable.get() for variable in inputs]
            before_results = (self.window.annual_text.get(), self.window.percentile_text.get(),
                              self.window.iv_percentile_text.get())
            self.assertEqual(self.window.iv_percentile_text.get(), '50.0%')
            before_details = self.window.details.get('1.0', 'end').replace('\t', '')
            before_widgets = self.window.winfo_children()
            before_database = database.read_bytes()
            with patch('option_quant.put_gui.analyze_put_preview') as calculate, \
                    patch('option_quant.put_gui.ReadOnlyOptionDatabase') as read_database:
                self.switch_language('zh_CN')
                self.assertIn('计算', self.window.analyze_button['text'])
                self.assertIn('Put 分析', self.root.title())
                self.assertIn('估值时间', self.window.details.get('1.0', 'end').replace('\t', ''))
                self.assertIn('样本较少', self.window.status.get())
                self.assertEqual([variable.get() for variable in inputs], before_inputs)
                self.assertEqual((self.window.annual_text.get(), self.window.percentile_text.get(),
                                  self.window.iv_percentile_text.get()), before_results)
                self.assertIn('当前隐含波动率', self.window.iv_current_text.get())
                self.switch_language('en')
                self.assertEqual(self.window.details.get('1.0', 'end').replace('\t', ''), before_details)
                self.assertEqual(self.window.winfo_children(), before_widgets)
                calculate.assert_not_called()
                read_database.assert_not_called()
            self.assertEqual(database.read_bytes(), before_database)

    def test_error_and_unavailable_result_retranslate_without_recalculation(self):
        self.fill()
        with patch('option_quant.put_gui.now_utc', return_value=NOW):
            self.window.calculate()
        self.switch_language('zh_CN')
        self.assertEqual(self.window.percentile_text.get(), '暂无可比数据')
        self.assertIn('历史库不可用', self.window.status.get())
        self.window.premium.set('invalid')
        self.window.calculate()
        self.assertIn('每股权利金必须是有效数字', self.window.status.get())
        self.switch_language('en')
        self.assertIn('Premium per share must be a valid number', self.window.status.get())

    @patch('option_quant.put_gui.now_utc', return_value=NOW)
    @patch('option_quant.put_gui.ReadOnlyOptionDatabase.load_underlying', return_value=sample_history())
    def test_reference_and_file_dialog_translate(self, *mocks):
        self.window.load_reference()
        before = self.window.spot.get()
        self.switch_language('zh_CN')
        self.assertIn('历史参考价', self.window.spot_source.get())
        self.assertEqual(self.window.spot.get(), before)
        self.assertTrue(self.window._historical_spot)
        with patch('option_quant.put_gui.filedialog.askopenfilename', return_value='') as dialog:
            self.window.choose_database()
            self.assertEqual(dialog.call_args.kwargs['title'], '选择期权历史库')

    def test_language_preference_restored_on_next_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'preferences.json'
            self.window.preference_path = path
            self.switch_language('zh_CN')
            self.window.destroy()
            self.window = PutAnalysisWindow(self.root, Path('missing.db'), path)
            self.assertEqual(self.window.translator.language, 'zh_CN')
            self.assertIn('计算', self.window.analyze_button['text'])
            with patch('option_quant.put_gui.save_language', return_value=False):
                self.switch_language('en')
                self.assertIn('could not be saved', self.window.preference_status.get())

    def test_enter_on_language_selector_does_not_calculate(self):
        with patch.object(self.window, 'calculate') as calculate:
            self.assertEqual(self.window.on_return(SimpleNamespace(widget=self.window.language_box)), 'break')
            calculate.assert_not_called()
            self.window.on_return(SimpleNamespace(widget=self.window.expiry_box))
            calculate.assert_called_once()

    @patch('option_quant.put_gui.now_utc', return_value=NOW)
    @patch('option_quant.put_gui.ReadOnlyOptionDatabase.load_underlying', return_value=iv_history())
    def test_iv_card_details_translation_and_invalidation(self, *mocks):
        self.fill()
        self.window.analyze_button.invoke()
        self.assertEqual(len(self.window.result_cards), 3)
        self.assertEqual(self.window.iv_percentile_text.get(), '50.0%')
        self.assertEqual(self.window.iv_current_text.get(), 'Current IV: 50.0%')
        details = self.window.details.get('1.0', 'end').replace('\t', '')
        self.assertIn('median 40.0%', details)
        self.assertIn('US.IREN261028P90000', details)
        self.assertIn('2026-09-23T15:00:00+00:00', details)
        self.assertIn('2 snapshots', details)
        self.switch_language('zh_CN')
        self.assertIn('隐含波动率历史百分位：50.0%', self.window.details.get('1.0', 'end').replace('\t', ''))
        self.assertIn('仅供参考', self.window.details.get('1.0', 'end').replace('\t', ''))
        self.window.strike.set('91')
        self.assertEqual(self.window.iv_percentile_text.get(), '—')
        self.assertEqual(self.window.iv_current_text.get(), '')
        self.window.analyze_button.invoke()
        self.assertIn('无已存储', self.window.iv_status_text.get())
        self.assertIn('%', self.window.annual_text.get())

    @patch('option_quant.put_gui.now_utc', return_value=NOW)
    @patch('option_quant.put_gui.ReadOnlyOptionDatabase.load_underlying', return_value=iv_history().iloc[-1:])
    def test_iv_insufficient_history_in_both_languages(self, *mocks):
        self.fill()
        self.window.calculate()
        self.assertEqual(self.window.iv_percentile_text.get(), '—')
        self.assertEqual(self.window.iv_status_text.get(), 'Insufficient historical IV data')
        self.assertIn('0 snapshots', self.window.details.get('1.0', 'end').replace('\t', ''))
        self.switch_language('zh_CN')
        self.assertEqual(self.window.iv_status_text.get(), '历史隐含波动率数据不足')
        self.assertIn('0 条快照', self.window.details.get('1.0', 'end').replace('\t', ''))


if __name__ == '__main__':
    unittest.main()
