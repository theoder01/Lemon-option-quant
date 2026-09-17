# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 13, 2026

import pandas as pd

from option_quant.filters import filter_otm_puts
from option_quant.time_utils import now_utc


SNAPSHOT_BATCH_SIZE = 200

def _get_full_option_chain(
    client,
    underlying: str,
) -> pd.DataFrame:
    """
    Get the option chain for an underlying
    from today up to one year.

    Futu limits one option-chain query to a maximum
    date range of about 30 days, so the available
    expiration dates are queried first and then grouped
    into multiple date windows.
    """

    expiration_data = client.get_option_expiration_dates(
        underlying
    )

    if expiration_data.empty:
        return pd.DataFrame()

    expiration_dates = (
        pd.to_datetime(
            expiration_data["strike_time"]
        )
        .sort_values()
        .drop_duplicates()
        .tolist()
    )

    today = pd.Timestamp.today().normalize()
    max_expiry = today + pd.DateOffset(years=1)

    expiration_dates = [
        expiry
        for expiry in expiration_dates
        if today <= expiry <= max_expiry
    ]

    if not expiration_dates:
        return pd.DataFrame()

    print()
    print(f"Available expirations for {underlying}:")

    for expiry in expiration_dates:
        print(expiry.date())

    print()

    chains = []

    window_start = expiration_dates[0]
    window_end = window_start

    for expiry in expiration_dates:

        if (expiry - window_start).days <= 30:
            window_end = expiry

        else:
            chain = client.get_option_chain(
                code=underlying,
                start=window_start.strftime("%Y-%m-%d"),
                end=window_end.strftime("%Y-%m-%d"),
            )

            chains.append(chain)

            window_start = expiry
            window_end = expiry

    # Last window
    chain = client.get_option_chain(
        code=underlying,
        start=window_start.strftime("%Y-%m-%d"),
        end=window_end.strftime("%Y-%m-%d"),
    )

    chains.append(chain)

    full_chain = pd.concat(
        chains,
        ignore_index=True,
    )

    full_chain = (
        full_chain
        .drop_duplicates(subset=["code"])
        .reset_index(drop=True)
    )

    return full_chain


def _get_option_snapshots(
    client,
    option_codes: list[str],
    batch_size: int = SNAPSHOT_BATCH_SIZE,
) -> pd.DataFrame:
    """
    Get market snapshots for option contracts in batches.
    """

    if not option_codes:
        return pd.DataFrame()

    snapshots = []

    for start in range(
        0,
        len(option_codes),
        batch_size,
    ):
        batch = option_codes[
            start:start + batch_size
        ]

        data = client.get_market_snapshot(
            batch
        )

        snapshots.append(data)

    return pd.concat(
        snapshots,
        ignore_index=True,
    )


def collect_option_snapshot(
    client,
    underlying: str,
) -> pd.DataFrame:
    """
    Collect one complete option snapshot for an underlying.

    Current strategy:
    - Put options only
    - Out-of-the-money only
    - Strike >= 60% of underlying price
    - Strike < underlying price
    - Expiration dates from today up to one year
    """

    snapshot_time = now_utc()

    # ---------------------------------------------------------
    # 1. Underlying price
    # ---------------------------------------------------------

    underlying_price = client.get_last_price(
        underlying
    )

    # ---------------------------------------------------------
    # 2. Full option chain
    # ---------------------------------------------------------

    option_chain = _get_full_option_chain(
        client=client,
        underlying=underlying,
    )

    # ---------------------------------------------------------
    # 3. Filter relevant OTM puts
    # ---------------------------------------------------------

    filtered_chain = filter_otm_puts(
        option_chain=option_chain,
        underlying_price=underlying_price,
    )

    option_codes = filtered_chain[
        "code"
    ].tolist()

    print()
    print(f"Underlying: {underlying}")
    print(
        f"Underlying price: "
        f"{underlying_price:.2f}"
    )
    print(
        f"All Put contracts: "
        f"{len(option_chain[option_chain['option_type'] == 'PUT'])}"
    )
    print(
        f"Filtered Put contracts: "
        f"{len(filtered_chain)}"
    )
    print()

    if not option_codes:
        return pd.DataFrame()

    # ---------------------------------------------------------
    # 4. Dynamic option market snapshots
    # ---------------------------------------------------------

    snapshots = _get_option_snapshots(
        client=client,
        option_codes=option_codes,
    )

    # ---------------------------------------------------------
    # 5. Build clean 17-column dataset
    # ---------------------------------------------------------

    result = pd.DataFrame(
        {
            "snapshot_time":
                snapshot_time,

            "underlying":
                underlying,

            "underlying_price":
                underlying_price,

            "option_code":
                snapshots["code"],

            "expiry":
                snapshots["strike_time"],

            "strike":
                snapshots["option_strike_price"],

            "dte":
                snapshots[
                    "option_expiry_date_distance"
                ],

            "last":
                snapshots["last_price"],

            "bid":
                snapshots["bid_price"],

            "ask":
                snapshots["ask_price"],

            "volume":
                snapshots["volume"],

            "open_interest":
                snapshots[
                    "option_open_interest"
                ],

            "iv":
                snapshots[
                    "option_implied_volatility"
                ],

            "delta":
                snapshots["option_delta"],

            "gamma":
                snapshots["option_gamma"],

            "vega":
                snapshots["option_vega"],

            "theta":
                snapshots["option_theta"],
        }
    )

    return result