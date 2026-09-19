# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 19, 2026

from dataclasses import dataclass


@dataclass
class CollectionResult:
    """
    Result of one option snapshot collection
    for a single underlying.
    """

    underlying: str

    collected_rows: int = 0
    valid_rows: int = 0
    removed_rows: int = 0

    saved_rows: int = 0
    duplicate_rows: int = 0

    success: bool = True
    error: str | None = None