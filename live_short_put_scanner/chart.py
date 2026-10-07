# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 7, 2026

"""Views of calculated snapshots only; no data access or financial formulas."""

from collections.abc import Iterable
from typing import TYPE_CHECKING

from .models import UnderlyingSnapshot, snapshot_issue

if TYPE_CHECKING:
    from matplotlib.figure import Figure

DRAWDOWN_LABEL = "52W Drawdown (%)"
VRP_LABEL = "VRP (IV - HV, pp)"
POINT_COLOR = "#356b99"
GUIDE_COLOR = "#728394"


def display_ticker(symbol: str) -> str:
    return symbol.removeprefix("US.")


def prepare_chart_data(snapshots: Iterable[UnderlyingSnapshot]) -> list[tuple[str, float, float, float]]:
    """Return complete observations in input order without inventing values."""
    return [(display_ticker(s.symbol), s.iv_rank, s.vrp, s.drawdown_from_52w_high)
            for s in snapshots if snapshot_issue(s) is None]


def prepare_projections(points: list[tuple[str, float, float, float]]) -> dict[str, list[tuple[str, float, float]]]:
    """Select coordinate pairs only; no normalization or universe-relative ranks."""
    return {
        "iv_vrp": [(label, x, y) for label, x, y, z in points],
        "iv_drawdown": [(label, x, z) for label, x, y, z in points],
        "vrp_drawdown": [(label, y, z) for label, x, y, z in points],
    }


def padded_zero_range(values: Iterable[float], minimum_padding: float = 1.0) -> tuple[float, float]:
    """Display limits include all observations and the mathematical origin."""
    values = [0.0, *values]
    low, high = min(values), max(values)
    padding = max((high - low) * 0.12, minimum_padding)
    return low - padding, high + padding


def reference_planes(y_limits: tuple[float, float], z_limits: tuple[float, float]) -> list[list[tuple[float, float, float]]]:
    """IV midpoint and raw premium zero boundary; no drawdown decision plane."""
    low, high = z_limits
    y_low, y_high = y_limits
    return [
        [(50, y_low, low), (50, y_high, low), (50, y_high, high), (50, y_low, high)],
        [(0, 0, low), (100, 0, low), (100, 0, high), (0, 0, high)],
    ]


def _draw_origin(axes, y_limits, z_limits):
    """True data-space origin, independent of the bounding box corner."""
    color = "#283b4b"
    for end, label in [((100, 0, 0), "X"), ((0, y_limits[1], 0), "Y"),
                       ((0, 0, z_limits[1]), "Z")]:
        axes.quiver(0, 0, 0, *end, color=color, linewidth=1.6, arrow_length_ratio=0.07)
        axes.text(*end, f" {label}", color=color, fontsize=10, fontweight="bold")
    axes.plot([0, 0], [y_limits[0], 0], [0, 0], color=color, linestyle=":", linewidth=1)
    axes.plot([0], [0], [0], marker="o", color=color, markersize=4)
    axes.text(0, 0, 0, "  O (0, 0, 0)", color=color, fontsize=8, va="top")
    axes.text2D(0.02, -0.10, "X: IV Rank   Y: VRP   Z: 52W Drawdown", transform=axes.transAxes,
                fontsize=8, color=color)


def tooltip_text(snapshot: UnderlyingSnapshot) -> str:
    return (f"Symbol: {display_ticker(snapshot.symbol)}\n"
            f"Price: {snapshot.price:.2f}\n"
            f"IV: {snapshot.iv:.2f}\n"
            f"HV: {snapshot.hv:.2f}\n"
            f"IV Rank: {snapshot.iv_rank:.2f}\n"
            f"VRP: {snapshot.vrp:+.2f}\n"
            f"VRP Rank: {snapshot.vrp_rank:.2f}\n"
            f"52W Drawdown: {snapshot.drawdown_from_52w_high:.2f}%")


