# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

"""Two analytical views of stored metrics; no live retrieval or metric logic."""

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from live_short_put_scanner.calculations import finite_number
from live_short_put_scanner.chart import _label_projection, padded_zero_range
from option_quant.runtime_paths import resource_root

from .stock_metrics_database import COLUMNS, StockMetricsDatabase

if TYPE_CHECKING:
    from matplotlib.figure import Figure

CHART_1_AXES = ("iv_hv", "iv_rank")
CHART_2_AXES = ("put_call_skew", "drawdown_52w")
PREMIUM_BOUNDARY = 0.0
IV_RANK_BOUNDARY = 50.0
SKEW_SWEET_MIN = 2.0
SKEW_SWEET_MAX = 5.0
DRAWDOWN_SWEET_MIN = 15.0
DRAWDOWN_SWEET_MAX = 30.0
SKEW_RANGE = (SKEW_SWEET_MIN, SKEW_SWEET_MAX)
DRAWDOWN_RANGE = (DRAWDOWN_SWEET_MIN, DRAWDOWN_SWEET_MAX)
SWEET_ZONE_CENTER = (sum(SKEW_RANGE) / 2, sum(DRAWDOWN_RANGE) / 2)
LANDSCAPE_COLORS = ("#95cba0", "#f6e8a2", "#efbf94", "#e3a7a2")
OUTPUT_DIRECTORY = resource_root() / "outputs" / "stock_scanner"
FILENAME_SUFFIX = "_stock_scanner_dashboard.jpg"
EXPORT_DPI = 200
JPEG_QUALITY = 95
HOVER_FIELDS = ("ticker", "spot", "iv_rank", "iv_hv", "drawdown_52w", "put_call_skew")
POINT_COLOR = "#356b99"
LOGO_PATH = resource_root() / "assets" / "branding" / "logo-128.png"


def prepare_chart_data(metrics: pd.DataFrame) -> pd.DataFrame:
    """Retain all supplied daily rows, with direct labels and hover details."""
    missing = [column for column in COLUMNS if column not in metrics.columns]
    if missing:
        raise ValueError("Missing chart columns: " + ", ".join(missing))
    data = metrics.loc[:, list(COLUMNS)].copy()
    if not data.empty and data["trading_date"].nunique(dropna=False) != 1:
        raise ValueError("Chart data must contain one trading date")
    for column in HOVER_FIELDS[1:]:
        data[column] = data[column].map(finite_number)
        if data[column].isna().any():
            raise ValueError(f"Invalid chart value: {column}")
    if data["ticker"].isna().any():
        raise ValueError("Missing chart ticker")
    data["label"] = data["ticker"].map(lambda value: str(value).removeprefix("US."))
    data["hover_text"] = data.apply(tooltip_text, axis=1) if not data.empty else pd.Series(dtype=str)
    return data.reset_index(drop=True)


def load_latest_chart_data(database: StockMetricsDatabase | None = None) -> pd.DataFrame:
    source = database if database is not None else StockMetricsDatabase()
    return prepare_chart_data(source.load_latest_metrics())


def tooltip_text(row) -> str:
    return (f"Ticker: {row['ticker']}\n"
            f"Spot: {row['spot']:.2f}\n"
            f"IV Rank: {row['iv_rank']:.2f}\n"
            f"IV - HV: {row['iv_hv']:+.2f} pp\n"
            f"52W Drawdown: {row['drawdown_52w']:.2f}%\n"
            f"30D 25Δ Put-Call Skew: {row['put_call_skew']:+.2f} vol points")


def sweet_zone_image(x_limits=None, y_limits=None):
    """Render a pale middle-to-extremes landscape; never a stock metric.

    Distance is used only to interpolate background pixels. Palette stops
    describe display colors, not financial caution/fear thresholds.
    """
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap

    x_limits = x_limits if x_limits is not None else SKEW_RANGE
    y_limits = y_limits if y_limits is not None else DRAWDOWN_RANGE
    xs, ys = np.meshgrid(np.linspace(*x_limits, 257), np.linspace(*y_limits, 257))
    dx = (xs - SWEET_ZONE_CENTER[0]) / ((SKEW_SWEET_MAX - SKEW_SWEET_MIN) / 2)
    dy = (ys - SWEET_ZONE_CENTER[1]) / ((DRAWDOWN_SWEET_MAX - DRAWDOWN_SWEET_MIN) / 2)
    radius = np.sqrt((dx ** 2 + dy ** 2) / 2)
    palette = LinearSegmentedColormap.from_list(
        "middle_landscape", list(zip((0.0, 0.4, 0.65, 1.0), LANDSCAPE_COLORS)), N=1024
    )
    image = palette(radius / (radius + 2))
    image[:, :, 3] = 0.22 + 0.16 * np.exp(-radius ** 2 / 2)
    return image


