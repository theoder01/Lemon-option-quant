# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 19, 2026

from dataclasses import dataclass

import pandas as pd


@dataclass
class PremiumAnalysisResult:
    """
    Statistical summary of normalized option premiums
    for comparable historical options.
    """

    current_premium: float
    current_premium_ratio: float
    sample_count: int

    mean_premium_ratio: float
    median_premium_ratio: float
    min_premium_ratio: float
    max_premium_ratio: float


def calculate_premium_ratio(
    premium: float,
    underlying_price: float,
) -> float:
    """
    Calculate normalized option premium.

    Premium ratio is defined as:

        premium / underlying_price

    Example
    -------
    Premium = 0.66
    Underlying price = 222.27

    Premium ratio = 0.66 / 222.27
                  = 0.00297
                  = 0.297%
    """

    if premium < 0:
        raise ValueError(
            "Premium must not be negative."
        )

    if underlying_price <= 0:
        raise ValueError(
            "Underlying price must be greater than zero."
        )

    return premium / underlying_price


def analyze_premium(
    comparables: pd.DataFrame,
    current_premium: float,
    current_underlying_price: float,
) -> PremiumAnalysisResult:
    """
    Analyze the current option premium against
    historical comparable option samples.

    Historical premiums are normalized by the
    underlying price before comparison.

    Parameters
    ----------
    comparables : pandas.DataFrame
        Historical comparable options.

        Must contain:
        - last
        - underlying_price

    current_premium : float
        Current option premium.

    current_underlying_price : float
        Current underlying price.

    Returns
    -------
    PremiumAnalysisResult
        Basic historical premium-ratio statistics.
    """

    required_columns = [
        "last",
        "underlying_price",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in comparables.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    current_premium_ratio = (
        calculate_premium_ratio(
            premium=current_premium,
            underlying_price=current_underlying_price,
        )
    )

    # -------------------------------------------------
    # Convert historical values to numeric
    # -------------------------------------------------

    premiums = pd.to_numeric(
        comparables["last"],
        errors="coerce",
    )

    underlying_prices = pd.to_numeric(
        comparables["underlying_price"],
        errors="coerce",
    )

    # -------------------------------------------------
    # Keep only valid historical samples
    # -------------------------------------------------

    valid_mask = (
        premiums.notna()
        & underlying_prices.notna()
        & (premiums >= 0)
        & (underlying_prices > 0)
    )

    premiums = premiums[
        valid_mask
    ]

    underlying_prices = underlying_prices[
        valid_mask
    ]

    if premiums.empty:
        raise ValueError(
            "No valid historical premium samples available."
        )

    # -------------------------------------------------
    # Normalize historical premiums
    # -------------------------------------------------

    premium_ratios = (
        premiums
        / underlying_prices
    )

    # -------------------------------------------------
    # Calculate basic statistics
    # -------------------------------------------------

    return PremiumAnalysisResult(
        current_premium=float(
            current_premium
        ),
        current_premium_ratio=float(
            current_premium_ratio
        ),
        sample_count=len(
            premium_ratios
        ),
        mean_premium_ratio=float(
            premium_ratios.mean()
        ),
        median_premium_ratio=float(
            premium_ratios.median()
        ),
        min_premium_ratio=float(
            premium_ratios.min()
        ),
        max_premium_ratio=float(
            premium_ratios.max()
        ),
    )