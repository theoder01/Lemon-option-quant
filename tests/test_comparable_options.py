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


def main():
    # Current option:
    # Spot = 220
    # Strike = 190
    # DTE = 30

    target_moneyness = calculate_moneyness(
        strike=190,
        underlying_price=220,
    )

    print(
        f"Target moneyness: "
        f"{target_moneyness:.4f}"
    )

    history = pd.DataFrame(
        {
            "option_code": [
                "MATCH_1",
                "MATCH_2",
                "BAD_MONEYNESS",
                "BAD_DTE",
                "BAD_UNDERLYING",
            ],
            "underlying": [
                "US.NVDA",
                "US.NVDA",
                "US.NVDA",
                "US.NVDA",
                "US.GOOG",
            ],
            "underlying_price": [
                200.0,
                250.0,
                200.0,
                220.0,
                200.0,
            ],
            "strike": [
                172.0,
                215.0,
                150.0,
                190.0,
                172.0,
            ],
            "dte": [
                28,
                33,
                30,
                50,
                30,
            ],
            "iv": [
                35.0,
                40.0,
                45.0,
                38.0,
                30.0,
            ],
            "last": [
                2.50,
                3.20,
                1.00,
                4.00,
                2.00,
            ],
        }
    )

    result = find_comparable_options(
        df=history,
        underlying="US.NVDA",
        target_moneyness=target_moneyness,
        target_dte=30,
    )

    print()
    print("Comparable Options")
    print("-" * 60)

    print(
        result[
            [
                "option_code",
                "underlying_price",
                "strike",
                "moneyness",
                "dte",
                "iv",
                "last",
            ]
        ].to_string(
            index=False
        )
    )

    print()
    print(
        f"Comparable rows: {len(result)}"
    )


if __name__ == "__main__":
    main()