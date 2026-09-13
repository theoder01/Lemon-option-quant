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

        # Create the data directory if it does not exist.
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _connect(self):
        """Create a connection to the SQLite database."""
        return sqlite3.connect(self.database_path)

    def save_snapshots(self, df: pd.DataFrame):
        """
        Append option snapshots to the database.
        """

        if df.empty:
            return

        with self._connect() as connection:
            df.to_sql(
                TABLE_NAME,
                connection,
                if_exists="append",
                index=False,
            )

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