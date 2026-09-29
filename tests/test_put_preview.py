# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 28, 2026

from datetime import date, datetime, timezone
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

import pandas as pd

from option_quant.analytics.put_preview import (
    ReadOnlyOptionDatabase,
    analyze_put_preview,
    latest_reference,
    normalize_underlying,
)


NOW = datetime(2026, 9, 28, 15, tzinfo=timezone.utc)


def sample_history():
    base = dict(underlying="US.IREN", underlying_price=100, strike=90,
                dte=30, expiry="2026-10-28", option_code="US.IREN261028P90000")
    return pd.DataFrame([dict(base, snapshot_time=f"2026-09-{day}T15:00:00Z", last=price)
                         for day, price in [(21, 1), (22, 2), (23, 3)]])


class PutPreviewTests(unittest.TestCase):
    def analyze(self, **changes):
        args = dict(underlying="iren", expiry=date(2026, 10, 28), premium=2,
                    strike=90, spot=100, as_of=NOW, history=sample_history())
        return analyze_put_preview(**(args | changes))

    def test_existing_percentile_strict_ties_and_calendar_dte(self):
        result = self.analyze()
        self.assertEqual(result.underlying, "US.IREN")
        self.assertAlmostEqual(result.premium.premium_percentile, 100 / 3)
        self.assertEqual(result.premium.sample_count, 3)
        self.assertEqual(result.trading_days, 3)
        self.assertEqual(result.annual.remaining_days, 30)
        self.assertAlmostEqual(result.annual.annualized_return, (200 - 2.5275) / 9000 * 365 / 30)
        self.assertTrue(any("Historical samples or date coverage are limited" in note for note in result.notes))

    def test_excludes_future_same_time_calls_other_tickers_and_noncomparables(self):
        history = sample_history()
        base = history.iloc[0].to_dict()
        bad = [dict(base, snapshot_time=NOW.isoformat()), dict(base, snapshot_time="2026-09-29"),
               dict(base, option_code="US.IREN261028C90000"), dict(base, underlying="US.NVDA"),
               dict(base, strike=50), dict(base, dte=50), dict(base, snapshot_time="bad")]
        result = self.analyze(history=pd.concat([history, pd.DataFrame(bad)]))
        self.assertEqual(result.premium.sample_count, 3)

    def test_invalid_rows_are_excluded_without_losing_valid_rows(self):
        history = sample_history()
        base = history.iloc[0].to_dict()
        bad = [dict(base, **{column: value}) for column in ['strike', 'underlying_price', 'last', 'dte']
               for value in [None, 'bad', float('inf'), -1]]
        result = self.analyze(history=pd.concat([history, pd.DataFrame(bad)]))
        self.assertEqual(result.premium.sample_count, 3)

    def test_no_history_no_spot_and_itm_still_return_annual(self):
        for changes in [dict(history=pd.DataFrame()), dict(spot=None), dict(strike=110), dict(strike=60)]:
            with self.subTest(changes=list(changes)):
                result = self.analyze(**changes)
                self.assertIsNone(result.premium)
                self.assertGreater(result.annual.annualized_return, 0)
                self.assertTrue(result.notes)

    def test_new_york_date_not_utc_date(self):
        result = self.analyze(as_of=datetime(2026, 9, 29, 1, tzinfo=timezone.utc))
        self.assertEqual(result.annual.remaining_days, 30)

    def test_invalid_user_inputs(self):
        for changes in [dict(expiry=date(2026, 9, 28)), dict(expiry=date(2026, 9, 27)),
                        dict(premium='nan'), dict(premium=-1), dict(strike=0), dict(spot=0),
                        dict(spot=float('inf')), dict(underlying=''), dict(as_of=NOW.replace(tzinfo=None))]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.analyze(**changes)

    def test_latest_reference_ignores_future_and_invalid_price(self):
        history = sample_history()
        base = history.iloc[0].to_dict()
        more = [dict(base, underlying_price=999, snapshot_time="2026-10-01"),
                dict(base, underlying_price=float('nan'), snapshot_time="2026-09-27")]
        price, timestamp, dates = latest_reference(pd.concat([history, pd.DataFrame(more)]), "US.IREN", NOW)
        self.assertEqual(price, 100)
        self.assertTrue(timestamp.startswith('2026-09-23'))
        self.assertEqual(dates, ['2026-10-28'])

    def test_read_only_database_does_not_create_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'missing.db'
            with self.assertRaises(sqlite3.OperationalError):
                ReadOnlyOptionDatabase(path).load_underlying('US.IREN')
            self.assertFalse(path.exists())

    def test_read_only_database_reuses_queries_and_rejects_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'options.db'
            with closing(sqlite3.connect(path)) as connection:
                sample_history().to_sql('option_snapshots', connection, index=False)
            database = ReadOnlyOptionDatabase(path)
            self.assertEqual(database.underlyings(), ['US.IREN'])
            self.assertEqual(len(database.load_underlying('US.IREN')), 3)
            with database._connect() as connection, self.assertRaises(sqlite3.OperationalError):
                connection.execute('DELETE FROM option_snapshots')

    def test_underlying_normalization(self):
        self.assertEqual(normalize_underlying(' nvda '), 'US.NVDA')
        self.assertEqual(normalize_underlying('us.iren'), 'US.IREN')


if __name__ == '__main__':
    unittest.main()
