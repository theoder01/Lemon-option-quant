# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 19, 2026

from option_quant.collection_result import CollectionResult
from option_quant.collector import collect_option_snapshot
from option_quant.database import OptionDatabase
from option_quant.validator import OptionDataValidator


class CollectionService:
    """
    Coordinate option snapshot collection,
    validation, and database storage.
    """

    def __init__(
        self,
        client,
        database: OptionDatabase,
        validator: OptionDataValidator,
    ):
        self.client = client
        self.database = database
        self.validator = validator

    def collect(
        self,
        underlying: str,
    ) -> CollectionResult:
        """
        Collect, validate, and save option data
        for one underlying.
        """

        try:

            # -------------------------------------------------
            # 1. Collect option snapshot
            # -------------------------------------------------

            df = collect_option_snapshot(
                client=self.client,
                underlying=underlying,
            )

            if df.empty:
                return CollectionResult(
                    underlying=underlying,
                    success=False,
                    error="No option data collected.",
                )

            collected_rows = len(df)

            # -------------------------------------------------
            # 2. Validate and clean
            # -------------------------------------------------

            clean_df, report = (
                self.validator.validate(df)
            )

            if clean_df.empty:
                return CollectionResult(
                    underlying=underlying,
                    collected_rows=collected_rows,
                    valid_rows=0,
                    removed_rows=report.removed_rows,
                    success=False,
                    error="No valid option data remains.",
                )

            # -------------------------------------------------
            # 3. Save validated data
            # -------------------------------------------------

            saved_rows, duplicate_rows = (
                self.database.save_snapshots(
                    clean_df
                )
            )

            # -------------------------------------------------
            # 4. Return structured result
            # -------------------------------------------------

            return CollectionResult(
                underlying=underlying,
                collected_rows=collected_rows,
                valid_rows=report.valid_rows,
                removed_rows=report.removed_rows,
                saved_rows=saved_rows,
                duplicate_rows=duplicate_rows,
                success=True,
            )

        except Exception as error:

            return CollectionResult(
                underlying=underlying,
                success=False,
                error=str(error),
            )