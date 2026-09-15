# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 13, 2026

import sqlite3
from pathlib import Path

import pandas as pd


TABLE_NAME = "option_snapshots"


class OptionDatabase:
    """
    SQLite storage for historical option snapshots.
    """

    def __init__(self, database_path: str):
        self.database_path = Path(database_path)

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _connect(self):
        """
        Create a connection to the SQLite database.
        """
        return sqlite3.connect(self.database_path)

    def save_snapshots(
        self,
        df: pd.DataFrame,
    ) -> tuple[int, int]:
        """
        Save option snapshots while preventing duplicate
        contracts from being stored on the same date.

        A duplicate is defined by:

            underlying + option_code + snapshot date

        Returns
        -------
        tuple[int, int]
            Number of saved rows and skipped duplicate rows.
        """

        if df.empty:
            return 0, 0

        df = df.copy()

        # Make sure snapshot_time is handled consistently.
        df["snapshot_time"] = pd.to_datetime(
            df["snapshot_time"]
        )

        snapshot_date = (
            df["snapshot_time"]
            .iloc[0]
            .date()
            .isoformat()
        )

        underlying = df["underlying"].iloc[0]

        with self._connect() as connection:

            # -------------------------------------------------
            # Check whether the table already exists
            # -------------------------------------------------

            table_exists = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = ?
                """,
                (TABLE_NAME,),
            ).fetchone()

            # -------------------------------------------------
            # First write: database/table is still empty
            # -------------------------------------------------

            if table_exists is None:

                df.to_sql(
                    TABLE_NAME,
                    connection,
                    if_exists="append",
                    index=False,
                )

                return len(df), 0

            # -------------------------------------------------
            # Find contracts already stored for this
            # underlying on this snapshot date
            # -------------------------------------------------

            query = f"""
            SELECT option_code
            FROM {TABLE_NAME}
            WHERE underlying = ?
              AND DATE(snapshot_time) = ?
            """

            existing = pd.read_sql_query(
                query,
                connection,
                params=(
                    underlying,
                    snapshot_date,
                ),
            )

            existing_codes = set(
                existing["option_code"]
            )

            # -------------------------------------------------
            # Remove duplicate contracts
            # -------------------------------------------------

            duplicate_mask = df[
                "option_code"
            ].isin(existing_codes)

            duplicate_count = int(
                duplicate_mask.sum()
            )

            new_df = df[
                ~duplicate_mask
            ].copy()

            # -------------------------------------------------
            # Save only new rows
            # -------------------------------------------------

            if not new_df.empty:

                new_df.to_sql(
                    TABLE_NAME,
                    connection,
                    if_exists="append",
                    index=False,
                )

            saved_count = len(new_df)

            return saved_count, duplicate_count

    def load_all(self) -> pd.DataFrame:
        """
        Load all option snapshots from the database.
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
                params=(underlying,),
            )