# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from option_quant.analytics import (
    daily_stock_metrics_market_data as market_data,
)
from option_quant.analytics.daily_stock_metrics import (
    DailyStockMetricsRunner,
    StockInputs,
)
from option_quant.analytics.skew import REQUIRED_COLUMNS
from option_quant.analytics.stock_metrics import StockMetrics


STAMP = datetime(
    2026,
    10,
    8,
    15,
    tzinfo=timezone.utc,
)


class ScannerStub:
    def get_overview(self, symbol):
        return pd.DataFrame(
            [
                {
                    "code": symbol,
                    "iv_rank": 55.5,
                }
            ]
        )

    def get_history(
        self,
        symbol,
        begin,
        end,
    ):
        self.window = (
            begin,
            end,
        )

        return pd.DataFrame(
            [
                {
                    "code": symbol,
                    "time": "2026-10-07",
                    "iv": 30,
                    "hv": 35,
                    "underlying_price": 76,
                },
                {
                    "code": symbol,
                    "time": "2026-10-08",
                    "iv": 30,
                    "hv": 35,
                    "underlying_price": 42,
                },
            ]
        )


class OptionsStub:
    def __init__(
        self,
        expirations=None,
        chains=None,
    ):
        self.batches = []
        self.chain_calls = []
        self.price_ticker = None

        self.expirations = (
            expirations
            if expirations is not None
            else [
                "2026-11-07",
            ]
        )

        self.chains = (
            chains
            if chains is not None
            else {}
        )

    def get_last_price(
        self,
        ticker,
    ):
        self.price_ticker = ticker
        return 38.0

    def get_option_expiration_dates(
        self,
        ticker,
    ):
        return pd.DataFrame(
            {
                "strike_time":
                    self.expirations,
            }
        )

    def get_option_chain(
        self,
        code,
        start=None,
        end=None,
    ):
        self.chain_calls.append(
            (
                code,
                start,
                end,
            )
        )

        key = (
            start,
            end,
        )

        if key in self.chains:
            return self.chains[
                key
            ].copy()

        return pd.DataFrame(
            [
                {
                    "code": "PUTP",
                    "option_type": "PUT",
                    "strike_price": 35.0,
                },
                {
                    "code": "CALLC",
                    "option_type": "CALL",
                    "strike_price": 42.0,
                },
            ]
        )

    def get_market_snapshot(
        self,
        codes,
    ):
        codes = list(
            codes
        )

        self.batches.append(
            codes
        )

        rows = []

        for code in codes:

            is_put = code.endswith(
                "P"
            )

            rows.append(
                {
                    "code":
                        code,

                    "strike_time":
                        "2026-11-07",

                    "option_expiry_date_distance":
                        30,

                    "option_delta":
                        (
                            -0.25
                            if is_put
                            else 0.25
                        ),

                    "option_implied_volatility":
                        (
                            60.0
                            if is_put
                            else 52.0
                        ),
                }
            )

        return pd.DataFrame(
            rows
        )


def test_stock_inputs_reuse_scanner_rank_vrp_and_high_with_live_spot():
    scanner = ScannerStub()
    options = OptionsStub()

    source = (
        market_data
        .FutuStockMetricsSource(
            scanner,
            options,
        )
    )

    result = source.get_stock_inputs(
        "US.NVDA",
        STAMP,
    )

    assert result == StockInputs(
        38,
        55.5,
        -5,
        50,
    )

    assert scanner.window == (
        "2025-10-08",
        "2026-10-08",
    )

    assert (
        options.price_ticker
        == "US.NVDA"
    )


def test_exact_30d_expiry_is_used_alone():
    options = OptionsStub(
        expirations=[
            "2026-10-30",
            "2026-11-07",
            "2026-11-13",
        ]
    )

    source = (
        market_data
        .FutuStockMetricsSource(
            None,
            options,
        )
    )

    lower, upper = (
        source
        ._get_30d_expiration_window(
            "US.NVDA",
            STAMP,
        )
    )

    assert lower.date().isoformat() == (
        "2026-11-07"
    )

    assert upper.date().isoformat() == (
        "2026-11-07"
    )


