# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 18, 2026

import time
from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


def retry(
    operation: Callable[[], T],
    max_attempts: int = 3,
    delay_seconds: float = 5.0,
) -> T:
    """
    Execute an operation and retry it if it fails.

    Parameters
    ----------
    operation : Callable
        Function to execute.

    max_attempts : int
        Maximum number of attempts, including
        the first attempt.

    delay_seconds : float
        Number of seconds to wait between attempts.

    Returns
    -------
    T
        Result returned by the operation.

    Raises
    ------
    Exception
        Re-raises the last exception if all attempts fail.
    """

    if max_attempts <= 0:
        raise ValueError(
            "max_attempts must be greater than 0"
        )

    if delay_seconds < 0:
        raise ValueError(
            "delay_seconds must not be negative"
        )

    last_exception = None

    for attempt in range(
        1,
        max_attempts + 1,
    ):
        try:
            return operation()

        except Exception as exc:
            last_exception = exc

            if attempt == max_attempts:
                break

            print(
                f"Operation failed "
                f"(attempt {attempt}/{max_attempts}). "
                f"Retrying in {delay_seconds:.1f} seconds..."
            )

            time.sleep(
                delay_seconds
            )

    raise last_exception