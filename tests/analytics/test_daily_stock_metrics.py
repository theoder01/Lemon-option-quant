# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from live_short_put_scanner import config
from option_quant.analytics.daily_stock_metrics import (
    DailyStockMetricsRunner, StockInputs, print_results,
)
from option_quant.analytics.skew import REQUIRED_COLUMNS
from option_quant.analytics.stock_metrics import StockMetrics
from option_quant.analytics.stock_metrics_database import StockMetricsDatabase


STAMP = datetime(2026, 10, 8, 15, tzinfo=timezone.utc)
INPUTS = StockInputs(38.0, 55.5, -5.0, 50.0)


def options(ticker, timestamp):
    rows = []
    for dte, skew in ((20, 6.0), (40, 10.0)):
        expiry = (timestamp.date() + timedelta(days=dte)).isoformat()
        for kind, delta, iv in (("PUT", -0.25, 52.0 + skew), ("CALL", 0.25, 52.0)):
            rows.append({
                "snapshot_time": timestamp, "underlying": ticker,
                "expiry": expiry, "dte": dte,
                "option_code": f"{ticker}-{expiry}-{kind}",
                "option_type": kind, "delta": delta, "iv": iv,
            })
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


class FakeSource:
    def __init__(self):
        self.inputs = {}
        self.option_frames = {}
        self.calls = []

    def get_stock_inputs(self, ticker, snapshot_time):
        self.calls.append(("stock", ticker, snapshot_time))
        value = self.inputs.get(ticker, INPUTS)
        if isinstance(value, Exception):
            raise value
        return value

    def get_option_snapshot(self, ticker, snapshot_time):
        self.calls.append(("options", ticker, snapshot_time))
        value = self.option_frames.get(ticker)
        if isinstance(value, Exception):
            raise value
        return value if value is not None else options(ticker, snapshot_time)


@pytest.fixture
def setup_runner(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "UNDERLYINGS", ["US.NVDA"])
    source = FakeSource()
    database = StockMetricsDatabase(tmp_path / "stock_metrics.db")
    return DailyStockMetricsRunner(source, database), source, database


def test_calculation_maps_all_fields_and_preserves_spot_and_metrics(setup_runner):
    runner, _, database = setup_runner
    result = runner.calculate("US.NVDA", STAMP)
    assert result == StockMetrics("US.NVDA", STAMP, 38.0, 55.5, -5.0, 50.0, 8.0)
    assert not database.database_path.exists()


def test_success_saves_to_temporary_database_and_reports_counts(setup_runner):
    runner, _, database = setup_runner
    result = runner.run(STAMP)
    assert (result.total_tickers, result.successful_tickers,
            result.saved_rows, result.duplicate_rows) == (1, 1, 1, 0)
    assert not result.skipped_tickers
    row = result.ticker_results[0]
    assert row.metrics == StockMetrics("US.NVDA", STAMP, 38.0, 55.5, -5.0, 50.0, 8.0)
    stored = database.load_all().iloc[0]
    assert (stored.spot, stored.iv_rank, stored.iv_hv,
            stored.drawdown_52w, stored.put_call_skew) == (38, 55.5, -5, 50, 8)


def test_same_ny_day_is_duplicate_and_first_write_wins(setup_runner):
    runner, source, database = setup_runner
    assert runner.run(STAMP).saved_rows == 1
    original = database.load_all()
    source.inputs["US.NVDA"] = replace(INPUTS, spot=40)
    # A different UTC date, still the same New York date.
    second = runner.run(datetime(2026, 10, 9, 1, tzinfo=timezone.utc))
    assert (second.successful_tickers, second.saved_rows, second.duplicate_rows) == (1, 0, 1)
    pd.testing.assert_frame_equal(database.load_all(), original)


