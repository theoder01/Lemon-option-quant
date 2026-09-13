# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 13, 2026

from option_quant.futu_client import FutuClient
from option_quant.collector import collect_option_snapshot
from option_quant.database import OptionDatabase

from option_quant.config import (
    FUTU_HOST,
    FUTU_PORT,
    UNDERLYINGS,
)


DATABASE_PATH = "data/options.db"


def main():

    client = FutuClient(
        host=FUTU_HOST,
        port=FUTU_PORT,
    )

    database = OptionDatabase(
        DATABASE_PATH
    )

    try:

        for underlying in UNDERLYINGS:

            print()
            print("=" * 60)
            print(f"Collecting {underlying}")
            print("=" * 60)

            try:

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

                # Save to SQLite database
                database.save_snapshots(df)

                print(
                    f"Saved {len(df)} rows "
                    f"to {DATABASE_PATH}"
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