def _attach_hover(figure, views, snapshots):
    """Pixel-distance hit testing also follows the current 3D rotation."""
    from mpl_toolkits.mplot3d import proj3d

    annotations = {}
    for axes, coordinates in views:
        annotation = axes.annotate("", xy=(0, 0), xytext=(12, 12),
                                   textcoords="offset points", fontsize=9,
                                   bbox=dict(boxstyle="round,pad=0.5", fc="white", ec=GUIDE_COLOR, alpha=0.97),
                                   zorder=100, annotation_clip=False)
        annotation.set_visible(False)
        annotations[axes] = annotation

    def on_motion(event):
        changed = False
        for axes, coordinates in views:
            annotation = annotations[axes]
            hit = None
            if event.inaxes is axes and event.button is None and event.x is not None and event.y is not None:
                positions = coordinates
                if axes.name == "3d":
                    positions = [proj3d.proj_transform(*point, axes.get_proj())[:2] for point in coordinates]
                pixels = axes.transData.transform(positions)
                distances = [(px - event.x) ** 2 + (py - event.y) ** 2 for px, py in pixels]
                index = min(range(len(distances)), key=distances.__getitem__)
                if distances[index] <= 12 ** 2:
                    hit = index
                    annotation.xy = positions[index]
                    right_half = event.x > (axes.bbox.x0 + axes.bbox.x1) / 2
                    top_half = event.y > (axes.bbox.y0 + axes.bbox.y1) / 2
                    annotation.set_position((-12 if right_half else 12, -12 if top_half else 12))
                    annotation.set_ha("right" if right_half else "left")
                    annotation.set_va("top" if top_half else "bottom")
                    annotation.set_text(tooltip_text(snapshots[index]))
            visible = hit is not None
            if annotation.get_visible() or visible:
                changed = True
            annotation.set_visible(visible)
        if changed:
            figure.canvas.draw_idle()

    figure.canvas.mpl_connect("motion_notify_event", on_motion)


def _label_projection(axes, points):
    # Try a few pixel offsets around each point. Only text moves, never the data.
    from matplotlib.text import Text

    figure = axes.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    occupied = [text.get_window_extent(renderer).padded(2) for text in axes.texts]
    offsets = sorted(((dx, dy) for dx in (7, 32, 57) for dy in (8, -14, 24, -30, 40, -46)),
                     key=lambda offset: offset[0] ** 2 + offset[1] ** 2)
    for label, x, y in points:
        x_low, x_high = axes.get_xlim()
        right = x > x_low + 0.85 * (x_high - x_low)
        annotation = axes.annotate(label, (x, y), xytext=(6, 7), textcoords="offset points",
                                   ha="right" if right else "left", fontsize=8, color="#203449",
                                   annotation_clip=False,
                                   arrowprops=dict(arrowstyle="-", color=GUIDE_COLOR, lw=0.45))
        best = None
        for dx, dy in offsets:
            annotation.set_position((-dx if right else dx, dy))
            annotation.update_positions(renderer)
            # Ignore the leader line when checking label collisions.
            box = Text.get_window_extent(annotation, renderer).padded(2)
            outside = not (axes.bbox.contains(box.x0, box.y0) and axes.bbox.contains(box.x1, box.y1))
            penalty = 100 * outside + sum(box.overlaps(other) for other in occupied)
            if best is None or penalty < best[0]:
                best = (penalty, annotation.get_position(), box)
            if penalty == 0:
                break
        annotation.set_position(best[1])
        occupied.append(best[2])


