# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

from datetime import datetime, timezone
import builtins
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backend_bases import MouseEvent
from matplotlib.colors import to_rgb
import numpy as np
from PIL import Image
import pytest

from option_quant.analytics import stock_metrics_charts as charts
from option_quant.analytics.stock_metrics import StockMetrics
from option_quant.analytics.stock_metrics_database import COLUMNS, StockMetricsDatabase
from scripts import show_stock_metrics_charts as entry


def row(ticker, day):
    return StockMetrics(ticker, datetime.fromisoformat(day + "T15:00:00+00:00"), 100, 65, 8, 22.5, 3.5)


@pytest.fixture
def latest_data(tmp_path):
    database = StockMetricsDatabase(tmp_path / "stock_metrics.db")
    for ticker in ("US.AAPL", "US.AMD", "US.OLD"):
        database.save(row(ticker, "2001-01-02"))
    for ticker in ("US.AAPL", "US.AMD"):
        database.save(row(ticker, "2001-01-03"))
    return charts.load_latest_chart_data(database)


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


def test_latest_cross_section_does_not_mix_history_or_backfill_missing_ticker(latest_data):
    assert latest_data.ticker.tolist() == ["US.AAPL", "US.AMD"]
    assert latest_data.trading_date.tolist() == ["2001-01-03", "2001-01-03"]
    assert "US.OLD" not in latest_data.ticker.values
    assert len(latest_data) == 2


def test_dashboard_has_two_side_by_side_panels_and_one_overall_logo(latest_data):
    figure = charts.create_stock_scanner_dashboard(latest_data)
    left, right, logo = figure.axes
    assert left.get_position().x1 < right.get_position().x0
    assert left.get_position().y0 == right.get_position().y0
    assert left.get_title() == "Volatility Premium Map"
    assert right.get_title() == "Drawdown / Skew Sweet Zone Map"
    assert sum(axis.get_label() == "lemon_logo" for axis in figure.axes) == 1
    assert logo.get_position().x0 < left.get_position().x0
    assert logo.get_position().y0 > left.get_position().y1
    box = logo.get_position()
    ratio = box.width * figure.get_figwidth() / (box.height * figure.get_figheight())
    image = logo.images[0].get_array()
    assert ratio == pytest.approx(image.shape[1] / image.shape[0])


def test_shared_header_date_and_count_come_from_same_latest_slice(latest_data):
    figure = charts.create_stock_scanner_dashboard(latest_data)
    headers = [text.get_text() for text in figure.texts if "New York trading date" in text.get_text()]
    assert headers == ["New York trading date: 2001-01-03   •   2 tickers"]


def test_panels_preserve_coordinates_all_points_and_ticker_labels(latest_data):
    figure = charts.create_stock_scanner_dashboard(latest_data)
    for axes, columns in zip(figure.axes[:2], (charts.CHART_1_AXES, charts.CHART_2_AXES)):
        np.testing.assert_array_equal(axes.collections[0].get_offsets(), latest_data[list(columns)].values)
        assert {"AAPL", "AMD"}.issubset({text.get_text() for text in axes.texts})
    left = figure.axes[0]
    assert left.patches[0].get_xy() == (0, 50)
    assert list(left.lines[0].get_xdata()) == [0, 0]
    assert list(left.lines[1].get_ydata()) == [50, 50]
    assert left.get_ylim() == (0, 100)


def test_named_sweet_zone_config_and_derived_center_are_preserved():
    assert (charts.SKEW_SWEET_MIN, charts.SKEW_SWEET_MAX) == (2, 5)
    assert (charts.DRAWDOWN_SWEET_MIN, charts.DRAWDOWN_SWEET_MAX) == (15, 30)
    assert charts.SWEET_ZONE_CENTER == (3.5, 22.5)


def test_landscape_palette_supports_green_yellow_orange_red_without_metric_fields(latest_data):
    green, yellow, orange, red = map(to_rgb, charts.LANDSCAPE_COLORS)
    assert green[1] > green[0] and green[1] > green[2]
    assert yellow[0] > yellow[2] and yellow[1] > yellow[2]
    assert orange[0] > orange[1] > orange[2]
    assert red[0] > red[1] and red[0] > red[2]
    assert list(latest_data.columns) == [*COLUMNS, "label", "hover_text"]


def test_gradient_extends_beyond_exact_zone_and_is_pale(latest_data):
    figure = charts.create_stock_scanner_dashboard(latest_data)
    right = figure.axes[1]
    x0, x1, y0, y1 = right.images[0].get_extent()
    assert x0 < 2 < 5 < x1
    assert y0 < 15 < 30 < y1
    rgba = right.images[0].get_array()
    assert rgba[:, :, 3].min() >= 0.22
    assert rgba[:, :, 3].max() <= 0.38


