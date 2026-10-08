# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

"""Daily stock-metric orchestration with injectable, live-only data sources."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import pandas as pd

from live_short_put_scanner import config
from live_short_put_scanner.calculations import finite_number
from option_quant.time_utils import UTC, now_utc

from .skew import calculate_30d_skew
from .stock_metrics import StockMetrics
from .stock_metrics_database import StockMetricsDatabase


@dataclass(frozen=True)
class StockInputs:
    spot: float | None
    iv_rank: float | None
    iv_hv: float | None
    drawdown_52w: float | None


class StockMetricsSource(Protocol):
    def get_stock_inputs(
        self,
        ticker: str,
        snapshot_time: datetime,
    ) -> StockInputs:
        ...

    def get_option_snapshot(
        self,
        ticker: str,
        snapshot_time: datetime,
    ) -> pd.DataFrame:
        ...


@dataclass(frozen=True)
class TickerResult:
    ticker: str
    metrics: StockMetrics | None = None
    saved_rows: int = 0
    duplicate_rows: int = 0
    reason: str | None = None


@dataclass(frozen=True)
class DailyRunResult:
    snapshot_time: datetime
    ticker_results: list[TickerResult]

    @property
    def total_tickers(self) -> int:
        return len(
            self.ticker_results
        )

    @property
    def successful_tickers(self) -> int:
        return sum(
            row.reason is None
            for row in self.ticker_results
        )

    @property
    def saved_rows(self) -> int:
        return sum(
            row.saved_rows
            for row in self.ticker_results
        )

    @property
    def duplicate_rows(self) -> int:
        return sum(
            row.duplicate_rows
            for row in self.ticker_results
        )

    @property
    def skipped_tickers(self) -> list[TickerResult]:
        return [
            row
            for row in self.ticker_results
            if row.reason is not None
        ]


def runner_time(
    value: datetime | None = None,
) -> datetime:
    timestamp = (
        value
        if value is not None
        else now_utc()
    )

    if (
        not isinstance(
            timestamp,
            datetime,
        )
        or timestamp.utcoffset() is None
    ):
        raise ValueError(
            "snapshot_time must be "
            "a timezone-aware datetime"
        )

    return timestamp.astimezone(
        UTC
    )


def required_number(
    name: str,
    value: object,
) -> float:
    number = finite_number(
        value
    )

    if number is None:
        raise ValueError(
            f"missing or invalid {name}"
        )

    if (
        name == "spot"
        and number <= 0
    ):
        raise ValueError(
            "spot must be positive"
        )

    if (
        name == "iv_rank"
        and not 0 <= number <= 100
    ):
        raise ValueError(
            "iv_rank outside 0–100"
        )

    return number


class DailyStockMetricsRunner:
    def __init__(
        self,
        source: StockMetricsSource,
        database: StockMetricsDatabase,
    ):
        self.source = source
        self.database = database

    def calculate(
        self,
        ticker: str,
        snapshot_time: datetime,
    ) -> StockMetrics:

        print(
            f"[{ticker}] calculate start",
            flush=True,
        )

        timestamp = runner_time(
            snapshot_time
        )

        # -------------------------------------------------
        # 1. Stock-level inputs
        # -------------------------------------------------

        print(
            f"[{ticker}] stock inputs start",
            flush=True,
        )

        inputs = self.source.get_stock_inputs(
            ticker,
            timestamp,
        )

        print(
            f"[{ticker}] stock inputs done",
            flush=True,
        )

        values = {
            name: required_number(
                name,
                getattr(
                    inputs,
                    name,
                ),
            )
            for name in (
                "spot",
                "iv_rank",
                "iv_hv",
                "drawdown_52w",
            )
        }

        print(
            f"[{ticker}] "
            f"spot={values['spot']:.2f}, "
            f"iv_rank={values['iv_rank']:.2f}, "
            f"iv_hv={values['iv_hv']:.2f}, "
            f"drawdown={values['drawdown_52w']:.2f}",
            flush=True,
        )

        # -------------------------------------------------
        # 2. Live option snapshot
        # -------------------------------------------------

        print(
            f"[{ticker}] option snapshot start",
            flush=True,
        )

        options = self.source.get_option_snapshot(
            ticker,
            timestamp,
        )

        print(
            f"[{ticker}] option snapshot done "
            f"({len(options)} rows)",
            flush=True,
        )

        if options.empty:
            raise ValueError(
                "no valid 30D skew"
            )

        # -------------------------------------------------
        # 3. Snapshot consistency
        # -------------------------------------------------

        times = pd.to_datetime(
            options["snapshot_time"],
            utc=True,
            errors="coerce",
        )

        if not (
            options["underlying"]
            .eq(
                ticker
            )
            .all()
            and times.eq(
                timestamp
            ).all()
        ):
            raise ValueError(
                "option rows do not belong "
                "to the current ticker/snapshot"
            )

        # -------------------------------------------------
        # 4. 30D constant-maturity skew
        # -------------------------------------------------

        print(
            f"[{ticker}] 30D skew start",
            flush=True,
        )

        skew = calculate_30d_skew(
            options
        )

        print(
            f"[{ticker}] 30D skew done "
            f"({len(skew)} rows)",
            flush=True,
        )

        if len(skew) != 1:
            raise ValueError(
                "no valid 30D skew"
            )

        skew_value = required_number(
            "30D skew",
            skew.iloc[0][
                "put_call_skew_30d"
            ],
        )

        print(
            f"[{ticker}] "
            f"30D skew={skew_value:.4f}",
            flush=True,
        )

        # -------------------------------------------------
        # 5. Build StockMetrics
        # -------------------------------------------------

        metrics = StockMetrics(
            ticker=ticker,
            snapshot_time=timestamp,
            **values,
            put_call_skew=(
                skew_value
            ),
        )

        print(
            f"[{ticker}] calculate done",
            flush=True,
        )

        return metrics

    def run(
        self,
        snapshot_time: datetime | None = None,
    ) -> DailyRunResult:

        timestamp = runner_time(
            snapshot_time
        )

        results = []

        for ticker in config.UNDERLYINGS:

            print()
            print(
                "=" * 60,
                flush=True,
            )

            print(
                f"[{ticker}] START",
                flush=True,
            )

            print(
                "=" * 60,
                flush=True,
            )

            try:

                metrics = self.calculate(
                    ticker,
                    timestamp,
                )

                print(
                    f"[{ticker}] "
                    f"database save start",
                    flush=True,
                )

                saved, duplicate = (
                    self.database.save(
                        metrics
                    )
                )

                print(
                    f"[{ticker}] "
                    f"database save done "
                    f"(saved={saved}, "
                    f"duplicate={duplicate})",
                    flush=True,
                )

                results.append(
                    TickerResult(
                        ticker=ticker,
                        metrics=metrics,
                        saved_rows=saved,
                        duplicate_rows=(
                            duplicate
                        ),
                    )
                )

                print(
                    f"[{ticker}] DONE",
                    flush=True,
                )

            except Exception as error:

                reason = (
                    " ".join(
                        str(
                            error
                        ).split()
                    )
                    or type(
                        error
                    ).__name__
                )

                print(
                    f"[{ticker}] "
                    f"SKIP: {reason}",
                    flush=True,
                )

                results.append(
                    TickerResult(
                        ticker=ticker,
                        reason=reason,
                    )
                )

        return DailyRunResult(
            snapshot_time=timestamp,
            ticker_results=results,
        )


def print_results(
    result: DailyRunResult,
) -> None:
    print()
    print(
        "Daily Stock Metrics"
    )
    print(
        "-------------------"
    )

    print(
        f"Snapshot (UTC): "
        f"{result.snapshot_time.isoformat()}"
    )

    for row in result.ticker_results:

        if row.reason is not None:

            status = (
                f"SKIP {row.reason}"
            )

        elif row.duplicate_rows:

            status = (
                "OK duplicate"
            )

        else:

            status = (
                "OK saved"
            )

        print(
            f"{row.ticker:<10} "
            f"{status}"
        )

    print()
    print(
        "Summary"
    )

    for label, value in (
        (
            "Total",
            result.total_tickers,
        ),
        (
            "Successful",
            result.successful_tickers,
        ),
        (
            "Saved",
            result.saved_rows,
        ),
        (
            "Duplicate",
            result.duplicate_rows,
        ),
        (
            "Skipped",
            len(
                result.skipped_tickers
            ),
        ),
    ):
        print(
            f"{label + ':':<12} "
            f"{value}"
        )