def create_opportunity_map(snapshots: Iterable[UnderlyingSnapshot]) -> "Figure | None":
    valid = [s for s in snapshots if snapshot_issue(s) is None]
    points = prepare_chart_data(valid)
    if not points:
        return None
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    _, xs, ys, zs = zip(*points)
    y_limits = padded_zero_range(ys)
    z_limits = padded_zero_range(zs, minimum_padding=2.0)
    figure = plt.figure(figsize=(16, 10), facecolor="white")
    grid = figure.add_gridspec(2, 2, left=0.07, right=0.95, bottom=0.12, top=0.86,
                              wspace=0.28, hspace=0.40)
    axes = figure.add_subplot(grid[0, 0], projection="3d")
    axes.scatter(xs, ys, zs, s=48, color=POINT_COLOR, edgecolors="white",
                 linewidths=0.6, depthshade=False)
    for index, (label, x, y, z) in enumerate(points):
        left = index % 2 == 0
        axes.text(x, y, z, f"  {label}" if left else f"{label}  ",
                  ha="left" if left else "right", va="bottom" if left else "top",
                  fontsize=8, color="#203449")
    axes.add_collection3d(Poly3DCollection(reference_planes(y_limits, z_limits),
                                         facecolors=GUIDE_COLOR, alpha=0.07,
                                         edgecolors=GUIDE_COLOR, linewidths=0.6))
    axes.set(xlim=(0, 100), ylim=y_limits, zlim=z_limits,
             xlabel="IV Rank", ylabel=VRP_LABEL, zlabel=DRAWDOWN_LABEL)
    _draw_origin(axes, y_limits, z_limits)
    axes.set_title("3D Opportunity Map", fontsize=12, pad=12)
    axes.view_init(elev=24, azim=-55)
    axes.grid(True)
    axes.tick_params(labelsize=8)
    axes.set_box_aspect((1.2, 1.2, 0.9))
    views = [(axes, list(zip(xs, ys, zs)))]
    projections = prepare_projections(points)
    definitions = [
        ("iv_vrp", grid[0, 1], "IV Rank × VRP", "IV Rank", VRP_LABEL),
        ("iv_drawdown", grid[1, 0], "IV Rank × 52W Drawdown", "IV Rank", DRAWDOWN_LABEL),
        ("vrp_drawdown", grid[1, 1], "VRP × 52W Drawdown", VRP_LABEL, DRAWDOWN_LABEL),
    ]
    for key, cell, title, xlabel, ylabel in definitions:
        projection = projections[key]
        _, px, py = zip(*projection)
        panel = figure.add_subplot(cell)
        panel.scatter(px, py, s=45, color=POINT_COLOR, edgecolors="white", linewidths=0.6, zorder=3)
        panel.set(xlim=y_limits if key == "vrp_drawdown" else (0, 100),
                  ylim=y_limits if key == "iv_vrp" else z_limits,
                  xlabel=xlabel, ylabel=ylabel, title=title)
        if key == "vrp_drawdown":
            panel.axvspan(y_limits[0], 0, color=GUIDE_COLOR, alpha=0.08)
            panel.axvline(0, color="#283b4b", linewidth=1.8)
        else:
            panel.axvline(50, color=GUIDE_COLOR, linestyle="--", linewidth=1)
        if key == "iv_vrp":
            panel.axhspan(y_limits[0], 0, color=GUIDE_COLOR, alpha=0.08)
            panel.axhline(0, color="#283b4b", linewidth=1.8)
            for x, y, label in [(0.02, 0.98, "IV Rank < 50 / VRP > 0"),
                                 (0.98, 0.98, "IV Rank ≥ 50 / VRP > 0"),
                                 (0.02, 0.02, "IV Rank < 50 / VRP ≤ 0"),
                                 (0.98, 0.02, "IV Rank ≥ 50 / VRP ≤ 0")]:
                panel.text(x, y, label, transform=panel.transAxes, fontsize=8, color="#647381",
                           ha="left" if x < 0.5 else "right", va="top" if y > 0.5 else "bottom")
        panel.grid(True, alpha=0.18)
        panel.set_axisbelow(True)
        panel.tick_params(labelsize=9)
        views.append((panel, list(zip(px, py))))
    figure.suptitle("Lemon Live Short Put Scanner", fontsize=19, y=0.97)
    figure.text(0.5, 0.925, "3D context + 2D projections • Hover over a point for exact values",
                ha="center", fontsize=11, color="#526170")
    figure.text(0.5, 0.05, "VRP ≤ 0: Stand Down (current workflow) • VRP > 0 is not an automatic trade signal",
                ha="center", fontsize=10, color="#526170")
    figure.text(0.5, 0.025, "IV Rank 50: visual midpoint only • No drawdown threshold • Deeper decline is not automatically better",
                ha="center", fontsize=9, color="#526170")
    for panel, definition in zip(figure.axes[1:], definitions):
        _label_projection(panel, projections[definition[0]])
    _attach_hover(figure, views, valid)
    return figure


def show_opportunity_map(snapshots: Iterable[UnderlyingSnapshot]) -> bool:
    figure = create_opportunity_map(snapshots)
    if figure is None:
        return False
    import matplotlib.pyplot as plt

    try:
        plt.show()
    finally:
        plt.close(figure)
    return True
