# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

from contextlib import closing
from dataclasses import replace
from datetime import datetime, timezone
import sqlite3
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from option_quant.analytics.stock_metrics import StockMetrics
from option_quant.analytics.stock_metrics_database import COLUMNS, StockMetricsDatabase
from option_quant.runtime_paths import resource_root


def metrics(time="2026-10-08T15:00:00+00:00", ticker="US.NVDA", **changes):
    row = StockMetrics(ticker, datetime.fromisoformat(time), 100, 55.5, -5, 50, 8)
    return replace(row, **changes)


@pytest.fixture
def database(tmp_path):
    return StockMetricsDatabase(tmp_path / "history" / "stock_metrics.db")


def test_first_save_creates_explicit_schema_and_stores_one_row(database):
    assert not database.database_path.exists()
    assert database.save(metrics()) == (1, 0)
    with closing(sqlite3.connect(database.database_path)) as connection:
        schema = connection.execute('PRAGMA table_info(stock_metrics)').fetchall()
    assert [row[1] for row in schema] == list(COLUMNS)
    assert [row[2] for row in schema] == ['TEXT', 'TEXT', 'TEXT', 'REAL', 'REAL', 'REAL', 'REAL', 'REAL']
    assert all(row[3] == 1 for row in schema)
    row = database.load_all().iloc[0]
    assert row.ticker == 'US.NVDA'
    assert (row.spot, row.iv_rank, row.iv_hv, row.drawdown_52w, row.put_call_skew) == (100, 55.5, -5, 50, 8)


def test_constructor_is_lazy_and_default_path_is_separate(tmp_path):
    assert StockMetricsDatabase().database_path == resource_root() / 'data' / 'stock_metrics.db'
    path = tmp_path / 'uncreated' / 'stock_metrics.db'
    StockMetricsDatabase(path)
    assert not path.parent.exists()


def test_same_ticker_same_ny_date_is_duplicate_and_never_overwrites(database):
    assert database.save(metrics()) == (1, 0)
    before = database.load_all()
    assert database.save(metrics('2026-10-09T01:00:00+00:00', spot=200, iv_hv=20)) == (0, 1)
    pd.testing.assert_frame_equal(database.load_all(), before)


@pytest.mark.parametrize('before,after,expected_dates', [
    ('2026-10-09T03:59:59+00:00', '2026-10-09T04:00:00+00:00', ['2026-10-08', '2026-10-09']),
    ('2026-01-09T04:59:59+00:00', '2026-01-09T05:00:00+00:00', ['2026-01-08', '2026-01-09']),
])
def test_ny_date_boundary_accepts_next_day_in_summer_and_winter(database, before, after, expected_dates):
    assert database.save(metrics(before)) == (1, 0)
    assert database.save(metrics(after)) == (1, 0)
    assert database.load_all().trading_date.tolist() == expected_dates


def test_different_tickers_same_date_and_filtered_load(database):
    assert database.save(metrics(ticker='US.NVDA')) == (1, 0)
    assert database.save(metrics(ticker='US.AAPL')) == (1, 0)
    assert len(database.load_all()) == 2
    assert database.load_ticker('US.AAPL').ticker.tolist() == ['US.AAPL']
    assert database.load_ticker("US.AAPL' OR 1=1 --").empty


def test_history_sorted_by_utc_timestamp_and_reopening_preserves_rows(database):
    assert database.save(metrics('2026-10-10T15:00:00+00:00')) == (1, 0)
    assert database.save(metrics('2026-10-08T15:00:00+00:00')) == (1, 0)
    assert database.save(metrics('2026-10-09T15:00:00+00:00')) == (1, 0)
    expected = ['2026-10-08T15:00:00.000000Z', '2026-10-09T15:00:00.000000Z', '2026-10-10T15:00:00.000000Z']
    assert database.load_all().snapshot_time.tolist() == expected
    assert database.load_ticker('US.NVDA').snapshot_time.tolist() == expected
    reopened = StockMetricsDatabase(database.database_path)
    pd.testing.assert_frame_equal(reopened.load_all(), database.load_all())
    assert reopened.save(metrics()) == (0, 1)


def test_timezone_normalization_and_microseconds(database):
    row = metrics(snapshot_time=datetime(2026, 10, 8, 11, 12, 13, 456789, tzinfo=ZoneInfo('America/New_York')))
    assert database.save(row) == (1, 0)
    stored = database.load_all().iloc[0]
    assert stored.snapshot_time == '2026-10-08T15:12:13.456789Z'
    assert stored.trading_date == '2026-10-08'
    assert database.save(replace(row, snapshot_time=row.snapshot_time.astimezone(timezone.utc))) == (0, 1)


def test_load_on_unused_database_returns_empty_schema(database):
    assert database.load_all().empty
    assert database.load_all().columns.tolist() == list(COLUMNS)
    assert database.load_ticker('US.UNKNOWN').empty
    assert database.load_ticker('US.UNKNOWN').columns.tolist() == list(COLUMNS)


@pytest.mark.parametrize('ticker', ['', '   ', None, 123])
def test_invalid_ticker_rejected_before_creating_file(database, ticker):
    with pytest.raises(ValueError, match='ticker'):
        database.save(metrics(ticker=ticker))
    assert not database.database_path.exists()


@pytest.mark.parametrize('spot', [0, -1, None, float('nan'), float('inf'), True])
def test_invalid_or_nonpositive_spot_rejected(database, spot):
    with pytest.raises(ValueError, match='spot'):
        database.save(metrics(spot=spot))
    assert not database.database_path.exists()


@pytest.mark.parametrize('timestamp', [None, datetime(2026, 10, 8), '2026-10-08'])
def test_missing_naive_or_wrong_type_timestamp_rejected(database, timestamp):
    with pytest.raises(ValueError, match='snapshot_time'):
        database.save(metrics(snapshot_time=timestamp))
    assert not database.database_path.exists()


def test_negative_and_extreme_metrics_preserved_without_thresholds(database):
    row = metrics(iv_rank=-123, iv_hv=-250, drawdown_52w=-20, put_call_skew=1000)
    assert database.save(row) == (1, 0)
    stored = database.load_all().iloc[0]
    assert (stored.iv_rank, stored.iv_hv, stored.drawdown_52w, stored.put_call_skew) == (-123, -250, -20, 1000)


@pytest.mark.parametrize('field', ['iv_rank', 'iv_hv', 'drawdown_52w', 'put_call_skew'])
def test_nonfinite_metrics_rejected_instead_of_persisting_invalid_values(database, field):
    with pytest.raises(ValueError, match=field):
        database.save(metrics(**{field: float('nan')}))


def test_unique_constraint_protects_against_direct_duplicate_insert(database):
    database.save(metrics())
    with closing(sqlite3.connect(database.database_path)) as connection, connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute('INSERT INTO stock_metrics SELECT * FROM stock_metrics')
    assert len(database.load_all()) == 1