def test_nearest_lower_and_upper_expiries_bracket_30d():
    options = OptionsStub(
        expirations=[
            "2026-10-16",
            "2026-10-30",
            "2026-11-13",
            "2026-12-18",
        ]
    )

    source = (
        market_data
        .FutuStockMetricsSource(
            None,
            options,
        )
    )

    lower, upper = (
        source
        ._get_30d_expiration_window(
            "US.NVDA",
            STAMP,
        )
    )

    assert lower.date().isoformat() == (
        "2026-10-30"
    )

    assert upper.date().isoformat() == (
        "2026-11-13"
    )


@pytest.mark.parametrize(
    "expirations",
    [
        [
            "2026-10-16",
            "2026-10-30",
        ],
        [
            "2026-11-13",
            "2026-12-18",
        ],
    ],
)
def test_30d_expiry_window_does_not_extrapolate(
    expirations,
):
    options = OptionsStub(
        expirations=expirations
    )

    source = (
        market_data
        .FutuStockMetricsSource(
            None,
            options,
        )
    )

    with pytest.raises(
        ValueError,
        match="cannot bracket 30D",
    ):
        source._get_30d_expiration_window(
            "US.NVDA",
            STAMP,
        )


def test_only_narrow_expiration_window_is_requested():
    options = OptionsStub(
        expirations=[
            "2026-10-16",
            "2026-10-30",
            "2026-11-13",
            "2026-12-18",
        ]
    )

    source = (
        market_data
        .FutuStockMetricsSource(
            None,
            options,
        )
    )

    result = source.get_option_snapshot(
        "US.NVDA",
        STAMP,
    )

    assert options.chain_calls == [
        (
            "US.NVDA",
            "2026-10-30",
            "2026-11-13",
        )
    ]

    assert not result.empty


def test_live_chain_types_and_snapshot_fields_are_mapped():
    options = OptionsStub(
        chains={
            (
                "2026-11-07",
                "2026-11-07",
            ):
                pd.DataFrame(
                    [
                        {
                            "code": "CALLC",
                            "option_type": "CALL",
                            "strike_price": 42.0,
                        },
                        {
                            "code": "PUTP",
                            "option_type": "PUT",
                            "strike_price": 35.0,
                        },
                    ]
                )
        }
    )

    source = (
        market_data
        .FutuStockMetricsSource(
            ScannerStub(),
            options,
        )
    )

    result = source.get_option_snapshot(
        "US.NVDA",
        STAMP,
    )

    assert options.chain_calls == [
        (
            "US.NVDA",
            "2026-11-07",
            "2026-11-07",
        )
    ]

    assert options.batches == [
        [
            "PUTP",
            "CALLC",
        ]
    ]

    assert list(
        result.columns
    ) == REQUIRED_COLUMNS

    assert result.option_type.tolist() == [
        "PUT",
        "CALL",
    ]

    assert result.delta.tolist() == [
        -0.25,
        0.25,
    ]

    assert result.iv.tolist() == [
        60.0,
        52.0,
    ]

    assert result.dte.tolist() == [
        30,
        30,
    ]

    assert result.snapshot_time.eq(
        STAMP
    ).all()

    assert result.underlying.eq(
        "US.NVDA"
    ).all()


def test_put_and_call_moneyness_filters_are_applied():
    chain = pd.DataFrame(
        [
            # Below 70% of 38 -> excluded PUT
            {
                "code": "LOWP",
                "option_type": "PUT",
                "strike_price": 25.0,
            },

            # Valid PUT
            {
                "code": "GOODP",
                "option_type": "PUT",
                "strike_price": 35.0,
            },

            # ATM -> excluded
            {
                "code": "ATMP",
                "option_type": "PUT",
                "strike_price": 38.0,
            },

            # Valid CALL
            {
                "code": "GOODC",
                "option_type": "CALL",
                "strike_price": 42.0,
            },

            # Above 130% of 38 -> excluded CALL
            {
                "code": "HIGHC",
                "option_type": "CALL",
                "strike_price": 50.0,
            },
        ]
    )

    options = OptionsStub(
        chains={
            (
                "2026-11-07",
                "2026-11-07",
            ):
                chain
        }
    )

    result = (
        market_data
        .FutuStockMetricsSource(
            None,
            options,
        )
        .get_option_snapshot(
            "US.NVDA",
            STAMP,
        )
    )

    assert options.batches == [
        [
            "GOODP",
            "GOODC",
        ]
    ]

    assert result.option_code.tolist() == [
        "GOODP",
        "GOODC",
    ]