def test_palette_moves_from_green_toward_red_on_both_sides():
    image = charts.sweet_zone_image((-26.5, 33.5), (-127.5, 172.5))
    # Symmetric around (3.5, 22.5), including far lower and upper extremes.
    np.testing.assert_allclose(image, image[::-1, :, :], atol=1e-12)
    np.testing.assert_allclose(image, image[:, ::-1, :], atol=1e-12)
    center = image[128, 128]
    low = image[128, 0]
    high = image[128, -1]
    assert center[1] > center[0]
    assert low[0] > low[1] and high[0] > high[1]


def test_auto_export_creates_directory_and_dated_quality_jpeg(latest_data, tmp_path):
    figure = charts.create_stock_scanner_dashboard(latest_data)
    directory = tmp_path / "outputs" / "stock_scanner"
    assert not directory.exists()
    path = charts.save_stock_scanner_dashboard(figure, latest_data, directory)
    assert path.name == "20010103_stock_scanner_dashboard.jpg"
    assert path.parent == directory
    with Image.open(path) as image:
        assert image.format == "JPEG"
        assert image.size == (24 * charts.EXPORT_DPI, 10 * charts.EXPORT_DPI)
        assert image.mode == "RGB"
        assert all(channel >= 250 for channel in image.getpixel((0, 0)))


def test_default_command_saves_automatically_before_gui_display(latest_data, tmp_path, monkeypatch):
    directory = tmp_path / "default" / "stock_scanner"
    monkeypatch.setattr(charts, "OUTPUT_DIRECTORY", directory)
    monkeypatch.setattr(entry, "load_latest_chart_data", lambda: latest_data)
    def show():
        assert (directory / "20010103_stock_scanner_dashboard.jpg").is_file()
    monkeypatch.setattr(plt, "show", show)
    assert entry.main([]) == 0
    assert len(list(directory.iterdir())) == 1


def test_filename_uses_database_date_even_when_exporting_today(latest_data, tmp_path):
    figure = charts.create_stock_scanner_dashboard(latest_data)
    path = charts.save_stock_scanner_dashboard(figure, latest_data, tmp_path)
    assert path.name.startswith("20010103_")
    assert "stock_scanner" in path.name
    assert path.suffix == ".jpg"


def test_empty_data_produces_no_dashboard(tmp_path):
    data = charts.load_latest_chart_data(StockMetricsDatabase(tmp_path / "missing.db"))
    assert charts.create_stock_scanner_dashboard(data) is None
    with pytest.raises(ValueError, match="empty"):
        charts.save_stock_scanner_dashboard(None, data, tmp_path / "exports")
    assert not (tmp_path / "exports").exists()


def test_mixed_dates_cannot_be_exported_or_rendered(latest_data, tmp_path):
    latest_data.loc[0, "trading_date"] = "2001-01-02"
    with pytest.raises(ValueError, match="one trading date"):
        charts.create_stock_scanner_dashboard(latest_data)
    with pytest.raises(ValueError, match="one trading date"):
        charts.save_stock_scanner_dashboard(None, latest_data, tmp_path)


def test_dashboard_keeps_hover_for_both_panels(latest_data):
    figure = charts.create_stock_scanner_dashboard(latest_data)
    figure.canvas.draw()
    for axes, xy in zip(figure.axes[:2], ((8, 65), (3.5, 22.5))):
        x, y = axes.transData.transform(xy)
        event = MouseEvent("motion_notify_event", figure.canvas, x, y)
        figure.canvas.callbacks.process("motion_notify_event", event)
        assert any(text.get_visible() and text.get_text() == latest_data.iloc[0].hover_text
                   for text in axes.texts)


def test_read_and_build_do_not_import_futu_or_open_options_database(tmp_path, monkeypatch):
    database = StockMetricsDatabase(tmp_path / "stock_metrics.db")
    database.save(row("US.AAPL", "2001-01-03"))
    original_import = builtins.__import__
    original_connect = sqlite3.connect
    def guarded_import(name, *args, **kwargs):
        if name == "futu" or name.startswith("futu."):
            raise AssertionError("Futu not permitted")
        return original_import(name, *args, **kwargs)
    def guarded_connect(path, *args, **kwargs):
        assert "options.db" not in str(path)
        return original_connect(path, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(sqlite3, "connect", guarded_connect)
    assert charts.create_stock_scanner_dashboard(charts.load_latest_chart_data(database)) is not None
