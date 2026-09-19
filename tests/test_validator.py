# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 19, 2026

from option_quant.collector import collect_option_snapshot
from option_quant.config import UNDERLYINGS
from option_quant.futu_client import FutuClient
from option_quant.validator import OptionDataValidator


def main():
    """
    Test option data validation using live Futu data.

    This script does not write anything to the database.
    """

    client = FutuClient()
    validator = OptionDataValidator()

    try:
        for underlying in UNDERLYINGS:

            print()
            print("=" * 60)
            print(f"Validating {underlying}")
            print("=" * 60)

            df = collect_option_snapshot(
                client=client,
                underlying=underlying,
            )

            clean_df, report = validator.validate(
                df
            )

            print()
            print("Validation Report")
            print("-" * 40)

            print(
                f"Input rows:        "
                f"{report.input_rows}"
            )
            print(
                f"Valid rows:        "
                f"{report.valid_rows}"
            )
            print(
                f"Removed rows:      "
                f"{report.removed_rows}"
            )

            print()
            print("Removal reasons")
            print("-" * 40)

            print(
                f"Missing values:    "
                f"{report.missing_values}"
            )
            print(
                f"Invalid price:     "
                f"{report.invalid_underlying_price}"
            )
            print(
                f"Invalid strike:    "
                f"{report.invalid_strike}"
            )
            print(
                f"Invalid DTE:       "
                f"{report.invalid_dte}"
            )
            print(
                f"Invalid IV:        "
                f"{report.invalid_iv}"
            )
            print(
                f"Extreme IV:        "
                f"{report.extreme_iv}"
            )
            print(
                f"Invalid delta:     "
                f"{report.invalid_delta}"
            )
            print(
                f"Invalid gamma:     "
                f"{report.invalid_gamma}"
            )
            print(
                f"Invalid vega:      "
                f"{report.invalid_vega}"
            )

            # Show removed contracts for inspection.
            removed_codes = set(
                df["option_code"]
            ) - set(
                clean_df["option_code"]
            )

            if removed_codes:

                removed_df = df[
                    df["option_code"].isin(
                        removed_codes
                    )
                ]

                print()
                print("Removed contracts")
                print("-" * 40)

                print(
                    removed_df[
                        [
                            "option_code",
                            "dte",
                            "strike",
                            "iv",
                            "delta",
                            "gamma",
                            "vega",
                        ]
                    ].to_string(
                        index=False
                    )
                )

    finally:
        client.close()


if __name__ == "__main__":
    main()