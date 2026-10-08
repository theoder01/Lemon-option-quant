# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

"""Append-only stock metric history, separate from option snapshot storage."""

from contextlib import closing, contextmanager
from datetime import datetime
from math import isfinite
from pathlib import Path
import sqlite3

import pandas as pd

from option_quant.database import TIMESTAMP_FORMAT
from option_quant.runtime_paths import resource_root
from option_quant.time_utils import UTC, get_trading_date

from .stock_metrics import StockMetrics


TABLE_NAME = "stock_metrics"
COLUMNS = ("snapshot_time", "trading_date", "ticker", "spot", "iv_rank",
           "iv_hv", "drawdown_52w", "put_call_skew")


class StockMetricsDatabase:
    def __init__(self, database_path: str | Path | None = None):
        # Construction has no filesystem side effects, including for the default.
        self.database_path = (Path(database_path) if database_path is not None
                              else resource_root() / "data" / "stock_metrics.db")

    @contextmanager
    def _connect(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        try:
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS stock_metrics (
                        snapshot_time TEXT NOT NULL,
                        trading_date TEXT NOT NULL,
                        ticker TEXT NOT NULL,
                        spot REAL NOT NULL,
                        iv_rank REAL NOT NULL,
                        iv_hv REAL NOT NULL,
                        drawdown_52w REAL NOT NULL,
                        put_call_skew REAL NOT NULL,
                        UNIQUE (ticker, trading_date)
                    )
                """)
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _prepare_row(metrics: StockMetrics) -> tuple:
        if not isinstance(metrics.ticker, str) or not metrics.ticker.strip():
            raise ValueError("ticker must be a nonempty string.")
        timestamp = metrics.snapshot_time
        if not isinstance(timestamp, datetime):
            raise ValueError("snapshot_time must be a timezone-aware datetime.")
        try:
            if timestamp.utcoffset() is None:
                raise ValueError("snapshot_time must be timezone-aware.")
            trading_date = get_trading_date(timestamp).isoformat()
            canonical_time = timestamp.astimezone(UTC).strftime(TIMESTAMP_FORMAT)
        except (TypeError, ValueError) as error:
            raise ValueError("snapshot_time must be a valid timezone-aware datetime.") from error

        numbers = []
        for name in ("spot", "iv_rank", "iv_hv", "drawdown_52w", "put_call_skew"):
            value = getattr(metrics, name)
            try:
                number = float(value)
            except (TypeError, ValueError, OverflowError) as error:
                raise ValueError(f"{name} must be a finite number.") from error
            if isinstance(value, bool) or not isfinite(number):
                raise ValueError(f"{name} must be a finite number.")
            if name == "spot" and number <= 0:
                raise ValueError("spot must be positive.")
            numbers.append(number)
        return (canonical_time, trading_date, metrics.ticker, *numbers)

    def save(self, metrics: StockMetrics) -> tuple[int, int]:
        row = self._prepare_row(metrics)
        with self._connect() as connection:
            cursor = connection.execute("""
                INSERT INTO stock_metrics (
                    snapshot_time, trading_date, ticker, spot, iv_rank,
                    iv_hv, drawdown_52w, put_call_skew
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (ticker, trading_date) DO NOTHING
            """, row)
            saved = cursor.rowcount
        return saved, 1 - saved

    def load_all(self) -> pd.DataFrame:
        with self._connect() as connection:
            return pd.read_sql_query(
                "SELECT * FROM stock_metrics ORDER BY snapshot_time ASC, ticker ASC",
                connection,
            )

    def load_ticker(self, ticker: str) -> pd.DataFrame:
        with self._connect() as connection:
            return pd.read_sql_query(
                "SELECT * FROM stock_metrics WHERE ticker = ? ORDER BY snapshot_time ASC",
                connection, params=(ticker,),
            )

    def load_latest_metrics(self) -> pd.DataFrame:
        """Read the latest NY date without creating or modifying a database."""
        if not self.database_path.is_file():
            return pd.DataFrame(columns=COLUMNS)
        uri = self.database_path.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (TABLE_NAME,),
            ).fetchone()
            if exists is None:
                return pd.DataFrame(columns=COLUMNS)
            return pd.read_sql_query(
                "SELECT * FROM stock_metrics WHERE trading_date = "
                "(SELECT MAX(trading_date) FROM stock_metrics) ORDER BY ticker ASC",
                connection,
            )