def _attach_hover(figure, axes, points, data):
    annotation = axes.annotate(
        "", xy=(0, 0), xytext=(12, 12), textcoords="offset points", fontsize=10,
        bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#728394", alpha=0.98),
        zorder=20, annotation_clip=False,
    )
    annotation.set_visible(False)

    def on_motion(event):
        was_visible = annotation.get_visible()
        hit = None
        if (event.inaxes is axes and event.button is None
                and event.x is not None and event.y is not None):
            pixels = axes.transData.transform(points)
            distances = [(x - event.x) ** 2 + (y - event.y) ** 2 for x, y in pixels]
            nearest = min(range(len(distances)), key=distances.__getitem__)
            if distances[nearest] <= 12 ** 2:
                hit = nearest
        if hit is not None:
            annotation.xy = points[hit]
            right = event.x > (axes.bbox.x0 + axes.bbox.x1) / 2
            top = event.y > (axes.bbox.y0 + axes.bbox.y1) / 2
            annotation.set_position((-12 if right else 12, -12 if top else 12))
            annotation.set_ha("right" if right else "left")
            annotation.set_va("top" if top else "bottom")
            annotation.set_text(data.iloc[hit]["hover_text"])
        annotation.set_visible(hit is not None)
        if was_visible or hit is not None:
            figure.canvas.draw_idle()

    figure.canvas.mpl_connect("motion_notify_event", on_motion)


def _add_branding(figure, *, dashboard=False):
    import matplotlib.image as mpimg

    image = mpimg.imread(LOGO_PATH)
    # Size in physical inches, accounting for both image and figure aspect ratio.
    height = 0.075 if dashboard else 0.10
    width = height * figure.get_figheight() / figure.get_figwidth() * image.shape[1] / image.shape[0]
    position = (0.04, 0.895, width, height) if dashboard else (0.97 - width, 0.88, width, height)
    logo_axes = figure.add_axes(position, label="lemon_logo")
    logo_axes.imshow(image, aspect="equal")
    logo_axes.set_axis_off()
    if not dashboard:
        figure.text(0.97, 0.86, "Lemon Option Quant", ha="right", fontsize=8, color="#526171")


def _draw_panel(figure, axes, data, *, premium: bool):
    from matplotlib.patches import Rectangle
    from matplotlib.ticker import FuncFormatter

    x_column, y_column = CHART_1_AXES if premium else CHART_2_AXES
    axes.set_facecolor("#fcfdfe")
    axes.set_xlim(padded_zero_range([*data[x_column], *(SKEW_RANGE if not premium else (0,))]))
    axes.set_ylim((0, 100) if premium else padded_zero_range([*data[y_column], *DRAWDOWN_RANGE], 2))
    if premium:
        title = "Volatility Premium Map"
        xlabel, ylabel = "IV - HV (percentage points)", "IV Rank"
        x_upper = axes.get_xlim()[1]
        axes.add_patch(Rectangle(
            (PREMIUM_BOUNDARY, IV_RANK_BOUNDARY), x_upper - PREMIUM_BOUNDARY,
            100 - IV_RANK_BOUNDARY, facecolor="#cce6d1", alpha=0.65, edgecolor="none", zorder=0,
        ))
        axes.axvline(PREMIUM_BOUNDARY, color="#728394", linestyle="--", linewidth=1, zorder=1)
        axes.axhline(IV_RANK_BOUNDARY, color="#728394", linestyle="--", linewidth=1, zorder=1)
        note = "Green region: IV - HV > 0 and IV Rank > 50. Visual reference only."
    else:
        title = "Drawdown / Skew Sweet Zone Map"
        xlabel, ylabel = "30D 25Δ Put-Call Skew (vol points)", "52W Drawdown (%)"
        axes.imshow(
            sweet_zone_image(axes.get_xlim(), axes.get_ylim()),
            extent=(*axes.get_xlim(), *axes.get_ylim()),
            origin="lower", aspect="auto", interpolation="bilinear", zorder=0,
        )
        note = (f"Sweet zone: skew {SKEW_SWEET_MIN:g}–{SKEW_SWEET_MAX:g}; "
                f"drawdown {DRAWDOWN_SWEET_MIN:g}–{DRAWDOWN_SWEET_MAX:g}%. "
                f"Center ({SWEET_ZONE_CENTER[0]:g}, {SWEET_ZONE_CENTER[1]:g}%).")
    axes.set_xlabel(xlabel, fontsize=12, labelpad=12)
    axes.set_ylabel(ylabel, fontsize=12, labelpad=10)
    axes.tick_params(labelsize=10)
    axes.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    axes.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    axes.set_axisbelow(True)
    axes.grid(color="#dfe5eb", linewidth=0.6, alpha=0.6)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    axes.set_title(title, fontsize=16, fontweight="bold", pad=18)
    points = list(zip(data[x_column], data[y_column]))
    axes.scatter(data[x_column], data[y_column], s=55, color=POINT_COLOR,
                 edgecolors="white", linewidths=0.7, zorder=3)
    _label_projection(axes, [(row.label, getattr(row, x_column), getattr(row, y_column))
                             for row in data.itertuples()])
    _attach_hover(figure, axes, points, data)
    return note