def test_next_ny_date_adds_a_row(setup_runner):
    runner, _, database = setup_runner
    assert runner.run(STAMP).saved_rows == 1
    assert runner.run(datetime(2026, 10, 9, 4, tzinfo=timezone.utc)).saved_rows == 1
    assert database.load_all().trading_date.tolist() == ["2026-10-08", "2026-10-09"]


def test_current_watchlist_is_processed_in_configured_order(tmp_path):
    source = FakeSource()
    result = DailyStockMetricsRunner(source, StockMetricsDatabase(tmp_path / "daily.db")).run(STAMP)
    assert [row.ticker for row in result.ticker_results] == list(config.UNDERLYINGS)
    assert [ticker for kind, ticker, _ in source.calls if kind == "stock"] == list(config.UNDERLYINGS)
    assert result.total_tickers == result.successful_tickers == result.saved_rows == len(config.UNDERLYINGS)


def test_config_is_read_at_run_time_and_common_timestamp_is_used(setup_runner, monkeypatch):
    runner, source, _ = setup_runner
    monkeypatch.setattr(config, "UNDERLYINGS", ["US.ZZZ", "US.AAA"])
    result = runner.run(STAMP)
    assert [row.ticker for row in result.ticker_results] == ["US.ZZZ", "US.AAA"]
    assert all(time == STAMP for _, _, time in source.calls)
    assert all(row.metrics.snapshot_time == STAMP for row in result.ticker_results)


@pytest.mark.parametrize("field,value", [
    ("iv_rank", None), ("iv_rank", float("nan")), ("iv_rank", 101),
    ("iv_hv", None), ("iv_hv", float("inf")),
    ("drawdown_52w", None), ("drawdown_52w", float("nan")),
    ("spot", None), ("spot", 0), ("spot", -1),
    ("spot", float("nan")), ("spot", float("inf")), ("spot", True),
])
def test_missing_or_invalid_stock_value_skips_without_placeholder(setup_runner, field, value):
    runner, source, database = setup_runner
    source.inputs["US.NVDA"] = replace(INPUTS, **{field: value})
    result = runner.run(STAMP)
    assert (result.successful_tickers, result.saved_rows, result.duplicate_rows) == (0, 0, 0)
    assert len(result.skipped_tickers) == 1
    assert field in result.skipped_tickers[0].reason
    assert result.skipped_tickers[0].metrics is None
    assert not database.database_path.exists()


@pytest.mark.parametrize("mode", ["empty", "one_sided", "missing_call", "invalid_delta", "nan_iv"])
def test_missing_30d_skew_is_skipped_without_storage(setup_runner, mode):
    runner, source, database = setup_runner
    frame = options("US.NVDA", STAMP)
    if mode == "empty":
        frame = frame.iloc[:0]
    elif mode == "one_sided":
        frame = frame[frame.dte == 20]
    elif mode == "missing_call":
        frame = frame[frame.option_type == "PUT"]
    elif mode == "invalid_delta":
        frame.loc[frame.option_type == "PUT", "delta"] = -0.1
    else:
        frame.loc[frame.option_type == "PUT", "iv"] = float("nan")
    source.option_frames["US.NVDA"] = frame
    result = runner.run(STAMP)
    assert "no valid 30D skew" in result.skipped_tickers[0].reason
    assert not database.database_path.exists()


@pytest.mark.parametrize("field,value", [
    ("underlying", "US.AAPL"),
    ("snapshot_time", STAMP - timedelta(days=1)),
])
def test_foreign_or_stale_option_rows_are_rejected(setup_runner, field, value):
    runner, source, database = setup_runner
    frame = options("US.NVDA", STAMP)
    frame.loc[0, field] = value
    source.option_frames["US.NVDA"] = frame
    result = runner.run(STAMP)
    assert "current ticker/snapshot" in result.skipped_tickers[0].reason
    assert not database.database_path.exists()


