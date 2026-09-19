# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 19, 2026

from dataclasses import dataclass

import pandas as pd


@dataclass
class ValidationReport:
    """
    Summary of option data validation results.
    """

    input_rows: int
    valid_rows: int
    removed_rows: int

    missing_values: int
    invalid_underlying_price: int
    invalid_strike: int
    invalid_dte: int
    invalid_iv: int
    extreme_iv: int
    invalid_delta: int
    invalid_gamma: int
    invalid_vega: int


class OptionDataValidator:
    """
    Validate and clean option snapshot data.

    Invalid rows are removed before they are stored
    in the historical option database.
    """

    REQUIRED_COLUMNS = [
        "snapshot_time",
        "underlying",
        "underlying_price",
        "option_code",
        "expiry",
        "strike",
        "dte",
        "iv",
        "delta",
        "gamma",
        "vega",
        "theta",
    ]

    MAX_IV = 500.0

    def validate(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, ValidationReport]:
        """
        Validate and clean an option snapshot DataFrame.

        Returns
        -------
        tuple[pandas.DataFrame, ValidationReport]
            Clean DataFrame and validation report.
        """

        self._check_required_columns(df)

        clean_df = df.copy()

        input_rows = len(clean_df)

        # -------------------------------------------------
        # Missing required values
        # -------------------------------------------------

        missing_mask = clean_df[
            self.REQUIRED_COLUMNS
        ].isna().any(axis=1)

        missing_values = int(
            missing_mask.sum()
        )

        # -------------------------------------------------
        # Invalid underlying price
        # -------------------------------------------------

        invalid_underlying_mask = (
            clean_df["underlying_price"] <= 0
        )

        invalid_underlying_price = int(
            invalid_underlying_mask.sum()
        )

        # -------------------------------------------------
        # Invalid strike
        # -------------------------------------------------

        invalid_strike_mask = (
            clean_df["strike"] <= 0
        )

        invalid_strike = int(
            invalid_strike_mask.sum()
        )

        # -------------------------------------------------
        # Invalid DTE
        # -------------------------------------------------

        invalid_dte_mask = (
            clean_df["dte"] < 0
        )

        invalid_dte = int(
            invalid_dte_mask.sum()
        )

        # -------------------------------------------------
        # Invalid IV
        # -------------------------------------------------

        invalid_iv_mask = (
            clean_df["iv"] < 0
        )

        invalid_iv = int(
            invalid_iv_mask.sum()
        )

        extreme_iv_mask = (
            clean_df["iv"] > self.MAX_IV
        )

        extreme_iv = int(
            extreme_iv_mask.sum()
        )

        # -------------------------------------------------
        # Invalid Greeks
        # -------------------------------------------------

        invalid_delta_mask = (
            (clean_df["delta"] < -1)
            | (clean_df["delta"] > 1)
        )

        invalid_delta = int(
            invalid_delta_mask.sum()
        )

        invalid_gamma_mask = (
            clean_df["gamma"] < 0
        )

        invalid_gamma = int(
            invalid_gamma_mask.sum()
        )

        invalid_vega_mask = (
            clean_df["vega"] < 0
        )

        invalid_vega = int(
            invalid_vega_mask.sum()
        )

        # -------------------------------------------------
        # Combine all invalid conditions
        # -------------------------------------------------

        invalid_mask = (
            missing_mask
            | invalid_underlying_mask
            | invalid_strike_mask
            | invalid_dte_mask
            | invalid_iv_mask
            | extreme_iv_mask
            | invalid_delta_mask
            | invalid_gamma_mask
            | invalid_vega_mask
        )

        clean_df = clean_df[
            ~invalid_mask
        ].copy()

        clean_df.reset_index(
            drop=True,
            inplace=True,
        )

        valid_rows = len(clean_df)

        removed_rows = (
            input_rows - valid_rows
        )

        # -------------------------------------------------
        # Validation report
        # -------------------------------------------------

        report = ValidationReport(
            input_rows=input_rows,
            valid_rows=valid_rows,
            removed_rows=removed_rows,
            missing_values=missing_values,
            invalid_underlying_price=(
                invalid_underlying_price
            ),
            invalid_strike=invalid_strike,
            invalid_dte=invalid_dte,
            invalid_iv=invalid_iv,
            extreme_iv=extreme_iv,
            invalid_delta=invalid_delta,
            invalid_gamma=invalid_gamma,
            invalid_vega=invalid_vega,
        )

        return clean_df, report

    def _check_required_columns(
        self,
        df: pd.DataFrame,
    ) -> None:
        """
        Ensure that all required columns exist.
        """

        missing_columns = [
            column
            for column in self.REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                "Missing required columns: "
                + ", ".join(missing_columns)
            )