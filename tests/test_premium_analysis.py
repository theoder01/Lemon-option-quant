# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 19, 2026

import pandas as pd

from option_quant.analytics.comparable_options import (
    find_comparable_options,
)
from option_quant.analytics.moneyness import (
    calculate_moneyness,
)
from option_quant.analytics.premium_analysis import (
    analyze_premium,
)
from option_quant.database import OptionDatabase


DATABASE_PATH = "data/options.db"

UNDERLYING = "US.NVDA"


def main():
    database = OptionDatabase(
        DATABASE_PATH
    )

    # -------------------------------------------------
    # 1. Load historical data
    # -------------------------------------------------

    history = database.load_underlying(
        UNDERLYING
    )

    if history.empty:
        print("No historical data found.")
        return

    # -------------------------------------------------
    # 2. Select the latest option snapshot
    # -------------------------------------------------

    history = history.copy()

    history["_parsed_time"] = pd.to_datetime(
        history["snapshot_time"],
        format="mixed",
        utc=True,
    )

    history = history.sort_values(
        "_parsed_time"
    )

    current = history.iloc[-1]

    current_snapshot_time = current["snapshot_time"]

    current_underlying_price = float(
        current["underlying_price"]
    )

    current_strike = float(
        current["strike"]
    )

    current_dte = int(
        current["dte"]
    )

    current_premium = float(
        current["last"]
    )

    # -------------------------------------------------
    # 3. Calculate target moneyness
    # -------------------------------------------------

    target_moneyness = calculate_moneyness(
        strike=current_strike,
        underlying_price=current_underlying_price,
    )

    # -------------------------------------------------
    # 4. Find historical comparable options
    # -------------------------------------------------

    comparables = find_comparable_options(
        df=history,
        underlying=UNDERLYING,
        target_moneyness=target_moneyness,
        target_dte=current_dte,
        current_snapshot_time=current_snapshot_time,
    )

    if comparables.empty:
        print(
            "No comparable historical options found."
        )
        return

    # -------------------------------------------------
    # 5. Analyze premium
    # -------------------------------------------------

    result = analyze_premium(
        comparables=comparables,
        current_premium=current_premium,
        current_underlying_price=current_underlying_price,
    )

    # -------------------------------------------------
    # 6. Print result
    # -------------------------------------------------

    print()
    print("=" * 60)
    print("Premium Analysis")
    print("=" * 60)

    print(
        f"Underlying:              "
        f"{UNDERLYING}"
    )

    print(
        f"Snapshot:                "
        f"{current_snapshot_time}"
    )

    print(
        f"Option:                  "
        f"{current['option_code']}"
    )

    print(
        f"Spot:                    "
        f"{current_underlying_price:.2f}"
    )

    print(
        f"Strike:                  "
        f"{current_strike:.2f}"
    )

    print(
        f"Moneyness:               "
        f"{target_moneyness:.2%}"
    )

    print(
        f"Target DTE:              "
        f"{current_dte}"
    )

    print()
    print(
        f"Current premium:         "
        f"${result.current_premium:.2f}"
    )

    print(
        f"Current premium ratio:   "
        f"{result.current_premium_ratio:.3%}"
    )

    print(
        f"Comparable rows:         "
        f"{result.sample_count}"
    )

    print()
    print("Historical Premium Ratio")
    print("-" * 40)

    print(
        f"Mean:                    "
        f"{result.mean_premium_ratio:.3%}"
    )

    print(
        f"Median:                  "
        f"{result.median_premium_ratio:.3%}"
    )

    print(
        f"Minimum:                 "
        f"{result.min_premium_ratio:.3%}"
    )

    print(
        f"Maximum:                 "
        f"{result.max_premium_ratio:.3%}"
    )

    print()
    print(
        f"Premium Percentile:      "
        f"{result.premium_percentile:.1f}%"
    )


if __name__ == "__main__":
    main()