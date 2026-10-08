# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

from datetime import datetime, timezone
import hashlib
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backend_bases import MouseEvent
import numpy as np
import pandas as pd
import pytest

from option_quant.analytics import stock_metrics_charts as charts
from option_quant.analytics.stock_metrics import StockMetrics
from option_quant.analytics.stock_metrics_database import COLUMNS, StockMetricsDatabase


def metric(ticker="US.AAPL", stamp="2026-10-08T15:00:00+00:00"):
    return StockMetrics(ticker, datetime.fromisoformat(stamp), 100, 65, 8, 22.5, 3.5)


@pytest.fixture
def database(tmp_path):
    return StockMetricsDatabase(tmp_path / "stock_metrics.db")


@pytest.fixture
def data(database):
    database.save(metric())
    database.save(metric("US.AMD"))
    return charts.load_latest_chart_data(database)


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


def test_latest_ny_trading_date_slice_includes_all_tickers(database):
    database.save(metric("US.OLD", "2026-10-07T15:00:00+00:00"))
    database.save(metric("US.AMD"))
    database.save(metric("US.AAPL", "2026-10-09T01:00:00+00:00"))
    result = charts.load_latest_chart_data(database)
    assert result.trading_date.tolist() == ["2026-10-08", "2026-10-08"]
    assert result.ticker.tolist() == ["US.AAPL", "US.AMD"]


def test_read_latest_does_not_modify_database_file(database):
    database.save(metric())
    before = hashlib.sha256(database.database_path.read_bytes()).digest()
    database.load_latest_metrics()
    assert hashlib.sha256(database.database_path.read_bytes()).digest() == before


def test_missing_database_is_not_created(tmp_path):
    path = tmp_path / "missing" / "stock_metrics.db"
    result = charts.load_latest_chart_data(StockMetricsDatabase(path))
    assert result.empty
    assert not path.parent.exists()
    assert set(COLUMNS).issubset(result.columns)


def test_database_with_no_table_is_handled_without_creating_table(tmp_path):
    path = tmp_path / "empty.db"
    connection = sqlite3.connect(path)
    connection.close()
    result = charts.load_latest_chart_data(StockMetricsDatabase(path))
    assert result.empty
    connection = sqlite3.connect(path)
    try:
        assert not connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    finally:
        connection.close()


def test_empty_stock_metrics_table_returns_empty_schema(database):
    assert database.load_all().empty
    result = database.load_latest_metrics()
    assert result.empty
    assert list(result.columns) == list(COLUMNS)
    assert charts.create_stock_metrics_charts(result) == (None, None)


def test_prepared_data_has_required_fields_labels_and_hover(data):
    assert list(data.columns) == [*COLUMNS, "label", "hover_text"]
    assert data.label.tolist() == ["AAPL", "AMD"]
    assert charts.HOVER_FIELDS == ("ticker", "spot", "iv_rank", "iv_hv", "drawdown_52w", "put_call_skew")
    text = data.iloc[0].hover_text
    for value in ("US.AAPL", "Spot: 100.00", "IV Rank: 65.00", "IV - HV: +8.00 pp",
                  "52W Drawdown: 22.50%", "Put-Call Skew: +3.50 vol points"):
        assert value in text


def test_preparation_does_not_change_metric_values_or_source(data):
    original = data.copy(deep=True)
    prepared = charts.prepare_chart_data(data)
    pd.testing.assert_frame_equal(data, original)
    pd.testing.assert_frame_equal(prepared.loc[:, list(COLUMNS)], data.loc[:, list(COLUMNS)])


def test_missing_required_column_is_reported(data):
    with pytest.raises(ValueError, match="put_call_skew"):
        charts.prepare_chart_data(data.drop(columns="put_call_skew"))


def test_mixed_dates_are_rejected(data):
    data.loc[0, "trading_date"] = "2026-10-07"
    with pytest.raises(ValueError, match="one trading date"):
        charts.prepare_chart_data(data)


def test_invalid_values_are_not_plotted_as_zero(data):
    data.loc[0, "iv_hv"] = float("nan")
    with pytest.raises(ValueError, match="iv_hv"):
        charts.prepare_chart_data(data)


