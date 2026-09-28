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
from option_quant.analytics.put_annualized_return import (
    PutAnnualizedReturnResult,
    calculate_initial_annualized_return,
)
from option_quant.database import OptionDatabase, TABLE_NAME
from option_quant.time_utils import get_trading_date


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
        raise ValueError("请输入美股代码，例如 IREN 或 US.NVDA。")
    return value


def _finite(value: float, label: str, positive: bool = False) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{label}必须是有效数字。") from error
    if isinstance(value, bool) or not math.isfinite(number) or number < 0 or (positive and number == 0):
        raise ValueError(f"{label}必须{'大于零' if positive else '不小于零'}，且为有限数字。")
    return number


def historical_rows(history: pd.DataFrame, underlying: str, as_of: datetime) -> pd.DataFrame:
    """Only past rows of the requested underlying; malformed dates are excluded."""
    if as_of.utcoffset() is None:
        raise ValueError("估值时间必须带时区。")
    if history.empty:
        return history.copy()
    if not {"underlying", "snapshot_time"}.issubset(history.columns):
        raise ValueError("历史库缺少 underlying 或 snapshot_time 字段。")
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
class PutPreview:
    underlying: str
    annual: PutAnnualizedReturnResult
    premium: PremiumAnalysisResult | None
    moneyness: float | None
    trading_days: int
    sample_start: str | None
    sample_end: str | None
    notes: tuple[str, ...]


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
    premium = _finite(premium, "每股权利金")
    strike = _finite(strike, "行权价", positive=True)
    if as_of.utcoffset() is None:
        raise ValueError("估值时间必须带时区。")
    if type(expiry) is not date or expiry <= get_trading_date(as_of):
        raise ValueError("到期日须晚于纽约今天；第一版暂不计算到期日当天的合约。")
    if spot is not None:
        spot = _finite(spot, "标的现价", positive=True)
    annual = calculate_initial_annualized_return(
        strike=strike, premium=premium, as_of=get_trading_date(as_of), expiration=expiry,
    )
    notes = []
    result = None
    moneyness = strike / spot if spot is not None else None
    days = 0
    start = end = None
    if spot is None:
        notes.append("补充标的现价后可计算历史百分位；年化不需要现价。")
    elif moneyness > 1:
        notes.append("当前为价内 Put；现有历史库只采集价外 Put，暂不提供历史百分位。")
    elif history.empty:
        notes.append("没有该标的历史记录；仍可计算初始年化。")
    else:
        required = {"last", "strike", "underlying_price", "dte", "option_code"}
        if not required.issubset(history.columns):
            notes.append("历史库缺少价格、合约代码或 DTE 字段，无法计算百分位。")
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
                    if result.sample_count < 20 or days < 5:
                        notes.append("历史样本较少或覆盖天数较短，百分位仅供参考。")
            if result is None:
                notes.append("没有满足相近价内外程度和 DTE 的有效历史 Put 样本。")
    return PutPreview(underlying, annual, result, moneyness, days, start, end, tuple(notes))
