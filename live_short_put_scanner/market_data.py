# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 7, 2026

from datetime import date, timedelta

import pandas as pd

from .calculations import (
    calculate_distance_from_high, calculate_high_52w_close,
    calculate_vrp, calculate_vrp_rank, finite_number,
)
from .futu_client import FutuClient, FutuDataError
from .models import ScanResult, UnderlyingSnapshot, snapshot_issue


def get_snapshot(client: FutuClient, symbol: str, end_date: date | None = None) -> UnderlyingSnapshot:
    end = end_date or date.today()
    begin = end - timedelta(days=365)
    overview = client.get_overview(symbol)
    history = client.get_history(symbol, begin.isoformat(), end.isoformat())
    if not {"code", "iv_rank"}.issubset(overview.columns):
        raise FutuDataError(f"{symbol}: overview missing required fields")
    current_overview = overview.loc[overview["code"] == symbol]
    if len(current_overview) != 1:
        raise FutuDataError(f"{symbol}: expected exactly one overview record")
    if not {"code", "time", "iv", "hv", "underlying_price"}.issubset(history.columns):
        raise FutuDataError(f"{symbol}: history missing required fields")
    history = history.loc[history["code"] == symbol].copy()
    history["_time"] = pd.to_datetime(history["time"], errors="coerce", format="mixed", utc=True)
    start_time = pd.Timestamp(begin, tz="UTC")
    stop_time = pd.Timestamp(end + timedelta(days=1), tz="UTC")
    history = history.loc[(history["_time"] >= start_time) & (history["_time"] < stop_time)]
    if history.empty:
        raise FutuDataError(f"{symbol}: no dated historical observations in the requested year")
    history = history.sort_values("_time", kind="stable")
    latest = history.iloc[-1]  # Explicit time sort, never assume API row order.
    official = current_overview.iloc[0]
    iv, hv = finite_number(latest["iv"]), finite_number(latest["hv"])
    price = finite_number(latest["underlying_price"])
    if price is not None and price <= 0:
        price = None
    vrp = calculate_vrp(iv, hv)
    # Reject invalid negative volatility observations without changing the VRP formula.
    pairs = ((finite_number(i), finite_number(h)) for i, h in zip(history["iv"], history["hv"]))
    historical_vrps = [calculate_vrp(i, h) for i, h in pairs
                      if i is not None and h is not None and i >= 0 and h >= 0]
    high = calculate_high_52w_close(history["underlying_price"])
    return UnderlyingSnapshot(
        symbol=symbol, name=str(official.get("name", symbol)), price=price, iv=iv, hv=hv,
        iv_rank=finite_number(official["iv_rank"]), vrp=vrp,
        vrp_rank=calculate_vrp_rank(vrp, historical_vrps), high_52w_close=high,
        drawdown_from_52w_high=calculate_distance_from_high(price, high),
        observation_time=str(latest["time"]),
    )


def scan_underlyings(client: FutuClient, symbols: list[str]) -> ScanResult:
    """Isolate each symbol's API/data failures and preserve configured order."""
    result = ScanResult(list(symbols), [], {})
    for symbol in symbols:
        try:
            snapshot = get_snapshot(client, symbol)
            issue = snapshot_issue(snapshot)
            if issue is None:
                result.snapshots.append(snapshot)
            else:
                result.skipped[symbol] = issue
        except Exception as error:
            result.skipped[symbol] = " ".join(str(error).split()) or type(error).__name__
    return result