def test_existing_snapshot_batching_is_reused():
    codes = [
        f"OPTION{i}P"
        for i in range(201)
    ]

    chain = pd.DataFrame(
        {
            "code":
                codes,

            "option_type":
                ["PUT"] * len(
                    codes
                ),

            "strike_price":
                [35.0] * len(
                    codes
                ),
        }
    )

    options = OptionsStub(
        chains={
            (
                "2026-11-07",
                "2026-11-07",
            ):
                chain
        }
    )

    result = (
        market_data
        .FutuStockMetricsSource(
            None,
            options,
        )
        .get_option_snapshot(
            "US.NVDA",
            STAMP,
        )
    )

    assert [
        len(batch)
        for batch in options.batches
    ] == [
        200,
        1,
    ]

    assert len(
        result
    ) == 201

    assert result.snapshot_time.eq(
        STAMP
    ).all()


def test_empty_chain_returns_empty_skew_schema():
    options = OptionsStub(
        chains={
            (
                "2026-11-07",
                "2026-11-07",
            ):
                pd.DataFrame()
        }
    )

    result = (
        market_data
        .FutuStockMetricsSource(
            None,
            options,
        )
        .get_option_snapshot(
            "US.NVDA",
            STAMP,
        )
    )

    assert result.empty

    assert list(
        result.columns
    ) == REQUIRED_COLUMNS


def test_empty_snapshots_return_empty_skew_schema():
    options = OptionsStub()

    options.get_market_snapshot = (
        lambda _:
            pd.DataFrame()
    )

    result = (
        market_data
        .FutuStockMetricsSource(
            None,
            options,
        )
        .get_option_snapshot(
            "US.NVDA",
            STAMP,
        )
    )

    assert result.empty

    assert list(
        result.columns
    ) == REQUIRED_COLUMNS


def test_unknown_snapshot_code_is_rejected():
    options = OptionsStub()

    def foreign_snapshot(_):
        return pd.DataFrame(
            [
                {
                    "code":
                        "FOREIGNP",

                    "strike_time":
                        "2026-11-07",

                    "option_expiry_date_distance":
                        30,

                    "option_delta":
                        -0.25,

                    "option_implied_volatility":
                        60.0,
                }
            ]
        )

    options.get_market_snapshot = (
        foreign_snapshot
    )

    with pytest.raises(
        ValueError,
        match="option_type",
    ):
        (
            market_data
            .FutuStockMetricsSource(
                None,
                options,
            )
            .get_option_snapshot(
                "US.NVDA",
                STAMP,
            )
        )


def test_duplicate_snapshot_codes_are_rejected():
    options = OptionsStub()

    def duplicate_snapshot(_):
        return pd.DataFrame(
            [
                {
                    "code":
                        "PUTP",

                    "strike_time":
                        "2026-11-07",

                    "option_expiry_date_distance":
                        30,

                    "option_delta":
                        -0.25,

                    "option_implied_volatility":
                        60.0,
                },
                {
                    "code":
                        "PUTP",

                    "strike_time":
                        "2026-11-07",

                    "option_expiry_date_distance":
                        30,

                    "option_delta":
                        -0.24,

                    "option_implied_volatility":
                        61.0,
                },
            ]
        )

    options.get_market_snapshot = (
        duplicate_snapshot
    )

    with pytest.raises(
        ValueError,
        match="duplicate live option snapshot codes",
    ):
        (
            market_data
            .FutuStockMetricsSource(
                None,
                options,
            )
            .get_option_snapshot(
                "US.NVDA",
                STAMP,
            )
        )


def test_negative_volatility_observation_is_rejected(
    monkeypatch,
):
    monkeypatch.setattr(
        market_data,
        "get_snapshot",
        lambda *args, **kwargs:
            SimpleNamespace(
                iv=-1,
                hv=35,
            ),
    )

    with pytest.raises(
        ValueError,
        match="negative IV/HV",
    ):
        (
            market_data
            .FutuStockMetricsSource(
                None,
                OptionsStub(),
            )
            .get_stock_inputs(
                "US.NVDA",
                STAMP,
            )
        )


def test_adapter_and_runner_work_together_without_database_or_api():
    source = (
        market_data
        .FutuStockMetricsSource(
            ScannerStub(),
            OptionsStub(),
        )
    )

    metrics = (
        DailyStockMetricsRunner(
            source,
            None,
        )
        .calculate(
            "US.NVDA",
            STAMP,
        )
    )

    assert metrics == StockMetrics(
        "US.NVDA",
        STAMP,
        38,
        55.5,
        -5,
        50,
        8,
    )