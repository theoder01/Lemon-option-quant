# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

import pandas as pd
import pytest

from option_quant.analytics.skew import (
    MAX_DELTA_DISTANCE,
    TARGET_CALL_DELTA,
    TARGET_PUT_DELTA,
    _find_nearest_delta,
    calculate_25delta_skew,
)


INPUT_COLUMNS = [
    "snapshot_time", "underlying", "expiry", "dte", "option_code",
    "option_type", "delta", "iv",
]
OUTPUT_COLUMNS = [
    "snapshot_time", "underlying", "expiry", "dte", "put_option_code",
    "put_delta", "put_iv", "call_option_code", "call_delta", "call_iv", "skew",
]
SNAPSHOT = "2026-10-08T15:00:00Z"
EXPIRY = "2026-11-20"


def contract(code, option_type, delta, iv, *, snapshot_time=SNAPSHOT,
             underlying="US.NVDA", expiry=EXPIRY, dte=43):
    return {
        "snapshot_time": snapshot_time, "underlying": underlying,
        "expiry": expiry, "dte": dte, "option_code": code,
        "option_type": option_type, "delta": delta, "iv": iv,
    }


def frame(rows):
    return pd.DataFrame(rows, columns=INPUT_COLUMNS)


def pair(*, prefix="A", put_iv=60.0, call_iv=52.0, **group):
    return [contract(prefix + "P", "PUT", -0.25, put_iv, **group),
            contract(prefix + "C", "CALL", 0.25, call_iv, **group)]


def test_basic_correct_pairing_and_vol_points():
    rows = [
        contract("P_FAR", "PUT", -0.29, 90.0),
        contract("C_FAR", "CALL", 0.21, 80.0),
        contract("P_NEAREST", "PUT", -0.24, 60.0),
        contract("C_NEAREST", "CALL", 0.26, 52.0),
        contract("P_OTHER", "PUT", -0.27, 70.0),
        contract("C_OTHER", "CALL", 0.28, 65.0),
    ]
    source = frame(rows)
    assert TARGET_PUT_DELTA == -0.25
    assert TARGET_CALL_DELTA == 0.25
    assert MAX_DELTA_DISTANCE == 0.05
    assert _find_nearest_delta(source[source.option_type == "PUT"], TARGET_PUT_DELTA).option_code == "P_NEAREST"
    assert _find_nearest_delta(source[source.option_type == "CALL"], TARGET_CALL_DELTA).option_code == "C_NEAREST"
    result = calculate_25delta_skew(source)
    assert len(result) == 1
    row = result.iloc[0]
    assert row.put_option_code == "P_NEAREST"
    assert row.call_option_code == "C_NEAREST"
    assert row.put_delta == pytest.approx(-0.24)
    assert row.call_delta == pytest.approx(0.26)
    assert row.put_iv == pytest.approx(60.0)
    assert row.call_iv == pytest.approx(52.0)
    assert row["skew"] == pytest.approx(8.0)  # Vol points, not 0.08.


def test_multiple_expirations_are_independent_and_sorted():
    source = frame(pair(prefix="LATE", expiry="2026-12-18", dte=71,
                        put_iv=70, call_iv=55)
                   + pair(prefix="EARLY", expiry="2026-11-20", put_iv=60, call_iv=52))
    result = calculate_25delta_skew(source)
    assert result.expiry.tolist() == ["2026-11-20", "2026-12-18"]
    assert result.put_option_code.tolist() == ["EARLYP", "LATEP"]
    assert result.call_option_code.tolist() == ["EARLYC", "LATEC"]
    assert result["skew"].tolist() == pytest.approx([8, 15])
    assert result.dte.tolist() == [43, 71]
    assert result.index.tolist() == [0, 1]


def test_put_outside_max_delta_distance_skips_expiry():
    assert calculate_25delta_skew(frame([
        contract("P", "PUT", -0.15, 60), contract("C", "CALL", 0.25, 52),
    ])).empty


def test_call_outside_max_delta_distance_skips_expiry():
    assert calculate_25delta_skew(frame([
        contract("P", "PUT", -0.25, 60), contract("C", "CALL", 0.35, 52),
    ])).empty


def test_missing_put_skips_expiry():
    assert calculate_25delta_skew(frame([contract("C", "CALL", 0.25, 52)])).empty


def test_missing_call_skips_expiry():
    assert calculate_25delta_skew(frame([contract("P", "PUT", -0.25, 60)])).empty