def test_one_failed_ticker_does_not_stop_remaining_and_summary_is_correct(setup_runner, monkeypatch):
    runner, source, database = setup_runner
    monkeypatch.setattr(config, "UNDERLYINGS", ["US.A", "US.B", "US.C", "US.D"])
    database.save(StockMetrics("US.B", STAMP, 100, 50, 5, 10, 8))
    source.inputs["US.A"] = RuntimeError("overview unavailable\ntry later")
    source.option_frames["US.C"] = RuntimeError("snapshot unavailable")
    result = runner.run(STAMP)
    assert (result.total_tickers, result.successful_tickers,
            result.saved_rows, result.duplicate_rows) == (4, 2, 1, 1)
    assert [row.ticker for row in result.skipped_tickers] == ["US.A", "US.C"]
    assert result.skipped_tickers[0].reason == "overview unavailable try later"
    assert database.load_all().ticker.tolist() == ["US.B", "US.D"]


def test_database_failure_is_isolated_to_one_ticker(setup_runner, monkeypatch):
    runner, _, database = setup_runner
    monkeypatch.setattr(config, "UNDERLYINGS", ["US.A", "US.B"])
    original_save = database.save
    def save(metrics):
        if metrics.ticker == "US.A":
            raise RuntimeError("disk unavailable")
        return original_save(metrics)
    monkeypatch.setattr(database, "save", save)
    result = runner.run(STAMP)
    assert result.saved_rows == 1
    assert result.skipped_tickers[0].reason == "disk unavailable"
    assert database.load_all().ticker.tolist() == ["US.B"]


def test_zero_metrics_are_valid_and_not_treated_as_missing(setup_runner):
    runner, source, _ = setup_runner
    source.inputs["US.NVDA"] = StockInputs(100, 0, 0, 0)
    frame = options("US.NVDA", STAMP)
    frame["iv"] = 52.0
    source.option_frames["US.NVDA"] = frame
    result = runner.run(STAMP)
    assert result.saved_rows == 1
    row = result.ticker_results[0].metrics
    assert (row.iv_rank, row.iv_hv, row.drawdown_52w, row.put_call_skew) == (0, 0, 0, 0)


def test_timestamp_is_normalized_to_utc(setup_runner):
    runner, source, _ = setup_runner
    local = STAMP.astimezone(timezone(timedelta(hours=8)))
    result = runner.run(local)
    assert result.snapshot_time.utcoffset() == timedelta(0)
    assert all(time.utcoffset() == timedelta(0) for _, _, time in source.calls)


def test_naive_timestamp_is_rejected_before_data_access(setup_runner):
    runner, source, database = setup_runner
    with pytest.raises(ValueError, match="timezone-aware"):
        runner.run(STAMP.replace(tzinfo=None))
    assert not source.calls
    assert not database.database_path.exists()


def test_default_time_is_captured_once_for_whole_run(setup_runner, monkeypatch):
    from option_quant.analytics import daily_stock_metrics
    runner, source, _ = setup_runner
    calls = []
    def clock():
        calls.append(True)
        return STAMP
    monkeypatch.setattr(daily_stock_metrics, "now_utc", clock)
    runner.run()
    assert len(calls) == 1
    assert all(time == STAMP for _, _, time in source.calls)


def test_terminal_reports_saved_duplicates_skips_and_counts(setup_runner, monkeypatch, capsys):
    runner, source, database = setup_runner
    monkeypatch.setattr(config, "UNDERLYINGS", ["US.A", "US.B", "US.C"])
    database.save(StockMetrics("US.B", STAMP, 100, 50, 5, 10, 8))
    source.inputs["US.C"] = replace(INPUTS, iv_rank=None)
    print_results(runner.run(STAMP))
    output = capsys.readouterr().out
    assert "US.A       OK saved" in output
    assert "US.B       OK duplicate" in output
    assert "US.C       SKIP missing or invalid iv_rank" in output
    for line in ("Total:       3", "Successful:  2", "Saved:       1", "Duplicate:   1", "Skipped:     1"):
        assert line in output
