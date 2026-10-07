# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 13, 2026

import pandas as pd


MIN_STRIKE_RATIO = 0.70
MAX_STRIKE_RATIO = 1.30


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
        underlying_price = 200.00
        min_strike_ratio = 0.70

        Valid strike range:
        140.00 <= strike_price < 200.00
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


def filter_otm_calls(
    option_chain: pd.DataFrame,
    underlying_price: float,
    max_strike_ratio: float = MAX_STRIKE_RATIO,
) -> pd.DataFrame:
    """
    Filter the option chain for out-of-the-money call options.

    Selection rules:
        underlying_price
            < strike_price
            <= max_strike_ratio * underlying_price

    Example:
        underlying_price = 200.00
        max_strike_ratio = 1.30

        Valid strike range:
        200.00 < strike_price <= 260.00
    """

    if underlying_price <= 0:
        raise ValueError(
            "underlying_price must be greater than zero."
        )

    if max_strike_ratio <= 1:
        raise ValueError(
            "max_strike_ratio must be greater than 1."
        )

    calls = option_chain[
        option_chain["option_type"] == "CALL"
    ].copy()

    max_strike = (
        max_strike_ratio * underlying_price
    )

    filtered_calls = calls[
        (calls["strike_price"] > underlying_price)
        & (calls["strike_price"] <= max_strike)
    ].copy()

    return filtered_calls