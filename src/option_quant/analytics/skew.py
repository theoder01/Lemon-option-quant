# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 7, 2026

import pandas as pd


TARGET_PUT_DELTA = -0.25
TARGET_CALL_DELTA = 0.25
MAX_DELTA_DISTANCE = 0.05


REQUIRED_COLUMNS = [
    "snapshot_time",
    "underlying",
    "expiry",
    "dte",
    "option_code",
    "option_type",
    "delta",
    "iv",
]


def _find_nearest_delta(
    df: pd.DataFrame,
    target_delta: float,
    max_distance: float = MAX_DELTA_DISTANCE,
) -> pd.Series | None:
    """
    Find the option row whose delta is closest to the target delta.

    The row is accepted only when the absolute delta distance is
    less than or equal to max_distance.

    Parameters
    ----------
    df : pandas.DataFrame
        Candidate option rows.

    target_delta : float
        Target option delta.

    max_distance : float
        Maximum allowed absolute distance from target delta.

    Returns
    -------
    pandas.Series | None
        The nearest valid row, or None if no row is close enough.
    """

    if df.empty:
        return None

    candidates = df.dropna(
        subset=["delta", "iv"]
    ).copy()

    if candidates.empty:
        return None

    candidates["delta_distance"] = (
        candidates["delta"] - target_delta
    ).abs()

    nearest_index = (
        candidates["delta_distance"]
        .idxmin()
    )

    nearest = candidates.loc[
        nearest_index
    ]

    if nearest["delta_distance"] > max_distance:
        return None

    return nearest


def calculate_25delta_skew(
    snapshot_df: pd.DataFrame,
    max_delta_distance: float = MAX_DELTA_DISTANCE,
) -> pd.DataFrame:
    """
    Calculate 25-delta Put-Call Skew for each expiration date.

    Definition:

        skew = 25Δ PUT IV - 25Δ CALL IV

    PUT target delta:
        -0.25

    CALL target delta:
        +0.25

    For each expiration date, the function selects the OTM PUT
    closest to -0.25 delta and the OTM CALL closest to +0.25 delta.

    A pair is included only when both selected contracts are within
    max_delta_distance of their target delta.

    Parameters
    ----------
    snapshot_df : pandas.DataFrame
        Option snapshot data containing PUT and CALL contracts.

    max_delta_distance : float
        Maximum allowed absolute delta distance from the target.

    Returns
    -------
    pandas.DataFrame
        One row per valid expiration date.
    """

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in snapshot_df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    if snapshot_df.empty:
        return pd.DataFrame(
            columns=[
                "snapshot_time",
                "underlying",
                "expiry",
                "dte",
                "put_option_code",
                "put_delta",
                "put_iv",
                "call_option_code",
                "call_delta",
                "call_iv",
                "skew",
            ]
        )

    if max_delta_distance < 0:
        raise ValueError(
            "max_delta_distance must be non-negative."
        )

    results = []

    grouped = snapshot_df.groupby(
        [
            "snapshot_time",
            "underlying",
            "expiry",
        ],
        dropna=False,
    )

    for (
        snapshot_time,
        underlying,
        expiry,
    ), group in grouped:

        puts = group[
            group["option_type"] == "PUT"
        ]

        calls = group[
            group["option_type"] == "CALL"
        ]

        put_row = _find_nearest_delta(
            df=puts,
            target_delta=TARGET_PUT_DELTA,
            max_distance=max_delta_distance,
        )

        call_row = _find_nearest_delta(
            df=calls,
            target_delta=TARGET_CALL_DELTA,
            max_distance=max_delta_distance,
        )

        if put_row is None or call_row is None:
            continue

        skew = (
            float(put_row["iv"])
            - float(call_row["iv"])
        )

        dte_values = group[
            "dte"
        ].dropna()

        dte = (
            int(dte_values.iloc[0])
            if not dte_values.empty
            else None
        )

        results.append(
            {
                "snapshot_time":
                    snapshot_time,

                "underlying":
                    underlying,

                "expiry":
                    expiry,

                "dte":
                    dte,

                "put_option_code":
                    put_row["option_code"],

                "put_delta":
                    float(put_row["delta"]),

                "put_iv":
                    float(put_row["iv"]),

                "call_option_code":
                    call_row["option_code"],

                "call_delta":
                    float(call_row["delta"]),

                "call_iv":
                    float(call_row["iv"]),

                "skew":
                    skew,
            }
        )

    result = pd.DataFrame(
        results,
        columns=[
            "snapshot_time",
            "underlying",
            "expiry",
            "dte",
            "put_option_code",
            "put_delta",
            "put_iv",
            "call_option_code",
            "call_delta",
            "call_iv",
            "skew",
        ],
    )

    if result.empty:
        return result

    result = result.sort_values(
        [
            "snapshot_time",
            "underlying",
            "expiry",
        ]
    ).reset_index(
        drop=True
    )

    return result


TARGET_DTE = 30

SKEW_30D_COLUMNS = [
    "snapshot_time",
    "underlying",
    "target_dte",
    "lower_dte",
    "upper_dte",
    "lower_skew",
    "upper_skew",
    "put_call_skew_30d",
]


def calculate_30d_skew(
    snapshot_df: pd.DataFrame,
    max_delta_distance: float = MAX_DELTA_DISTANCE,
) -> pd.DataFrame:
    """Calculate 30-day skew in volatility points per ticker/snapshot.

    Reuse valid per-expiry 25-delta pairs. Prefer an exact 30-DTE expiry;
    otherwise linearly interpolate between the nearest lower and upper
    DTEs. Groups without both bounds are omitted: never extrapolate or
    fall back to a single expiry. An empty result retains its columns.
    """
    per_expiry = calculate_25delta_skew(snapshot_df, max_delta_distance)
    results = []

    for (snapshot_time, underlying), group in per_expiry.groupby(
        ["snapshot_time", "underlying"], dropna=False
    ):
        # A valid option pair may still have no maturity to interpolate.
        maturities = group.dropna(subset=["dte", "skew"]).sort_values(
            ["dte", "expiry"]
        )
        exact = maturities[maturities["dte"] == TARGET_DTE]
        if not exact.empty:
            lower = upper = exact.iloc[0]
            skew_30d = float(lower["skew"])
        else:
            below = maturities[maturities["dte"] < TARGET_DTE]
            above = maturities[maturities["dte"] > TARGET_DTE]
            if below.empty or above.empty:
                continue
            lower = below.iloc[-1]
            upper = above.iloc[0]
            weight = (TARGET_DTE - lower["dte"]) / (
                upper["dte"] - lower["dte"]
            )
            skew_30d = float(
                lower["skew"] + weight * (upper["skew"] - lower["skew"])
            )

        results.append({
            "snapshot_time": snapshot_time,
            "underlying": underlying,
            "target_dte": TARGET_DTE,
            "lower_dte": int(lower["dte"]),
            "upper_dte": int(upper["dte"]),
            "lower_skew": float(lower["skew"]),
            "upper_skew": float(upper["skew"]),
            "put_call_skew_30d": skew_30d,
        })

    result = pd.DataFrame(results, columns=SKEW_30D_COLUMNS)
    return result.sort_values(
        ["snapshot_time", "underlying"]
    ).reset_index(drop=True)
