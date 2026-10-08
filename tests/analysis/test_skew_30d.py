# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

from datetime import date, timedelta

import pandas as pd
import pytest

from option_quant.analytics.skew import (
    REQUIRED_COLUMNS,
    SKEW_30D_COLUMNS,
    calculate_25delta_skew,
    calculate_30d_skew,
)


SNAPSHOT = "2026-10-08T15:00:00Z"


def pair(dte, skew, *, underlying="US.NVDA", snapshot_time=SNAPSHOT):
    expiry = (date(2026, 10, 8) + timedelta(days=dte)).isoformat()
    shared = {
        "snapshot_time": snapshot_time,
        "underlying": underlying,
        "expiry": expiry,
        "dte": dte,
    }
    return [
        dict(shared, option_code=f"{underlying}-{expiry}-P",
             option_type="PUT", delta=-0.25, iv=50.0 + skew),
        dict(shared, option_code=f"{underlying}-{expiry}-C",
             option_type="CALL", delta=0.25, iv=50.0),
    ]


def frame(rows):
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


def test_exact_30_dte_has_matching_bounds():
    result = calculate_30d_skew(frame(pair(30, 8)))
    assert list(result.columns) == SKEW_30D_COLUMNS
    assert result.to_dict("records") == [{
        "snapshot_time": SNAPSHOT,
        "underlying": "US.NVDA",
        "target_dte": 30,
        "lower_dte": 30,
        "upper_dte": 30,
        "lower_skew": 8.0,
        "upper_skew": 8.0,
        "put_call_skew_30d": 8.0,
    }]


@pytest.mark.parametrize("lower_dte,upper_dte,lower_skew,upper_skew,expected", [
    (23, 37, 5.0, 11.0, 8.0),
    (20, 40, 6.0, 10.0, 8.0),
    (25, 45, 4.0, 12.0, 6.0),
    (27, 36, 3.0, 12.0, 6.0),
    (20, 40, -6.0, -10.0, -8.0),
    (20, 40, 2.0, 2.0, 2.0),
])
def test_linear_interpolation(lower_dte, upper_dte, lower_skew, upper_skew, expected):
    result = calculate_30d_skew(frame(
        pair(upper_dte, upper_skew) + pair(lower_dte, lower_skew)
    ))
    assert len(result) == 1
    row = result.iloc[0]
    assert row["put_call_skew_30d"] == pytest.approx(expected)
    assert row["lower_dte"] == lower_dte
    assert row["upper_dte"] == upper_dte
    assert row["lower_skew"] == lower_skew
    assert row["upper_skew"] == upper_skew


@pytest.mark.parametrize("dtes", [(20,), (40,), (10, 29), (31, 60)])
def test_one_sided_maturities_do_not_extrapolate(dtes):
    rows = [row for dte in dtes for row in pair(dte, 8)]
    result = calculate_30d_skew(frame(rows))
    assert result.empty
    assert list(result.columns) == SKEW_30D_COLUMNS


def test_empty_input_preserves_output_columns():
    result = calculate_30d_skew(frame([]))
    assert result.empty
    assert list(result.columns) == SKEW_30D_COLUMNS


def test_no_valid_per_expiry_skew_returns_no_result():
    rows = pair(20, 6) + pair(40, 10)
    for row in rows:
        row["delta"] = -0.1 if row["option_type"] == "PUT" else 0.1
    assert calculate_30d_skew(frame(rows)).empty


def test_nearest_lower_and_upper_expiries_are_selected():
    rows = pair(50, 90) + pair(10, 90) + pair(40, 10) + pair(20, 6)
    row = calculate_30d_skew(frame(rows)).iloc[0]
    assert row["lower_dte"] == 20
    assert row["upper_dte"] == 40
    assert row["put_call_skew_30d"] == 8


def test_exact_30_dte_takes_precedence_over_interpolation():
    rows = pair(20, 6) + pair(40, 10) + pair(30, 15)
    row = calculate_30d_skew(frame(rows)).iloc[0]
    assert row["lower_dte"] == row["upper_dte"] == 30
    assert row["lower_skew"] == row["upper_skew"] == 15
    assert row["put_call_skew_30d"] == 15


def test_multiple_underlyings_are_independent_and_sorted():
    rows = pair(20, 6) + pair(40, 10)
    rows += pair(25, 4, underlying="US.AAPL") + pair(45, 12, underlying="US.AAPL")
    result = calculate_30d_skew(frame(rows))
    assert result["underlying"].tolist() == ["US.AAPL", "US.NVDA"]
    assert result["put_call_skew_30d"].tolist() == [6.0, 8.0]


def test_multiple_snapshot_times_are_independent_and_sorted():
    later = "2026-10-08T16:00:00Z"
    rows = pair(25, 4, snapshot_time=later) + pair(45, 12, snapshot_time=later)
    rows += pair(20, 6) + pair(40, 10)
    result = calculate_30d_skew(frame(rows))
    assert result["snapshot_time"].tolist() == [SNAPSHOT, later]
    assert result["put_call_skew_30d"].tolist() == [8.0, 6.0]


@pytest.mark.parametrize("group_field,other", [
    ("underlying", "US.AAPL"),
    ("snapshot_time", "2026-10-08T16:00:00Z"),
])
def test_bounds_from_different_groups_are_never_combined(group_field, other):
    rows = pair(20, 6) + pair(40, 10, **{group_field: other})
    assert calculate_30d_skew(frame(rows)).empty


def test_invalid_nearby_and_exact_expiries_are_ignored():
    rows = pair(20, 6) + pair(40, 10)
    invalid = pair(29, 90) + pair(30, 90) + pair(31, 90)
    for row in invalid:
        if row["option_type"] == "PUT":
            row["delta"] = -0.1
    row = calculate_30d_skew(frame(rows + invalid)).iloc[0]
    assert row["lower_dte"] == 20
    assert row["upper_dte"] == 40
    assert row["put_call_skew_30d"] == 8


def test_missing_dte_cannot_supply_an_interpolation_bound():
    rows = pair(20, 6) + pair(40, 10)
    for row in rows[2:]:
        row["dte"] = None
    assert calculate_30d_skew(frame(rows)).empty


def test_delta_tolerance_is_forwarded_to_existing_pairing_logic():
    rows = pair(30, 8)
    rows[0]["delta"] = -0.21
    assert calculate_30d_skew(frame(rows), max_delta_distance=0.03).empty
    assert len(calculate_30d_skew(frame(rows), max_delta_distance=0.05)) == 1


def test_input_and_per_expiry_results_remain_unchanged():
    snapshot = frame(pair(20, 6) + pair(30, 15) + pair(40, 10))
    original = snapshot.copy(deep=True)
    before = calculate_25delta_skew(snapshot)
    calculate_30d_skew(snapshot)
    pd.testing.assert_frame_equal(snapshot, original)
    pd.testing.assert_frame_equal(calculate_25delta_skew(snapshot), before)


def test_missing_required_columns_reuses_existing_validation():
    with pytest.raises(ValueError, match="option_type"):
        calculate_30d_skew(frame(pair(30, 8)).drop(columns="option_type"))


def test_negative_delta_tolerance_reuses_existing_validation():
    with pytest.raises(ValueError, match="non-negative"):
        calculate_30d_skew(frame(pair(30, 8)), max_delta_distance=-0.01)
