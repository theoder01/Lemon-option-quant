# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scripts import show_stock_metrics_charts as entry
from option_quant.analytics.stock_metrics_charts import load_latest_chart_data
from option_quant.analytics.stock_metrics import StockMetrics
from option_quant.analytics.stock_metrics_database import StockMetricsDatabase


def test_empty_data_exits_cleanly_without_gui(tmp_path, monkeypatch, capsys):
    database = StockMetricsDatabase(tmp_path / "missing.db")
    monkeypatch.setattr(entry, "load_latest_chart_data", lambda: load_latest_chart_data(database))
    monkeypatch.setattr(entry, "create_stock_scanner_dashboard", lambda _: (_ for _ in ()).throw(AssertionError()))
    assert entry.main([]) == 0
    assert "No stored stock metrics" in capsys.readouterr().out
    assert not database.database_path.exists()


def test_script_exports_one_dashboard_without_gui_and_closes_figure(tmp_path, monkeypatch):
    database = StockMetricsDatabase(tmp_path / "metrics.db")
    database.save(StockMetrics("US.AAPL", datetime(2026, 10, 8, 15, tzinfo=timezone.utc), 100, 60, 10, 22.5, 3.5))
    monkeypatch.setattr(entry, "load_latest_chart_data", lambda: load_latest_chart_data(database))
    def forbidden():
        raise AssertionError("GUI must not open")
    monkeypatch.setattr(plt, "show", forbidden)
    before = plt.get_fignums()
    output = tmp_path / "charts"
    assert entry.main(["--no-show", "--save-dir", str(output)]) == 0
    assert {path.name for path in output.iterdir()} == {
        "20261008_stock_scanner_dashboard.jpg",
    }
    assert plt.get_fignums() == before


def test_script_reports_loading_error(monkeypatch, capsys):
    def fail():
        raise RuntimeError("schema unreadable")
    monkeypatch.setattr(entry, "load_latest_chart_data", fail)
    assert entry.main([]) == 1
    assert "schema unreadable" in capsys.readouterr().err
