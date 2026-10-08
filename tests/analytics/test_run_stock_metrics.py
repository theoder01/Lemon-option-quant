# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

from datetime import datetime, timezone

import pytest

from scripts import run_stock_metrics as entry
from option_quant.analytics.daily_stock_metrics import DailyRunResult, TickerResult


STAMP = datetime(2026, 10, 8, 15, tzinfo=timezone.utc)


def install_stubs(monkeypatch, *, fail_options=False, fail_run=False, fail_close=False):
    events = []
    class Scanner:
        def __init__(self, host, port):
            events.append(("scanner_config", host, port))
        def __enter__(self):
            events.append("scanner_enter")
            return self
        def __exit__(self, *args):
            events.append("scanner_close")
    class Options:
        def close(self):
            events.append("options_close")
            if fail_close:
                raise RuntimeError("option cleanup failed")
    def create_options():
        if fail_options:
            raise RuntimeError("cannot initialize options")
        events.append("options_create")
        return Options()
    class Runner:
        def __init__(self, source, database):
            pass
        def run(self, timestamp):
            assert timestamp == STAMP
            events.append("run")
            if fail_run:
                raise RuntimeError("unexpected run failure")
            return DailyRunResult(timestamp, [TickerResult("US.TEST", saved_rows=1)])
    monkeypatch.setattr(entry, "ScannerClient", Scanner)
    monkeypatch.setattr(entry, "create_option_client", create_options)
    monkeypatch.setattr(entry, "DailyStockMetricsRunner", Runner)
    monkeypatch.setattr(entry, "StockMetricsDatabase", lambda: object())
    monkeypatch.setattr(entry, "runner_time", lambda: STAMP)
    return events


def test_script_closes_both_clients_after_success(monkeypatch, capsys):
    events = install_stubs(monkeypatch)
    assert entry.main() == 0
    assert events[-3:] == ["run", "options_close", "scanner_close"]
    output = capsys.readouterr().out
    assert "Daily Stock Metrics" in output and "OK saved" in output


def test_script_closes_scanner_if_second_client_initialization_fails(monkeypatch, capsys):
    events = install_stubs(monkeypatch, fail_options=True)
    assert entry.main() == 1
    assert events[-1] == "scanner_close"
    output = capsys.readouterr().out
    assert "cannot initialize options" in output
    assert output.count("SKIP") == len(entry.config.UNDERLYINGS)


def test_script_closes_both_clients_on_unexpected_runner_error(monkeypatch):
    events = install_stubs(monkeypatch, fail_run=True)
    assert entry.main() == 1
    assert events[-2:] == ["options_close", "scanner_close"]


def test_script_closes_both_clients_on_interrupt(monkeypatch):
    events = install_stubs(monkeypatch)
    class Runner:
        def __init__(self, *args):
            pass
        def run(self, timestamp):
            raise KeyboardInterrupt()
    monkeypatch.setattr(entry, "DailyStockMetricsRunner", Runner)
    with pytest.raises(KeyboardInterrupt):
        entry.main()
    assert events[-2:] == ["options_close", "scanner_close"]


def test_script_returns_failure_status_when_some_tickers_are_skipped(monkeypatch):
    events = install_stubs(monkeypatch)
    class Runner:
        def __init__(self, *args):
            pass
        def run(self, timestamp):
            return DailyRunResult(timestamp, [TickerResult("US.TEST", reason="no valid 30D skew")])
    monkeypatch.setattr(entry, "DailyStockMetricsRunner", Runner)
    assert entry.main() == 1
    assert events[-2:] == ["options_close", "scanner_close"]


def test_cleanup_failure_preserves_saved_summary_and_still_closes_scanner(monkeypatch, capsys):
    events = install_stubs(monkeypatch, fail_close=True)
    assert entry.main() == 1
    assert events[-2:] == ["options_close", "scanner_close"]
    captured = capsys.readouterr()
    assert "option cleanup failed" in captured.err
    assert "OK saved" in captured.out
    assert "Saved:       1" in captured.out
    assert "Skipped:     0" in captured.out
