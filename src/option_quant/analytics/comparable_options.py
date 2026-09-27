# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 19, 2026

import pandas as pd

from option_quant.analytics.moneyness import calculate_moneyness


def find_comparable_options(
    df: pd.DataFrame,
    underlying: str,
    target_moneyness: float,
    target_dte: int,
    current_snapshot_time: str,
    moneyness_tolerance: float = 0.02,
    dte_tolerance: int = 5,
) -> pd.DataFrame:
    """
    Find historical options with similar moneyness and DTE.

    Only snapshots strictly earlier than current_snapshot_time
    are included.

    Parameters
    ----------
    df : pandas.DataFrame
        Historical option snapshot data.

    underlying : str
        Underlying security code, for example "US.NVDA".

    target_moneyness : float
        Target strike / underlying price ratio.

        Example:
        0.86 means the strike is approximately
        86% of the underlying price.

    target_dte : int
        Target days to expiration.

    current_snapshot_time : str
        Timestamp of the option being analyzed.

        Only snapshots earlier than this timestamp
        are included in the historical comparison.

    moneyness_tolerance : float
        Allowed difference from target moneyness.

        Default 0.02 means +/- 2 percentage points.

    dte_tolerance : int
        Allowed difference from target DTE.

        Default 5 means +/- 5 days.

    Returns
    -------
    pandas.DataFrame
        Historical options matching the requested
        underlying, moneyness range, DTE range,
        and historical time constraint.
    """

    required_columns = [
        "snapshot_time",
        "underlying",
        "underlying_price",
        "strike",
        "dte",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    if not 0 < target_moneyness <= 1:
        raise ValueError(
            "Target moneyness must be "
            "greater than 0 and at most 1."
        )

    if target_dte < 0:
        raise ValueError(
            "Target DTE must not be negative."
        )

    if moneyness_tolerance < 0:
        raise ValueError(
            "Moneyness tolerance must not be negative."
        )

    if dte_tolerance < 0:
        raise ValueError(
            "DTE tolerance must not be negative."
        )

    # Convert timestamps to UTC before comparison.
    current_time = pd.to_datetime(
        current_snapshot_time,
        utc=True,
    )

    snapshot_times = pd.to_datetime(
        df["snapshot_time"],
        format="mixed",
        utc=True,
    )

    # Keep only snapshots from the past.
    result = df[
        (df["underlying"] == underlying)
        & (snapshot_times < current_time)
    ].copy()

    if result.empty:
        return result

    # Calculate moneyness for each historical option.
    result["moneyness"] = result.apply(
        lambda row: calculate_moneyness(
            strike=row["strike"],
            underlying_price=row["underlying_price"],
        ),
        axis=1,
    )

    min_moneyness = (
        target_moneyness
        - moneyness_tolerance
    )

    max_moneyness = (
        target_moneyness
        + moneyness_tolerance
    )

    min_dte = max(
        0,
        target_dte - dte_tolerance,
    )

    max_dte = (
        target_dte
        + dte_tolerance
    )

    # Filter by moneyness and DTE.
    result = result[
        (
            result["moneyness"]
            >= min_moneyness
        )
        & (
            result["moneyness"]
            <= max_moneyness
        )
        & (
            result["dte"]
            >= min_dte
        )
        & (
            result["dte"]
            <= max_dte
        )
    ].copy()

    return result.reset_index(
        drop=True
    )