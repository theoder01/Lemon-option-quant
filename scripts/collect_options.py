# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 13, 2026

from option_quant.collection_service import CollectionService
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

    service = CollectionService(
        client=client,
        database=database,
        validator=validator,
    )

    try:

        for underlying in UNDERLYINGS:

            print()
            print("=" * 60)
            print(f"Collecting {underlying}")
            print("=" * 60)

            result = service.collect(
                underlying
            )

            print()
            print("Collection Result")
            print("-" * 40)

            print(
                f"Underlying:      "
                f"{result.underlying}"
            )

            print(
                f"Success:         "
                f"{result.success}"
            )

            print(
                f"Collected rows:  "
                f"{result.collected_rows}"
            )

            print(
                f"Valid rows:      "
                f"{result.valid_rows}"
            )

            print(
                f"Removed rows:    "
                f"{result.removed_rows}"
            )

            print(
                f"Saved rows:      "
                f"{result.saved_rows}"
            )

            print(
                f"Duplicate rows:  "
                f"{result.duplicate_rows}"
            )

            if result.error is not None:
                print(
                    f"Error:           "
                    f"{result.error}"
                )

    finally:

        client.close()


if __name__ == "__main__":
    main()