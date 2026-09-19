# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 13, 2026

from option_quant.collector import collect_option_snapshot
from option_quant.config import (
    FUTU_HOST,
    FUTU_PORT,
    UNDERLYINGS,
)
from option_quant.database import OptionDatabase
from option_quant.futu_client import FutuClient
from option_quant.validator import OptionDataValidator


DATABASE_PATH = "data/options.db"


def main():
    client = FutuClient(
        host=FUTU_HOST,
        port=FUTU_PORT,
    )

    database = OptionDatabase(
        DATABASE_PATH
    )

    validator = OptionDataValidator()

    try:

        for underlying in UNDERLYINGS:

            print()
            print("=" * 60)
            print(f"Collecting {underlying}")
            print("=" * 60)

            try:

                # -------------------------------------------------
                # 1. Collect option snapshot
                # -------------------------------------------------

                df = collect_option_snapshot(
                    client=client,
                    underlying=underlying,
                )

                if df.empty:
                    print(
                        f"No option data collected "
                        f"for {underlying}."
                    )
                    continue

                print(df)

                print()
                print(
                    f"Collected {len(df)} "
                    f"Put contracts for {underlying}."
                )

                # -------------------------------------------------
                # 2. Validate and clean option data
                # -------------------------------------------------

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

                # -------------------------------------------------
                # 3. Show removal reasons if invalid data exists
                # -------------------------------------------------

                if report.removed_rows > 0:

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

                # -------------------------------------------------
                # 4. Skip database write if nothing valid remains
                # -------------------------------------------------

                if clean_df.empty:
                    print(
                        f"No valid option data "
                        f"for {underlying}."
                    )
                    continue

                # -------------------------------------------------
                # 5. Save validated data to SQLite
                # -------------------------------------------------

                saved_count, duplicate_count = (
                    database.save_snapshots(
                        clean_df
                    )
                )

                print()
                print(
                    f"Saved {saved_count} new rows "
                    f"to {DATABASE_PATH}"
                )

                print(
                    f"Skipped {duplicate_count} "
                    f"duplicate rows."
                )

            except Exception as error:

                print(
                    f"Failed to collect "
                    f"{underlying}: {error}"
                )

    finally:

        client.close()


if __name__ == "__main__":
    main()