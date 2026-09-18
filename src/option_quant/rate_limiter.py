# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 18, 2026

import time
from collections import deque
from threading import Lock


class RateLimiter:
    """
    Thread-safe sliding-window API rate limiter.

    The limiter allows at most ``max_calls`` requests
    within ``period_seconds``.

    If the request limit has been reached, the caller
    waits until another request is allowed.
    """

    def __init__(
        self,
        max_calls: int,
        period_seconds: float,
    ):
        if max_calls <= 0:
            raise ValueError(
                "max_calls must be greater than 0"
            )

        if period_seconds <= 0:
            raise ValueError(
                "period_seconds must be greater than 0"
            )

        self.max_calls = max_calls
        self.period_seconds = period_seconds

        self._calls = deque()
        self._lock = Lock()

    def wait(self) -> None:
        """
        Wait until an API request is allowed.

        A monotonic clock is used so that changes to the
        system clock do not affect rate limiting.
        """

        while True:

            with self._lock:

                now = time.monotonic()

                # Remove requests that are outside
                # the current sliding time window.
                while (
                    self._calls
                    and now - self._calls[0]
                    >= self.period_seconds
                ):
                    self._calls.popleft()

                # A request is allowed immediately.
                if len(self._calls) < self.max_calls:

                    self._calls.append(now)

                    return

                # Calculate how long we must wait
                # until the oldest request expires.
                wait_seconds = (
                    self.period_seconds
                    - (now - self._calls[0])
                )

            # Sleep outside the lock so that the lock
            # is not held while waiting.
            time.sleep(
                max(wait_seconds, 0.01)
            )