# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 7, 2026

import sys

from .chart import display_ticker, show_opportunity_map
from .config import UNDERLYINGS
from .futu_client import FutuClient
from .market_data import scan_underlyings
from .models import ScanResult


def print_results(result: ScanResult) -> None:
    print("=" * 91)
    print("Lemon Live Short Put Scanner")
    print("=" * 91)
    labels = ("Price", "IV", "HV", "IV Rank", "VRP", "VRP Rank", "52W Drawdown")
    widths = (10, 10, 10, 10, 10, 10, 14)
    print(f"{'Symbol':<10}" + "".join(f"{label:>{width}}" for label, width in zip(labels, widths)))
    print("-" * 91)
    for snapshot in result.snapshots:
        values = (snapshot.price, snapshot.iv, snapshot.hv, snapshot.iv_rank,
                  snapshot.vrp, snapshot.vrp_rank, snapshot.drawdown_from_52w_high)
        print(f"{display_ticker(snapshot.symbol):<10}" + "".join(
            f"{value:>+{width}.2f}" if index == 4 else f"{value:>{width}.2f}"
            for index, (value, width) in enumerate(zip(values, widths))))
    print("\nLatest historical observation (price, IV, HV):")
    for snapshot in result.snapshots:
        print(f"  {snapshot.symbol}: {snapshot.observation_time}")
    print("IV Rank: current Futu overview; 52W Drawdown: % below highest historical underlying_price.")
    print(f"\nRequested symbols ({len(result.requested)}): {', '.join(result.requested)}")
    print(f"Successfully calculated symbols: {len(result.snapshots)}")
    print(f"Skipped symbols: {len(result.skipped)}")
    for symbol, reason in result.skipped.items():
        print(f"WARNING {symbol}: {reason}")


def main() -> int:
    try:
        with FutuClient() as client:
            result = scan_underlyings(client, UNDERLYINGS)
        # Close OpenD before the blocking chart window; rotation needs no connection.
    except Exception as error:
        reason = f"OpenD connection/SDK error: {' '.join(str(error).split())}"
        result = ScanResult(list(UNDERLYINGS), [], {symbol: reason for symbol in UNDERLYINGS})
    print_results(result)
    if not result.snapshots:
        print("No valid results; 3D Opportunity Map was not opened.")
        return 1
    try:
        show_opportunity_map(result.snapshots)
    except Exception as error:
        print(f"Cannot display 3D Opportunity Map: {error}", file=sys.stderr)
        return 1
    return 1 if result.skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
