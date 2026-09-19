# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 19, 2026

from option_quant.analytics.comparable_options import (
    find_comparable_options,
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


def main():
    database = OptionDatabase(
        DATABASE_PATH
    )

    # -------------------------------------------------
    # 1. Load historical NVDA data
    # -------------------------------------------------

    history = database.load_underlying(
        UNDERLYING
    )

    print(
        f"Historical rows loaded: "
        f"{len(history)}"
    )

    # -------------------------------------------------
    # 2. Calculate target moneyness
    # -------------------------------------------------

    target_moneyness = calculate_moneyness(
        strike=CURRENT_STRIKE,
        underlying_price=CURRENT_UNDERLYING_PRICE,
    )

    print(
        f"Target moneyness: "
        f"{target_moneyness:.4f}"
    )

    print(
        f"Target DTE: "
        f"{CURRENT_DTE}"
    )

    # -------------------------------------------------
    # 3. Find historical comparable options
    # -------------------------------------------------

    comparables = find_comparable_options(
        df=history,
        underlying=UNDERLYING,
        target_moneyness=target_moneyness,
        target_dte=CURRENT_DTE,
    )

    print()
    print("=" * 60)
    print("Historical Comparable Options")
    print("=" * 60)

    if comparables.empty:
        print(
            "No comparable historical options found."
        )
        return

    columns = [
        "snapshot_time",
        "underlying_price",
        "option_code",
        "strike",
        "moneyness",
        "dte",
        "last",
        "iv",
    ]

    print(
        comparables[
            columns
        ].to_string(
            index=False
        )
    )

    print()
    print(
        f"Comparable rows: "
        f"{len(comparables)}"
    )


if __name__ == "__main__":
    main()