def test_chart_one_uses_raw_iv_hv_and_iv_rank_with_reference_guides(data):
    figure = charts.create_volatility_premium_map(data)
    axes = figure.axes[0]
    assert charts.CHART_1_AXES == ("iv_hv", "iv_rank")
    np.testing.assert_array_equal(axes.collections[0].get_offsets(), data[["iv_hv", "iv_rank"]].values)
    assert axes.get_xlabel() == "IV - HV (percentage points)"
    assert axes.get_ylabel() == "IV Rank"
    assert list(axes.lines[0].get_xdata()) == [0, 0]
    assert list(axes.lines[1].get_ydata()) == [50, 50]
    region = axes.patches[0]
    assert region.get_xy() == (0, 50)
    assert region.get_width() == axes.get_xlim()[1]
    assert region.get_height() == 50
    assert region.get_zorder() < axes.collections[0].get_zorder()


def test_chart_two_uses_skew_and_drawdown_and_fixed_middle_zone(data):
    figure = charts.create_drawdown_skew_map(data)
    axes = figure.axes[0]
    assert charts.CHART_2_AXES == ("put_call_skew", "drawdown_52w")
    np.testing.assert_array_equal(axes.collections[0].get_offsets(), data[["put_call_skew", "drawdown_52w"]].values)
    assert axes.get_xlabel() == "30D 25Δ Put-Call Skew (vol points)"
    assert axes.get_ylabel() == "52W Drawdown (%)"
    assert charts.SKEW_RANGE == (2, 5)
    assert charts.DRAWDOWN_RANGE == (15, 30)
    assert charts.SWEET_ZONE_CENTER == (3.5, 22.5)
    assert tuple(axes.images[0].get_extent()) == (*axes.get_xlim(), *axes.get_ylim())
    assert axes.get_xlim()[0] < 2 and axes.get_xlim()[1] > 5
    assert axes.get_ylim()[0] < 15 and axes.get_ylim()[1] > 30
    assert not axes.patches  # Smooth landscape replaces the hard-edged rectangle.
    assert any("Higher is not always better" in text.get_text() for text in figure.texts)


def test_green_display_gradient_is_centered_and_softens_towards_extremes():
    rgba = charts.sweet_zone_image((-1, 8), (0, 45))
    alpha = rgba[:, :, 3]
    assert alpha[128, 128] == pytest.approx(0.38)
    assert alpha[128, 128] > alpha[128, 64] > alpha[128, 0]
    assert np.all(alpha <= 0.38)
    np.testing.assert_allclose(alpha, alpha[::-1, :])
    np.testing.assert_allclose(alpha, alpha[:, ::-1])
    assert rgba[128, 128, 1] > rgba[128, 128, 0]  # Green center, not pink.


@pytest.mark.parametrize("builder", [charts.create_volatility_premium_map, charts.create_drawdown_skew_map])
def test_both_charts_have_direct_ticker_labels_and_original_logo(data, builder):
    figure = builder(data)
    axes, logo_axes = figure.axes
    texts = [text.get_text() for text in axes.texts]
    assert "AAPL" in texts and "AMD" in texts
    assert logo_axes.get_label() == "lemon_logo"
    assert charts.LOGO_PATH.name == "logo-128.png"
    assert charts.LOGO_PATH.parent.name == "branding"
    assert logo_axes.get_position().y0 > axes.get_position().y1
    image = logo_axes.images[0].get_array()
    box = logo_axes.get_position()
    physical_ratio = box.width * figure.get_figwidth() / (box.height * figure.get_figheight())
    assert physical_ratio == pytest.approx(image.shape[1] / image.shape[0])
    assert any(text.get_text() == "Lemon Option Quant" for text in figure.texts)


def test_hover_shows_all_details_and_hides_when_pointer_leaves(data):
    figure = charts.create_volatility_premium_map(data)
    axes = figure.axes[0]
    figure.canvas.draw()
    x, y = axes.transData.transform((8, 65))
    event = MouseEvent("motion_notify_event", figure.canvas, x, y)
    figure.canvas.callbacks.process("motion_notify_event", event)
    tooltip = axes.texts[-1]
    assert tooltip.get_visible()
    assert tooltip.get_text() == data.iloc[0].hover_text
    event = MouseEvent("motion_notify_event", figure.canvas, 0, 0)
    figure.canvas.callbacks.process("motion_notify_event", event)
    assert not tooltip.get_visible()


def test_loading_stored_data_needs_no_futu_or_network(database, monkeypatch):
    import socket
    from live_short_put_scanner.futu_client import FutuClient
    def forbidden(*args, **kwargs):
        raise AssertionError("No live retrieval permitted")
    database.save(metric())
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(FutuClient, "__enter__", forbidden)
    assert len(charts.load_latest_chart_data(database)) == 1
