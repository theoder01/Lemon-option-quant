# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 7, 2026

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class UnderlyingSnapshot:
    symbol: str
    name: str
    price: float | None
    iv: float | None
    hv: float | None
    iv_rank: float | None
    vrp: float | None
    vrp_rank: float | None
    high_52w_close: float | None
    drawdown_from_52w_high: float | None
    observation_time: str


def snapshot_issue(snapshot: UnderlyingSnapshot) -> str | None:
    """Validate a complete observation without filling or recalculating metrics."""
    fields = ("price", "iv", "hv", "iv_rank", "vrp", "vrp_rank",
              "high_52w_close", "drawdown_from_52w_high")
    for field in fields:
        value = getattr(snapshot, field)
        if value is None:
            detail = " (insufficient/constant valid history)" if field == "vrp_rank" else ""
            return f"missing {field}{detail}"
        try:
            valid = not isinstance(value, bool) and isfinite(value)
        except (TypeError, ValueError, OverflowError):
            valid = False
        if not valid:
            return f"invalid {field}"
    for field in ("price", "high_52w_close"):
        if getattr(snapshot, field) <= 0:
            return f"nonpositive {field}"
    for field in ("iv", "hv"):
        if getattr(snapshot, field) < 0:
            return f"negative {field}"
    for field in ("iv_rank", "vrp_rank"):
        if not 0 <= getattr(snapshot, field) <= 100:
            return f"{field} outside 0–100"
    return None


@dataclass
class ScanResult:
    requested: list[str]
    snapshots: list[UnderlyingSnapshot]
    skipped: dict[str, str]
