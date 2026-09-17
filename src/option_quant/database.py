# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 13, 2026

import sqlite3
from pathlib import Path

import pandas as pd

from option_quant.time_utils import (
    get_trading_date,
    get_trading_day_utc_bounds,
)


TABLE_NAME = "option_snapshots"

# Canonical timestamp format used in SQLite.
#
# Example:
# 2026-09-17T20:00:00.000000Z
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class OptionDatabase:
    """
    SQLite storage for historical option snapshots.
    """

    def __init__(
        self,
        database_path: str,
    ):
        self.database_path = Path(
            database_path
        )

        # Create the data directory if necessary.
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _connect(self):
        """
        Create a connection to the SQLite database.
        """
        return sqlite3.connect(
            self.database_path
        )

    def save_snapshots(
        self,
        df: pd.DataFrame,
    ) -> tuple[int, int]:
        """
        Save option snapshots to SQLite.

        Duplicate definition:

            underlying
            + option_code
            + New York trading date

        Snapshot timestamps are stored in UTC.

        Returns
        -------
        tuple[int, int]

        saved_count
            Number of newly stored rows.

        duplicate_count
            Number of skipped duplicate rows.
        """

        if df.empty:
            return 0, 0

        df = df.copy()

        # -------------------------------------------------
        # 1. Normalize snapshot timestamps to UTC
        # -------------------------------------------------

        df["snapshot_time"] = pd.to_datetime(
            df["snapshot_time"],
            utc=True,
        )

        # All rows from one collection run should have
        # the same snapshot timestamp.
        snapshot_time = (
            df["snapshot_time"]
            .iloc[0]
            .to_pydatetime()
        )

        # -------------------------------------------------
        # 2. Determine the New York trading date
        # -------------------------------------------------

        trading_date = get_trading_date(
            snapshot_time
        )

        # Convert the New York calendar-day boundaries
        # into UTC.
        start_utc, end_utc = (
            get_trading_day_utc_bounds(
                trading_date
            )
        )

        # -------------------------------------------------
        # 3. Convert timestamps to canonical SQLite format
        # -------------------------------------------------

        start_text = start_utc.strftime(
            TIMESTAMP_FORMAT
        )

        end_text = end_utc.strftime(
            TIMESTAMP_FORMAT
        )

        df["snapshot_time"] = (
            df["snapshot_time"]
            .dt.strftime(
                TIMESTAMP_FORMAT
            )
        )

        underlying = df[
            "underlying"
        ].iloc[0]

        # -------------------------------------------------
        # 4. Open database
        # -------------------------------------------------

        with self._connect() as connection:

            # ---------------------------------------------
            # Check whether the table already exists
            # ---------------------------------------------

            table_exists = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = ?
                """,
                (TABLE_NAME,),
            ).fetchone()

            # ---------------------------------------------
            # First write
            # ---------------------------------------------

            if table_exists is None:

                df.to_sql(
                    TABLE_NAME,
                    connection,
                    if_exists="append",
                    index=False,
                )

                return len(df), 0

            # ---------------------------------------------
            # 5. Find contracts already stored during
            #    this New York trading date
            # ---------------------------------------------

            query = f"""
            SELECT option_code
            FROM {TABLE_NAME}
            WHERE underlying = ?
              AND snapshot_time >= ?
              AND snapshot_time < ?
            """

            existing = pd.read_sql_query(
                query,
                connection,
                params=(
                    underlying,
                    start_text,
                    end_text,
                ),
            )

            existing_codes = set(
                existing[
                    "option_code"
                ]
            )

            # ---------------------------------------------
            # 6. Detect duplicate contracts
            # ---------------------------------------------

            duplicate_mask = df[
                "option_code"
            ].isin(
                existing_codes
            )

            duplicate_count = int(
                duplicate_mask.sum()
            )

            new_df = df[
                ~duplicate_mask
            ].copy()

            # ---------------------------------------------
            # 7. Save only new contracts
            # ---------------------------------------------

            if not new_df.empty:

                new_df.to_sql(
                    TABLE_NAME,
                    connection,
                    if_exists="append",
                    index=False,
                )

            saved_count = len(
                new_df
            )

            return (
                saved_count,
                duplicate_count,
            )

    def load_all(
        self,
    ) -> pd.DataFrame:
        """
        Load all option snapshots.
        """

        query = f"""
        SELECT *
        FROM {TABLE_NAME}
        ORDER BY snapshot_time
        """

        with self._connect() as connection:

            return pd.read_sql_query(
                query,
                connection,
            )

    def load_underlying(
        self,
        underlying: str,
    ) -> pd.DataFrame:
        """
        Load all snapshots for one underlying.
        """

        query = f"""
        SELECT *
        FROM {TABLE_NAME}
        WHERE underlying = ?
        ORDER BY snapshot_time
        """

        with self._connect() as connection:

            return pd.read_sql_query(
                query,
                connection,
                params=(
                    underlying,
                ),
            )