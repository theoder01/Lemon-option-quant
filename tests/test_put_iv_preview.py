# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 13, 2026

from datetime import date
import unittest
from unittest.mock import patch

import pandas as pd

from option_quant.analytics.iv_analysis import analyze_iv
from option_quant.analytics.put_preview import analyze_put_preview
from test_put_preview import NOW, sample_history


def iv_history():
    return sample_history().assign(iv=[30.0, 50.0, 50.0])


class PutIVPreviewTests(unittest.TestCase):
    def analyze(self, history=None, **changes):
        args = dict(underlying='US.IREN', expiry=date(2026, 10, 28), premium=2,
                    strike=90, spot=100, as_of=NOW,
                    history=iv_history() if history is None else history)
        return analyze_put_preview(**(args | changes))

    def test_reuses_existing_analyzer_strict_ties_units_and_source(self):
        with patch('option_quant.analytics.put_preview.analyze_iv', wraps=analyze_iv) as analyzer:
            result = self.analyze()
            analyzer.assert_called_once()
        self.assertEqual(result.iv.status, 'available')
        self.assertEqual(result.iv.current_iv, 50.0)
        self.assertEqual(result.iv.option_code, 'US.IREN261028P90000')
        self.assertEqual(result.iv.snapshot_time, '2026-09-23T15:00:00+00:00')
        self.assertEqual(result.iv.analysis.iv_percentile, 50.0)
        self.assertEqual(result.iv.sample_count, 2)
        self.assertEqual(result.iv.trading_days, 2)
        self.assertEqual(result.iv.analysis.median_iv, 40.0)
        self.assertEqual(result.iv.analysis.min_iv, 30.0)
        self.assertEqual(result.iv.analysis.max_iv, 50.0)
        self.assertTrue(result.iv.limited_history)

    def test_iv_does_not_change_premium_annual_fees_or_notes(self):
        original = self.analyze(sample_history())
        for values in [[30, 50, 50], [400, 500, 450], [None, 'invalid', 0]]:
            with self.subTest(values=values):
                result = self.analyze(sample_history().assign(iv=values))
                self.assertEqual(result.premium, original.premium)
                self.assertEqual(result.annual, original.annual)
                self.assertEqual(result.notes, original.notes)
                self.assertAlmostEqual(result.premium.premium_percentile, 100 / 3)
                self.assertAlmostEqual(result.annual.annualized_return, (200 - 2.5275) / 9000 * 365 / 30)

    def test_current_is_latest_exact_contract_not_latest_underlying_row(self):
        base = iv_history().iloc[-1].to_dict()
        other = [dict(base, snapshot_time='2026-09-27T15:00:00Z', **change) for change in [
            dict(underlying='US.NVDA'), dict(strike=91), dict(expiry='2026-11-28'),
            dict(option_code='US.IREN261028C90000'),
        ]]
        other += [dict(base, snapshot_time=NOW.isoformat(), iv=250),
                  dict(base, snapshot_time='2026-10-01T15:00:00Z', iv=300),
                  dict(base, snapshot_time='bad', iv=400)]
        result = self.analyze(pd.concat([iv_history(), pd.DataFrame(other)], ignore_index=True))
        self.assertEqual(result.iv.current_iv, 50)
        self.assertTrue(result.iv.snapshot_time.startswith('2026-09-23'))
        self.assertEqual(result.iv.sample_count, 2)

    def test_same_time_later_rows_and_current_snapshot_are_excluded(self):
        base = iv_history().iloc[-1].to_dict()
        more = [dict(base, expiry='2026-10-29', option_code='US.IREN261029P90000', iv=1,
                     snapshot_time=timestamp) for timestamp in [
                         '2026-09-23T15:00:00Z', '2026-09-24T15:00:00Z']]
        result = self.analyze(pd.concat([iv_history(), pd.DataFrame(more)], ignore_index=True))
        self.assertEqual(result.premium.sample_count, 5)
        self.assertEqual(result.iv.sample_count, 2)
        self.assertEqual(result.iv.analysis.iv_percentile, 50)

    def test_peers_share_premium_moneyness_dte_and_put_filters(self):
        base = iv_history().iloc[0].to_dict()
        valid = [dict(base, strike=88, dte=25, iv=20), dict(base, strike=92, dte=35, iv=60)]
        invalid = [dict(base, **change) for change in [
            dict(strike=87.9), dict(strike=92.1), dict(dte=24), dict(dte=36),
            dict(option_code='US.IREN261028C90000'), dict(underlying='US.NVDA'),
            dict(underlying_price=0), dict(last=-1), dict(dte=30.5),
        ]]
        history = pd.concat([iv_history(), pd.DataFrame(valid + invalid)], ignore_index=True)
        result = self.analyze(history)
        self.assertEqual(result.premium.sample_count, 5)
        self.assertEqual(result.iv.sample_count, 4)
        self.assertEqual(result.iv.analysis.iv_percentile, 50)
        # Targets follow GUI spot/DTE, not the older source snapshot's spot/DTE.
        self.assertEqual(self.analyze(history, spot=110).iv.status, 'history_insufficient')

    def test_invalid_historical_iv_values_are_excluded(self):
        base = iv_history().iloc[0].to_dict()
        more = [dict(base, iv=value) for value in [None, 'bad', float('nan'), float('inf'),
                                                 -float('inf'), 0, -1, 500.1]]
        more.append(dict(base, iv='500'))
        result = self.analyze(pd.concat([iv_history(), pd.DataFrame(more)], ignore_index=True))
        self.assertEqual(result.iv.sample_count, 3)
        self.assertAlmostEqual(result.iv.analysis.iv_percentile, 100 / 3)
        self.assertEqual(result.iv.analysis.max_iv, 500)

    def test_invalid_latest_iv_does_not_fall_back_to_an_older_value(self):
        for value in [None, 'bad', float('nan'), float('inf'), 0, -1, 501]:
            with self.subTest(value=value):
                history = iv_history().astype({'iv': object})
                history.loc[2, 'iv'] = value
                result = self.analyze(history)
                self.assertEqual(result.iv.status, 'invalid_current')
                self.assertIsNone(result.iv.current_iv)
                self.assertTrue(result.iv.snapshot_time.startswith('2026-09-23'))
                self.assertIsNotNone(result.premium)

    def test_zero_valid_samples_insufficient_and_one_sample_existing_policy(self):
        for history in [iv_history().iloc[-1:], iv_history().assign(iv=[None, 0, 50])]:
            result = self.analyze(history)
            self.assertEqual(result.iv.status, 'history_insufficient')
            self.assertEqual(result.iv.sample_count, 0)
            self.assertIsNone(result.iv.analysis)
            self.assertEqual(result.iv.current_iv, 50)
        result = self.analyze(iv_history().iloc[1:])
        self.assertEqual(result.iv.sample_count, 1)
        self.assertEqual(result.iv.analysis.iv_percentile, 0)
        self.assertTrue(result.iv.limited_history)

    def test_missing_contract_columns_history_spot_and_itm(self):
        for history in [pd.DataFrame(), iv_history().drop(columns='iv'),
                        iv_history().drop(columns='expiry'), iv_history().assign(expiry='2026-10-29')]:
            result = self.analyze(history)
            self.assertEqual(result.iv.status, 'current_unavailable')
            self.assertIsNotNone(result.annual)
        for spot in [None, 80]:
            result = self.analyze(spot=spot)
            self.assertEqual(result.iv.status, 'comparison_unavailable')
            self.assertEqual(result.iv.current_iv, 50)
            self.assertIsNone(result.premium)

    def test_ambiguous_latest_snapshot_is_not_arbitrarily_selected(self):
        history = pd.concat([iv_history(), iv_history().iloc[-1:]], ignore_index=True)
        self.assertEqual(self.analyze(history).iv.status, 'ambiguous_current')

    def test_existing_coverage_warning_boundary(self):
        base = iv_history().iloc[0].to_dict()
        peers = [dict(base, snapshot_time=f'2026-09-{day}T15:00:00Z', iv=40)
                 for day in range(14, 19) for _ in range(4)]
        history = pd.concat([pd.DataFrame(peers), iv_history().iloc[-1:]], ignore_index=True)
        result = self.analyze(history)
        self.assertEqual(result.iv.sample_count, 20)
        self.assertEqual(result.iv.trading_days, 5)
        self.assertFalse(result.iv.limited_history)


if __name__ == '__main__':
    unittest.main()
