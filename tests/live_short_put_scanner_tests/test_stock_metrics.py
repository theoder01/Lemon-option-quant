# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

import pytest
import pandas as pd
from datetime import date
from unittest.mock import Mock

from live_short_put_scanner.calculations import (
    calculate_distance_from_high, calculate_high_52w_close, calculate_vrp,
    normalize_official_iv_rank,
)
from live_short_put_scanner.futu_client import FutuDataError
from live_short_put_scanner.market_data import get_snapshot


@pytest.mark.parametrize('value,expected', [(0, 0.0), (100, 100.0), (43.7, 43.7), ('73.25', 73.25)])
def test_official_iv_rank_adapter_preserves_values(value, expected):
    assert normalize_official_iv_rank(value) == expected


@pytest.mark.parametrize('value', [None, float('nan'), float('inf'), 'invalid'])
def test_missing_official_iv_rank_stays_unavailable(value):
    assert normalize_official_iv_rank(value) is None


def synthetic_client(ivs, official_rank):
    client = Mock()
    client.get_overview.return_value = pd.DataFrame([{
        'code': 'US.NVDA', 'iv_rank': official_rank,
    }])
    client.get_history.return_value = pd.DataFrame([
        {'code': 'US.NVDA', 'time': f'2026-10-{index+1:02d}',
         'iv': iv, 'hv': 20, 'underlying_price': 100}
        for index, iv in enumerate(ivs)
    ], columns=['code', 'time', 'iv', 'hv', 'underlying_price'])
    return client


@pytest.mark.parametrize('history,official', [
    ([30, 60, 45], 73.25),  # Normal range: provider rank wins over any local estimate.
    ([30, 60, 30], 0.0),   # Current IV at minimum, supplied official endpoint.
    ([30, 60, 60], 100.0), # Current IV at maximum, supplied official endpoint.
    ([30, 60, 40], 47.0),  # Interior observation, no locally reconstructed formula.
    ([40, 40, 40], 47.0),  # Flat local history does not invalidate an official rank.
    ([40], 47.0),         # Short local history follows the existing provider policy.
])
def test_official_iv_rank_remains_authoritative_across_history_scenarios(history, official):
    result = get_snapshot(synthetic_client(history, official), 'US.NVDA', date(2026, 10, 8))
    assert result.iv_rank == official


def test_flat_history_with_missing_official_rank_has_no_fabricated_fallback():
    result = get_snapshot(synthetic_client([40, 40], None), 'US.NVDA', date(2026, 10, 8))
    assert result.iv_rank is None


def test_empty_history_preserves_existing_snapshot_error_policy():
    with pytest.raises(FutuDataError, match='no dated historical observations'):
        get_snapshot(synthetic_client([], 47), 'US.NVDA', date(2026, 10, 8))


@pytest.mark.parametrize('iv,hv,expected', [
    (60.0, 52.0, 8.0), (52.0, 52.0, 0.0), (47.0, 52.0, -5.0),
    (74.32, 67.338, 6.982), (55.5, 50.0, 5.5),
])
def test_iv_hv_is_signed_volatility_point_difference(iv, hv, expected):
    assert calculate_vrp(iv, hv) == pytest.approx(expected)


@pytest.mark.parametrize('current,high,expected', [
    (76.0, 76.0, 0.0), (60.8, 76.0, 20.0), (38.0, 76.0, 50.0),
    (110.0, 100.0, -10.0),
])
def test_drawdown_keeps_percentage_convention_and_negative_above_high(current, high, expected):
    assert calculate_distance_from_high(current, high) == pytest.approx(expected)


@pytest.mark.parametrize('high', [None, 0, -76, float('nan'), float('inf')])
def test_drawdown_invalid_or_nonpositive_high_is_unavailable(high):
    assert calculate_distance_from_high(38, high) is None


def test_high_source_is_maximum_valid_underlying_price():
    high = calculate_high_52w_close([40, 60, 76, 55, None, float('nan'), -1, 0])
    assert high == 76
    assert calculate_distance_from_high(38, high) == 50
