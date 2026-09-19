# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 19, 2026

from dataclasses import dataclass

import pandas as pd


@dataclass
class IVAnalysisResult:
    """
    Statistical summary of implied volatility
    for comparable historical options.
    """

    current_iv: float
    sample_count: int

    mean_iv: float
    median_iv: float
    min_iv: float
    max_iv: float


def analyze_iv(
    comparables: pd.DataFrame,
    current_iv: float,
) -> IVAnalysisResult:
    """
    Analyze current implied volatility against
    historical comparable option samples.

    Parameters
    ----------
    comparables : pandas.DataFrame
        Historical comparable options.

        Must contain the column:
        "iv"

    current_iv : float
        Current implied volatility.

        Example:
        39.2 means 39.2%.

    Returns
    -------
    IVAnalysisResult
        Basic historical IV statistics.

    Raises
    ------
    ValueError
        If the required IV column is missing,
        current IV is invalid, or no valid
        historical IV samples are available.
    """

    if "iv" not in comparables.columns:
        raise ValueError(
            "Missing required column: iv"
        )

    if current_iv < 0:
        raise ValueError(
            "Current IV must not be negative."
        )

    # -------------------------------------------------
    # Remove missing or invalid historical IV values
    # -------------------------------------------------

    iv_series = pd.to_numeric(
        comparables["iv"],
        errors="coerce",
    )

    iv_series = iv_series[
        iv_series.notna()
        & (iv_series >= 0)
    ]

    if iv_series.empty:
        raise ValueError(
            "No valid historical IV samples available."
        )

    # -------------------------------------------------
    # Calculate basic statistics
    # -------------------------------------------------

    return IVAnalysisResult(
        current_iv=float(current_iv),
        sample_count=len(iv_series),
        mean_iv=float(iv_series.mean()),
        median_iv=float(iv_series.median()),
        min_iv=float(iv_series.min()),
        max_iv=float(iv_series.max()),
    )