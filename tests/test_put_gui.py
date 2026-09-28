# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 28, 2026

from pathlib import Path
import tkinter as tk
import unittest
from unittest.mock import patch

from option_quant.put_gui import PutAnalysisWindow
from test_put_preview import NOW, sample_history


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
        self.assertIn('无法计算', self.window.status.get())
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
        self.assertEqual(self.window.percentile_text.get(), '暂无可比数据')
        self.assertIn('历史库不可用', self.window.status.get())


if __name__ == '__main__':
    unittest.main()
