# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 19, 2026

from option_quant.analytics.comparable_options import (
    find_comparable_options,
)
from option_quant.analytics.iv_analysis import (
    analyze_iv,
)
from option_quant.analytics.moneyness import (
    calculate_moneyness,
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

    history = history.sort_values(
        "snapshot_time"
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
    current_iv = float(
        current["iv"]
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
    # 5. Analyze implied volatility
    # -------------------------------------------------

    result = analyze_iv(
        comparables=comparables,
        current_iv=current_iv,
    )

    # -------------------------------------------------
    # 6. Print result
    # -------------------------------------------------

    print()
    print("=" * 60)
    print("IV Analysis")
    print("=" * 60)

    print(f"Underlying:       {UNDERLYING}")
    print(f"Snapshot:         {current_snapshot_time}")
    print(f"Option:           {current['option_code']}")
    print(f"Spot:             {current_underlying_price:.2f}")
    print(f"Strike:           {current_strike:.2f}")
    print(f"Moneyness:        {target_moneyness:.2%}")
    print(f"Target DTE:       {current_dte}")

    print()
    print(f"Current IV:       {result.current_iv:.3f}%")
    print(f"Comparable rows:  {result.sample_count}")

    print()
    print("Historical IV")
    print("-" * 40)

    print(f"Mean:             {result.mean_iv:.3f}%")
    print(f"Median:           {result.median_iv:.3f}%")
    print(f"Minimum:          {result.min_iv:.3f}%")
    print(f"Maximum:          {result.max_iv:.3f}%")

    print()
    print(
        f"IV Percentile:    "
        f"{result.iv_percentile:.1f}%"
    )


if __name__ == "__main__":
    main()