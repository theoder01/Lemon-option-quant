# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 13, 2026

import pandas as pd


MIN_STRIKE_RATIO = 0.60


def filter_otm_puts(
    option_chain: pd.DataFrame,
    underlying_price: float,
    min_strike_ratio: float = MIN_STRIKE_RATIO,
) -> pd.DataFrame:
    """
    Filter the option chain for out-of-the-money put options.

    Selection rules:
        min_strike_ratio * underlying_price
            <= strike_price
            < underlying_price

    Example:
        underlying_price = 218.29
        min_strike_ratio = 0.60

        Valid strike range:
        130.97 <= strike_price < 218.29

    Parameters
    ----------
    option_chain : pandas.DataFrame
        Option chain returned by Futu OpenAPI.

    underlying_price : float
        Current price of the underlying security.

    min_strike_ratio : float
        Minimum strike price as a fraction of the underlying price.
        Default is 0.60.

    Returns
    -------
    pandas.DataFrame
        Filtered OTM put option chain.
    """

    if underlying_price <= 0:
        raise ValueError(
            "underlying_price must be greater than zero."
        )

    if not 0 < min_strike_ratio < 1:
        raise ValueError(
            "min_strike_ratio must be between 0 and 1."
        )

    puts = option_chain[
        option_chain["option_type"] == "PUT"
    ].copy()

    min_strike = (
        min_strike_ratio * underlying_price
    )

    filtered_puts = puts[
        (puts["strike_price"] >= min_strike)
        & (puts["strike_price"] < underlying_price)
    ].copy()

    return filtered_puts