# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 28, 2026

"""Read-only, offline analysis shared by the simple Put window and tests."""

from dataclasses import dataclass
from contextlib import contextmanager
from datetime import date, datetime
import math
from pathlib import Path
import re
import sqlite3

import pandas as pd

from option_quant.analytics.comparable_options import find_comparable_options
from option_quant.analytics.premium_analysis import PremiumAnalysisResult, analyze_premium
from option_quant.analytics.iv_analysis import IVAnalysisResult, analyze_iv, valid_iv_values
from option_quant.analytics.put_annualized_return import (
    PutAnnualizedReturnResult,
    calculate_initial_annualized_return,
)
from option_quant.database import OptionDatabase, TABLE_NAME
from option_quant.time_utils import get_trading_date


LIMITED_HISTORY_SAMPLES = 20
LIMITED_HISTORY_DAYS = 5


class ReadOnlyOptionDatabase(OptionDatabase):
    """Reuse existing queries without creating or modifying database files."""

    def __init__(self, database_path: str):
        self.database_path = Path(database_path).resolve()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(
            self.database_path.as_uri() + "?mode=ro", uri=True, timeout=2,
        )
        try:
            yield connection
        finally:
            connection.close()

    def underlyings(self) -> list[str]:
        with self._connect() as connection:
            return [row[0] for row in connection.execute(
                f"SELECT DISTINCT underlying FROM {TABLE_NAME} ORDER BY underlying"
            ) if row[0]]


def normalize_underlying(value: str) -> str:
    value = value.strip().upper()
    if not value.startswith("US."):
        value = "US." + value
    if not re.fullmatch(r"US\.[A-Z][A-Z0-9.\-]*", value):
        raise ValueError("Enter a US stock symbol, such as IREN or US.NVDA.")
    return value


def _finite(value: float, label: str, positive: bool = False) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{label} must be a valid number.") from error
    if isinstance(value, bool) or not math.isfinite(number) or number < 0 or (positive and number == 0):
        raise ValueError(f"{label} must be finite and {'positive' if positive else 'nonnegative'}.")
    return number


def historical_rows(history: pd.DataFrame, underlying: str, as_of: datetime) -> pd.DataFrame:
    """Only past rows of the requested underlying; malformed dates are excluded."""
    if as_of.utcoffset() is None:
        raise ValueError("Valuation time must be timezone-aware.")
    if history.empty:
        return history.copy()
    if not {"underlying", "snapshot_time"}.issubset(history.columns):
        raise ValueError("History is missing underlying or snapshot_time fields.")
    rows = history.copy()
    rows["_time"] = pd.to_datetime(rows["snapshot_time"], format="mixed", utc=True, errors="coerce")
    return rows[(rows["underlying"] == underlying) & (rows["_time"] < as_of)].copy()


def latest_reference(history: pd.DataFrame, underlying: str, as_of: datetime):
    """Return a timestamped historical stock quote and known future expirations."""
    rows = historical_rows(history, underlying, as_of)
    expirations = []
    if "expiry" in rows:
        dates = pd.to_datetime(rows["expiry"], errors="coerce").dropna().dt.date
        expirations = sorted({d.isoformat() for d in dates if d > get_trading_date(as_of)})
    if rows.empty or "underlying_price" not in rows:
        return None, None, expirations
    price = pd.to_numeric(rows["underlying_price"], errors="coerce")
    rows = rows[price.map(lambda p: math.isfinite(p) and p > 0)].sort_values("_time")
    if rows.empty:
        return None, None, expirations
    row = rows.iloc[-1]
    return float(row["underlying_price"]), row["_time"].isoformat(), expirations


@dataclass(frozen=True)
class PutIVReference:
    """Stored contract IV and its prior peers, independent of entry decisions."""

    status: str = "current_unavailable"
    current_iv: float | None = None
    option_code: str | None = None
    snapshot_time: str | None = None
    analysis: IVAnalysisResult | None = None
    sample_count: int = 0
    trading_days: int = 0
    limited_history: bool = False


