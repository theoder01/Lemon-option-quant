# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

"""Adapt existing Futu retrieval to one in-memory daily stock-metric run."""

from datetime import datetime

import pandas as pd

from live_short_put_scanner.calculations import (
    calculate_distance_from_high,
)
from live_short_put_scanner.market_data import (
    get_snapshot,
)
from option_quant.collector import (
    _get_option_snapshots,
)
from option_quant.filters import (
    filter_otm_calls,
    filter_otm_puts,
)
from option_quant.time_utils import (
    get_trading_date,
)

from .daily_stock_metrics import StockInputs
from .skew import REQUIRED_COLUMNS


TARGET_DTE = 30


class FutuStockMetricsSource:
    def __init__(
        self,
        scanner_client,
        option_client,
    ):
        self.scanner_client = scanner_client
        self.option_client = option_client

    def get_stock_inputs(
        self,
        ticker: str,
        snapshot_time: datetime,
    ) -> StockInputs:

        snapshot = get_snapshot(
            self.scanner_client,
            ticker,
            end_date=get_trading_date(
                snapshot_time
            ),
        )

        # Rank and IV/HV retain scanner sources.
        # Spot uses the current live quote.
        # Drawdown uses live spot and the scanner's
        # unchanged historical 52-week high.
        spot = self.option_client.get_last_price(
            ticker
        )

        if (
            (
                snapshot.iv is not None
                and snapshot.iv < 0
            )
            or (
                snapshot.hv is not None
                and snapshot.hv < 0
            )
        ):
            raise ValueError(
                "negative IV/HV observation"
            )

        return StockInputs(
            spot=spot,
            iv_rank=snapshot.iv_rank,
            iv_hv=snapshot.vrp,
            drawdown_52w=(
                calculate_distance_from_high(
                    spot,
                    snapshot.high_52w_close,
                )
            ),
        )

    def _get_30d_expiration_window(
        self,
        ticker: str,
        snapshot_time: datetime,
    ) -> tuple[pd.Timestamp, pd.Timestamp]:
        """
        Find the expiration date(s) needed for 30D
        constant-maturity skew.

        If an exact 30-DTE expiration exists, return it
        as both start and end.

        Otherwise return the nearest expiration below
        30 DTE and the nearest expiration above 30 DTE.

        No extrapolation is allowed.
        """

        expiration_data = (
            self.option_client
            .get_option_expiration_dates(
                ticker
            )
        )

        if expiration_data.empty:
            raise ValueError(
                "no option expiration dates"
            )

        trading_date = pd.Timestamp(
            get_trading_date(
                snapshot_time
            )
        ).normalize()

        expirations = (
            pd.to_datetime(
                expiration_data[
                    "strike_time"
                ]
            )
            .dropna()
            .drop_duplicates()
            .sort_values()
        )

        candidates = []

        for expiry in expirations:

            expiry = pd.Timestamp(
                expiry
            ).normalize()

            dte = (
                expiry - trading_date
            ).days

            if dte < 0:
                continue

            candidates.append(
                (
                    expiry,
                    dte,
                )
            )

        if not candidates:
            raise ValueError(
                "no future option expirations"
            )

        # Exact 30 DTE takes priority.
        exact = [
            expiry
            for expiry, dte in candidates
            if dte == TARGET_DTE
        ]

        if exact:
            return (
                exact[0],
                exact[0],
            )

        lower = [
            (
                expiry,
                dte,
            )
            for expiry, dte in candidates
            if dte < TARGET_DTE
        ]

        upper = [
            (
                expiry,
                dte,
            )
            for expiry, dte in candidates
            if dte > TARGET_DTE
        ]

        if not lower or not upper:
            raise ValueError(
                "cannot bracket 30D expiration"
            )

        lower_expiry, _ = max(
            lower,
            key=lambda item: item[1],
        )

        upper_expiry, _ = min(
            upper,
            key=lambda item: item[1],
        )

        return (
            lower_expiry,
            upper_expiry,
        )

    def get_option_snapshot(
        self,
        ticker: str,
        snapshot_time: datetime,
    ) -> pd.DataFrame:
        """
        Retrieve only the live option data required for
        30D constant-maturity 25-delta skew.

        Unlike the historical collector, this does NOT
        load the full one-year option chain.
        """

        # -------------------------------------------------
        # 1. Find only the expiration window needed
        #    around 30 DTE.
        # -------------------------------------------------

        lower_expiry, upper_expiry = (
            self._get_30d_expiration_window(
                ticker,
                snapshot_time,
            )
        )

        print(
            f"[{ticker}] 30D expiries: "
            f"{lower_expiry.date()} -> "
            f"{upper_expiry.date()}",
            flush=True,
        )

        # -------------------------------------------------
        # 2. Fetch only this narrow option-chain window.
        # -------------------------------------------------

        chain = self.option_client.get_option_chain(
            code=ticker,
            start=lower_expiry.strftime(
                "%Y-%m-%d"
            ),
            end=upper_expiry.strftime(
                "%Y-%m-%d"
            ),
        )

        if chain.empty:
            return pd.DataFrame(
                columns=REQUIRED_COLUMNS
            )

        print(
            f"[{ticker}] narrow chain: "
            f"{len(chain)} contracts",
            flush=True,
        )

        # -------------------------------------------------
        # 3. Restrict snapshots to relevant OTM contracts.
        #
        # PUT:
        #   70% <= strike / spot < 100%
        #
        # CALL:
        #   100% < strike / spot <= 130%
        # -------------------------------------------------

        spot = self.option_client.get_last_price(
            ticker
        )

        puts = filter_otm_puts(
            option_chain=chain,
            underlying_price=spot,
        )

        calls = filter_otm_calls(
            option_chain=chain,
            underlying_price=spot,
        )

        filtered_chain = pd.concat(
            [
                puts,
                calls,
            ],
            ignore_index=True,
        )

        if filtered_chain.empty:
            return pd.DataFrame(
                columns=REQUIRED_COLUMNS
            )

        print(
            f"[{ticker}] skew candidates: "
            f"{len(filtered_chain)} contracts "
            f"(PUT={len(puts)}, "
            f"CALL={len(calls)})",
            flush=True,
        )

        # -------------------------------------------------
        # 4. Retrieve snapshots only for these contracts.
        # -------------------------------------------------

        codes = filtered_chain[
            "code"
        ].tolist()

        snapshots = _get_option_snapshots(
            self.option_client,
            codes,
        )

        if snapshots.empty:
            return pd.DataFrame(
                columns=REQUIRED_COLUMNS
            )

        # -------------------------------------------------
        # 5. Restore option type from chain metadata.
        # -------------------------------------------------

        option_type_by_code = (
            filtered_chain
            .set_index(
                "code"
            )[
                "option_type"
            ]
        )

        option_types = snapshots[
            "code"
        ].map(
            option_type_by_code
        )

        if option_types.isna().any():
            raise ValueError(
                "could not determine live option_type"
            )

        if snapshots[
            "code"
        ].duplicated().any():
            raise ValueError(
                "duplicate live option snapshot codes"
            )

        # -------------------------------------------------
        # 6. Return the normalized in-memory skew dataset.
        # -------------------------------------------------

        return pd.DataFrame(
            {
                "snapshot_time":
                    snapshot_time,

                "underlying":
                    ticker,

                "expiry":
                    snapshots[
                        "strike_time"
                    ],

                "dte":
                    snapshots[
                        "option_expiry_date_distance"
                    ],

                "option_code":
                    snapshots[
                        "code"
                    ],

                "option_type":
                    option_types,

                "delta":
                    snapshots[
                        "option_delta"
                    ],

                "iv":
                    snapshots[
                        "option_implied_volatility"
                    ],
            },
            columns=REQUIRED_COLUMNS,
        )