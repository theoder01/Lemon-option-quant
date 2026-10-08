# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 7, 2026

"""Pure calculations; unavailable/undefined results are explicitly None."""

from collections.abc import Iterable
from math import isfinite


def finite_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) else None


def normalize_official_iv_rank(value: object) -> float | None:
    """Preserve Futu's official rank; no local historical formula or fallback.

    This pure adapter retains the existing finite-number/missing-value policy.
    Historical sample sufficiency and flat IV ranges are handled by the provider,
    not reinterpreted here. Range validation remains in snapshot_issue.
    """
    return finite_number(value)


def calculate_vrp(iv: object, hv: object) -> float | None:
    """IV minus HV, in percentage points."""
    iv, hv = finite_number(iv), finite_number(hv)
    if iv is None or hv is None:
        return None
    return finite_number(iv - hv)


def calculate_vrp_rank(current_vrp: object, historical_vrps: Iterable[object]) -> float | None:
    """Min/max rank clipped to 0–100; undefined for empty/constant history."""
    current = finite_number(current_vrp)
    values = [v for item in historical_vrps if (v := finite_number(item)) is not None]
    if current is None or not values:
        return None
    low, high = min(values), max(values)
    width = finite_number(high - low)
    if width is None or width == 0:
        return None
    rank = finite_number((current - low) / width * 100)
    return None if rank is None else max(0.0, min(100.0, rank))


def calculate_high_52w_close(prices: Iterable[object]) -> float | None:
    values = [v for item in prices if (v := finite_number(item)) is not None and v > 0]
    return max(values, default=None)


def calculate_distance_from_high(current_price: object, high: object) -> float | None:
    current, high = finite_number(current_price), finite_number(high)
    if current is None or high is None or current <= 0 or high <= 0:
        return None
    return finite_number((high - current) / high * 100)