def analyze_put_iv_reference(
    *, history: pd.DataFrame, comparables: pd.DataFrame, underlying: str,
    expiry: date, strike: float, as_of: datetime, comparison_available: bool,
) -> PutIVReference:
    """Match the latest exact Put; reuse premium peers with a stricter time cutoff.

    IV is stored in percentage points, not a decimal fraction. Do not fall back
    to a different contract or older quote when the latest matching IV is invalid.
    The peer moneyness/DTE targets remain those of the current GUI inputs.
    """
    required = {"underlying", "snapshot_time", "expiry", "strike", "option_code", "iv"}
    if history.empty or not required.issubset(history.columns):
        return PutIVReference()
    rows = historical_rows(history, underlying, as_of)
    rows = rows[
        rows["option_code"].astype(str).str.contains(r"P\d+$", regex=True)
        & (pd.to_numeric(rows["strike"], errors="coerce") == strike)
        & (pd.to_datetime(rows["expiry"], errors="coerce").dt.date == expiry)
    ]
    if rows.empty:
        return PutIVReference()
    latest = rows[rows["_time"] == rows["_time"].max()]
    if len(latest) != 1:
        return PutIVReference(status="ambiguous_current")
    current = latest.iloc[0]
    source = dict(option_code=str(current["option_code"]), snapshot_time=current["_time"].isoformat())
    valid_current = valid_iv_values(latest)
    if valid_current.empty:
        return PutIVReference(status="invalid_current", **source)
    source["current_iv"] = float(valid_current.iloc[0])
    if not comparison_available:
        return PutIVReference(status="comparison_unavailable", **source)
    if comparables.empty or "iv" not in comparables:
        return PutIVReference(status="history_insufficient", **source)
    # Exclude the source snapshot, simultaneous observations, and later rows.
    prior = comparables[comparables["_time"] < current["_time"]].reset_index(drop=True)
    valid = valid_iv_values(prior)
    if valid.empty:
        return PutIVReference(status="history_insufficient", **source)
    analysis = analyze_iv(prior, source["current_iv"])
    trading_days = int(prior.loc[valid.index, "_time"].dt.tz_convert("America/New_York").dt.date.nunique())
    return PutIVReference(
        status="available", analysis=analysis, sample_count=analysis.sample_count,
        trading_days=trading_days,
        limited_history=analysis.sample_count < LIMITED_HISTORY_SAMPLES or trading_days < LIMITED_HISTORY_DAYS,
        **source,
    )


@dataclass(frozen=True)
class PutPreview:
    underlying: str
    annual: PutAnnualizedReturnResult
    premium: PremiumAnalysisResult | None
    moneyness: float | None
    trading_days: int
    sample_start: str | None
    sample_end: str | None
    notes: tuple[str, ...]
    iv: PutIVReference = PutIVReference()


def analyze_put_preview(
    *, underlying: str, expiry: date, premium: float, strike: float,
    spot: float | None, as_of: datetime, history: pd.DataFrame,
) -> PutPreview:
    """One standard Put; existing normalized-premium percentile and fee logic.

    Calendar DTE uses today's New York date. Same-day expiration is excluded
    because a date-only UI cannot know the exact contract cutoff time.
    Percentile is snapshot-row weighted, using historical last / stock price.
    """
    underlying = normalize_underlying(underlying)
    premium = _finite(premium, "Premium per share")
    strike = _finite(strike, "Strike price", positive=True)
    if as_of.utcoffset() is None:
        raise ValueError("Valuation time must be timezone-aware.")
    if type(expiry) is not date or expiry <= get_trading_date(as_of):
        raise ValueError("Expiration must be after today in New York; same-day expiration is not supported.")
    if spot is not None:
        spot = _finite(spot, "Spot price", positive=True)
    annual = calculate_initial_annualized_return(
        strike=strike, premium=premium, as_of=get_trading_date(as_of), expiration=expiry,
    )
    notes = []
    result = None
    comparable = pd.DataFrame()
    moneyness = strike / spot if spot is not None else None
    days = 0
    start = end = None
    if spot is None:
        notes.append("Enter a spot price to calculate historical percentile; annualized return does not require it.")
    elif moneyness > 1:
        notes.append("This Put is in the money; history only collects out-of-the-money Puts, so percentile is unavailable.")
    elif history.empty:
        notes.append("No history for this underlying; initial annualized return is still available.")
    else:
        required = {"last", "strike", "underlying_price", "dte", "option_code"}
        if not required.issubset(history.columns):
            notes.append("History is missing price, option code, or DTE fields; percentile is unavailable.")
        else:
            rows = historical_rows(history, underlying, as_of)
            # Explicitly exclude calls; the existing collector stores standard puts.
            rows = rows[rows["option_code"].astype(str).str.contains(r"P\d+$", regex=True)].copy()
            for column in ["last", "strike", "underlying_price", "dte"]:
                rows[column] = pd.to_numeric(rows[column], errors="coerce")
                rows = rows[rows[column].map(math.isfinite)]
            rows = rows[(rows["strike"] > 0) & (rows["underlying_price"] > 0)
                        & (rows["last"] >= 0) & (rows["dte"] >= 0)
                        & (rows["dte"] % 1 == 0)]
            if not rows.empty:
                comparable = find_comparable_options(
                    df=rows, underlying=underlying, target_moneyness=moneyness,
                    target_dte=int(annual.remaining_days), current_snapshot_time=as_of.isoformat(),
                )
                if not comparable.empty:
                    result = analyze_premium(comparable, premium, spot)
                    dates = comparable["_time"].dt.tz_convert("America/New_York").dt.date
                    days = dates.nunique()
                    start, end = str(dates.min()), str(dates.max())
                    if result.sample_count < LIMITED_HISTORY_SAMPLES or days < LIMITED_HISTORY_DAYS:
                        notes.append("Historical samples or date coverage are limited; percentile is for reference only.")
            if result is None:
                notes.append("No valid historical Put samples with similar moneyness and DTE.")
    iv = analyze_put_iv_reference(
        history=history, comparables=comparable, underlying=underlying,
        expiry=expiry, strike=strike, as_of=as_of,
        comparison_available=moneyness is not None and moneyness <= 1,
    )
    return PutPreview(underlying, annual, result, moneyness, days, start, end, tuple(notes), iv)