def test_wrong_option_types_never_pair():
    distractors = [
        contract("OTHER_P", "OTHER", -0.25, 99),
        contract("OTHER_C", "OTHER", 0.25, 1),
        contract("CALL_NEGATIVE", "CALL", -0.25, 99),
        contract("PUT_POSITIVE", "PUT", 0.25, 1),
        contract("NULL_TYPE", None, -0.25, 99),
    ]
    source = frame(distractors + [contract("P", "PUT", -0.24, 60),
                                  contract("C", "CALL", 0.26, 52)])
    row = calculate_25delta_skew(source).iloc[0]
    assert (row.put_option_code, row.call_option_code) == ("P", "C")
    assert row["skew"] == pytest.approx(8)
    assert calculate_25delta_skew(frame(distractors)).empty


@pytest.mark.parametrize("invalid_side", ["PUT", "CALL"])
def test_missing_delta_or_iv_ignored_with_fallback_or_skipped(invalid_side):
    target = -0.25 if invalid_side == "PUT" else 0.25
    invalid = [contract("NO_DELTA", invalid_side, None, 60),
               contract("NO_IV", invalid_side, target, None)]
    valid = pair()
    row = calculate_25delta_skew(frame(invalid + valid)).iloc[0]
    assert (row.put_option_code, row.call_option_code) == ("AP", "AC")
    assert row["skew"] == pytest.approx(8)
    opposite = [r for r in valid if r["option_type"] != invalid_side]
    assert calculate_25delta_skew(frame(invalid + opposite)).empty


@pytest.mark.parametrize("side, boundary, outside", [
    ("PUT", -0.20, -0.199999), ("PUT", -0.30, -0.300001),
    ("CALL", 0.20, 0.199999), ("CALL", 0.30, 0.300001),
])
def test_exact_delta_boundary_is_inclusive(side, boundary, outside):
    rows = pair()
    index = 0 if side == "PUT" else 1
    rows[index]["delta"] = boundary
    result = calculate_25delta_skew(frame(rows))
    assert len(result) == 1
    assert result.iloc[0]["put_delta" if side == "PUT" else "call_delta"] == boundary
    assert result.iloc[0]["skew"] == pytest.approx(8)
    rows[index]["delta"] = outside
    assert calculate_25delta_skew(frame(rows)).empty


def test_exact_target_delta_selected_over_nearby_candidates():
    source = frame([contract("NEAR_P", "PUT", -0.24, 80),
                    contract("NEAR_C", "CALL", 0.26, 70)] + pair())
    row = calculate_25delta_skew(source).iloc[0]
    assert (row.put_option_code, row.call_option_code) == ("AP", "AC")
    assert (row.put_delta, row.call_delta) == (-0.25, 0.25)
    assert row["skew"] == pytest.approx(8)


def test_empty_input_keeps_expected_output_columns():
    result = calculate_25delta_skew(frame([]))
    assert result.empty
    assert result.columns.tolist() == OUTPUT_COLUMNS


def test_missing_required_column_raises_value_error():
    with pytest.raises(ValueError, match="option_type"):
        calculate_25delta_skew(frame(pair()).drop(columns="option_type"))


def test_negative_max_delta_distance_raises_value_error():
    with pytest.raises(ValueError, match="non-negative"):
        calculate_25delta_skew(frame(pair()), max_delta_distance=-0.01)


def test_multiple_snapshots_never_pair_across_times():
    first = "2026-10-08T15:00:00Z"
    second = "2026-10-08T16:00:00Z"
    source = frame(pair(prefix="SECOND", snapshot_time=second, put_iv=70, call_iv=56)
                   + pair(prefix="FIRST", snapshot_time=first)
                   + [contract("ORPHAN_P", "PUT", -0.25, 100, snapshot_time="2026-10-08T17:00:00Z"),
                      contract("ORPHAN_C", "CALL", 0.25, 1, snapshot_time="2026-10-08T18:00:00Z")])
    result = calculate_25delta_skew(source)
    assert result.snapshot_time.tolist() == [first, second]
    assert result.put_option_code.tolist() == ["FIRSTP", "SECONDP"]
    assert result.call_option_code.tolist() == ["FIRSTC", "SECONDC"]
    assert result["skew"].tolist() == pytest.approx([8, 14])


def test_multiple_underlyings_never_pair_across_symbols():
    source = frame(pair(prefix="NVDA", underlying="US.NVDA", put_iv=65, call_iv=50)
                   + pair(prefix="AAPL", underlying="US.AAPL")
                   + [contract("ORPHAN_P", "PUT", -0.25, 100, underlying="US.IREN"),
                      contract("ORPHAN_C", "CALL", 0.25, 1, underlying="US.GOOG")])
    result = calculate_25delta_skew(source)
    assert result.underlying.tolist() == ["US.AAPL", "US.NVDA"]
    assert result.put_option_code.tolist() == ["AAPLP", "NVDAP"]
    assert result.call_option_code.tolist() == ["AAPLC", "NVDAC"]
    assert result["skew"].tolist() == pytest.approx([8, 15])