def _create_chart(metrics: pd.DataFrame, *, premium: bool) -> "Figure | None":
    data = prepare_chart_data(metrics)
    if data.empty:
        return None
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(figsize=(13, 8), facecolor="white")
    figure.subplots_adjust(left=0.09, right=0.97, top=0.81, bottom=0.15)
    note = _draw_panel(figure, axes, data, premium=premium)
    figure.text(0.09, 0.89, f"New York trading date: {data.iloc[0]['trading_date']}   •   {len(data)} tickers",
                fontsize=11, color="#526171")
    figure.text(0.09, 0.04, note, fontsize=10, color="#526171")
    if not premium:
        figure.text(0.09, 0.015, "Higher is not always better. Background color is a visual aid only.",
                    fontsize=9, color="#526171")
    _add_branding(figure)
    return figure


def create_volatility_premium_map(metrics: pd.DataFrame) -> "Figure | None":
    return _create_chart(metrics, premium=True)


def create_drawdown_skew_map(metrics: pd.DataFrame) -> "Figure | None":
    return _create_chart(metrics, premium=False)


def create_stock_metrics_charts(metrics: pd.DataFrame) -> tuple:
    return create_volatility_premium_map(metrics), create_drawdown_skew_map(metrics)


def create_stock_scanner_dashboard(metrics: pd.DataFrame) -> "Figure | None":
    data = prepare_chart_data(metrics)
    if data.empty:
        return None
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    figure, axes = plt.subplots(1, 2, figsize=(24, 10), facecolor="white")
    figure.subplots_adjust(left=0.055, right=0.98, top=0.81, bottom=0.20, wspace=0.20)
    for axis, premium in zip(axes, (True, False)):
        note = _draw_panel(figure, axis, data, premium=premium)
        axis.text(0, -0.18, note, transform=axis.transAxes, fontsize=10, color="#526171")
    axes[1].text(0, -0.23, "Middle is preferred; both extremes are less attractive. Visual aid only, not risk thresholds.",
                 transform=axes[1].transAxes, fontsize=9, color="#526171")
    figure.legend(
        handles=[Patch(facecolor=color, alpha=0.6, label=label) for color, label in zip(
            LANDSCAPE_COLORS, ("Preferred middle", "Transition", "Caution", "Extreme"))],
        loc="lower right", bbox_to_anchor=(0.98, 0.025), ncol=4, frameon=False, fontsize=9,
    )
    _add_branding(figure, dashboard=True)
    figure.text(0.085, 0.944, "Lemon Option Quant  |  Stock Scanner", fontsize=21, fontweight="bold")
    figure.text(0.085, 0.900, f"New York trading date: {data.iloc[0]['trading_date']}   •   {len(data)} tickers",
                fontsize=13, color="#526171")
    return figure


def save_stock_scanner_dashboard(figure, metrics: pd.DataFrame, output_directory=None) -> Path:
    data = prepare_chart_data(metrics)
    if data.empty:
        raise ValueError("Cannot export an empty dashboard")
    trading_date = date.fromisoformat(str(data.iloc[0]["trading_date"]))
    directory = Path(output_directory) if output_directory is not None else OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (trading_date.strftime("%Y%m%d") + FILENAME_SUFFIX)
    figure.savefig(path, format="jpeg", dpi=EXPORT_DPI, facecolor="white",
                   pil_kwargs={"quality": JPEG_QUALITY, "subsampling": 0})
    return path
