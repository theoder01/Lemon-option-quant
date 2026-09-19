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

CURRENT_UNDERLYING_PRICE = 222.27
CURRENT_STRIKE = 190.0
CURRENT_DTE = 30
CURRENT_IV = 39.201


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

    # -------------------------------------------------
    # 2. Calculate target moneyness
    # -------------------------------------------------

    target_moneyness = calculate_moneyness(
        strike=CURRENT_STRIKE,
        underlying_price=CURRENT_UNDERLYING_PRICE,
    )

    # -------------------------------------------------
    # 3. Find comparable historical options
    # -------------------------------------------------

    comparables = find_comparable_options(
        df=history,
        underlying=UNDERLYING,
        target_moneyness=target_moneyness,
        target_dte=CURRENT_DTE,
    )

    if comparables.empty:
        print(
            "No comparable historical options found."
        )
        return

    # -------------------------------------------------
    # 4. Analyze implied volatility
    # -------------------------------------------------

    result = analyze_iv(
        comparables=comparables,
        current_iv=CURRENT_IV,
    )

    # -------------------------------------------------
    # 5. Print result
    # -------------------------------------------------

    print()
    print("=" * 60)
    print("IV Analysis")
    print("=" * 60)

    print(
        f"Underlying:       "
        f"{UNDERLYING}"
    )

    print(
        f"Spot:             "
        f"{CURRENT_UNDERLYING_PRICE:.2f}"
    )

    print(
        f"Strike:           "
        f"{CURRENT_STRIKE:.2f}"
    )

    print(
        f"Moneyness:        "
        f"{target_moneyness:.2%}"
    )

    print(
        f"Target DTE:       "
        f"{CURRENT_DTE}"
    )

    print()
    print(
        f"Current IV:       "
        f"{result.current_iv:.3f}%"
    )

    print(
        f"Comparable rows:  "
        f"{result.sample_count}"
    )

    print()
    print("Historical IV")
    print("-" * 40)

    print(
        f"Mean:             "
        f"{result.mean_iv:.3f}%"
    )

    print(
        f"Median:           "
        f"{result.median_iv:.3f}%"
    )

    print(
        f"Minimum:          "
        f"{result.min_iv:.3f}%"
    )

    print(
        f"Maximum:          "
        f"{result.max_iv:.3f}%"
    )


if __name__ == "__main__":
    main()