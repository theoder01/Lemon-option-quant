# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 19, 2026

import pandas as pd
import pytest

from option_quant.analytics.comparable_options import (
    find_comparable_options,
)


CURRENT_TIME = "2026-09-23T14:45:00Z"


def make_option(
    snapshot_time: str,
    underlying: str = "US.NVDA",
    underlying_price: float = 220.0,
    strike: float = 190.0,
    dte: int = 30,
) -> dict:
    return {
        "snapshot_time": snapshot_time,
        "underlying": underlying,
        "underlying_price": underlying_price,
        "strike": strike,
        "dte": dte,
    }


def find_nvda_comparables(
    df: pd.DataFrame,
    **kwargs,
) -> pd.DataFrame:
    return find_comparable_options(
        df=df,
        underlying="US.NVDA",
        target_moneyness=190.0 / 220.0,
        target_dte=30,
        current_snapshot_time=CURRENT_TIME,
        **kwargs,
    )


def test_excludes_current_and_future_snapshots():
    df = pd.DataFrame([
        make_option("2026-09-21T14:45:00Z"),
        make_option("2026-09-22T14:45:00Z"),
        make_option("2026-09-23T14:45:00Z"),
        make_option("2026-09-24T14:45:00Z"),
    ])

    result = find_nvda_comparables(df)

    assert len(result) == 2

    assert result["snapshot_time"].tolist() == [
        "2026-09-21T14:45:00Z",
        "2026-09-22T14:45:00Z",
    ]


def test_filters_underlying():
    df = pd.DataFrame([
        make_option("2026-09-21T14:45:00Z"),
        make_option(
            "2026-09-21T14:45:00Z",
            underlying="US.GOOG",
        ),
    ])

    result = find_nvda_comparables(df)

    assert len(result) == 1
    assert result.iloc[0]["underlying"] == "US.NVDA"


def test_filters_moneyness():
    df = pd.DataFrame([
        make_option(
            "2026-09-21T14:45:00Z",
            strike=190.0,
        ),
        make_option(
            "2026-09-21T14:45:00Z",
            strike=180.0,
        ),
        make_option(
            "2026-09-21T14:45:00Z",
            strike=200.0,
        ),
    ])

    result = find_nvda_comparables(df)

    assert len(result) == 1
    assert result.iloc[0]["strike"] == 190.0


def test_filters_dte():
    df = pd.DataFrame([
        make_option(
            "2026-09-21T14:45:00Z",
            dte=25,
        ),
        make_option(
            "2026-09-21T14:45:00Z",
            dte=30,
        ),
        make_option(
            "2026-09-21T14:45:00Z",
            dte=35,
        ),
        make_option(
            "2026-09-21T14:45:00Z",
            dte=36,
        ),
    ])

    result = find_nvda_comparables(df)

    assert result["dte"].tolist() == [25, 30, 35]


def test_handles_different_timestamp_formats():
    df = pd.DataFrame([
        make_option("2026-09-21 14:45:00"),
        make_option("2026-09-22T14:45:00Z"),
        make_option("2026-09-23T14:45:00Z"),
    ])

    result = find_nvda_comparables(df)

    assert len(result) == 2


def test_returns_empty_when_no_historical_data():
    df = pd.DataFrame([
        make_option("2026-09-23T14:45:00Z"),
        make_option("2026-09-24T14:45:00Z"),
    ])

    result = find_nvda_comparables(df)

    assert result.empty


def test_missing_required_column():
    df = pd.DataFrame([
        make_option("2026-09-21T14:45:00Z"),
    ]).drop(columns=["snapshot_time"])

    with pytest.raises(
        ValueError,
        match="Missing required columns",
    ):
        find_nvda_comparables(df)


def test_invalid_target_moneyness():
    df = pd.DataFrame([
        make_option("2026-09-21T14:45:00Z"),
    ])

    with pytest.raises(
        ValueError,
        match="Target moneyness",
    ):
        find_comparable_options(
            df=df,
            underlying="US.NVDA",
            target_moneyness=1.2,
            target_dte=30,
            current_snapshot_time=CURRENT_TIME,
        )


def test_invalid_target_dte():
    df = pd.DataFrame([
        make_option("2026-09-21T14:45:00Z"),
    ])

    with pytest.raises(
        ValueError,
        match="Target DTE",
    ):
        find_comparable_options(
            df=df,
            underlying="US.NVDA",
            target_moneyness=0.86,
            target_dte=-1,
            current_snapshot_time=CURRENT_TIME,
        )


def test_invalid_tolerances():
    df = pd.DataFrame([
        make_option("2026-09-21T14:45:00Z"),
    ])

    with pytest.raises(
        ValueError,
        match="Moneyness tolerance",
    ):
        find_nvda_comparables(
            df,
            moneyness_tolerance=-0.01,
        )

    with pytest.raises(
        ValueError,
        match="DTE tolerance",
    ):
        find_nvda_comparables(
            df,
            dte_tolerance=-1,
        )