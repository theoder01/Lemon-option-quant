# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 17, 2026

from datetime import date, datetime
from zoneinfo import ZoneInfo


UTC = ZoneInfo("UTC")
NEW_YORK = ZoneInfo("America/New_York")


def now_utc() -> datetime:
    """
    Return the current time as a timezone-aware UTC datetime.

    The result is independent of the local timezone of the
    computer running the application.
    """
    return datetime.now(UTC)


def get_trading_date(
    timestamp: datetime,
) -> date:
    """
    Return the New York calendar date for a timestamp.

    Parameters
    ----------
    timestamp : datetime
        A timezone-aware datetime.

    Returns
    -------
    date
        Calendar date in the America/New_York timezone.
    """
    if timestamp.tzinfo is None:
        raise ValueError(
            "timestamp must be timezone-aware"
        )

    new_york_time = timestamp.astimezone(
        NEW_YORK
    )

    return new_york_time.date()


def get_trading_day_utc_bounds(
    trading_date: date,
) -> tuple[datetime, datetime]:
    """
    Return the UTC boundaries of a New York calendar day.

    The returned interval is:

        [start_utc, end_utc)

    Daylight saving time is handled automatically.

    Parameters
    ----------
    trading_date : date
        Calendar date in America/New_York.

    Returns
    -------
    tuple[datetime, datetime]
        Start and end of the New York calendar day,
        converted to UTC.
    """
    start_new_york = datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        tzinfo=NEW_YORK,
    )

    next_date = trading_date.fromordinal(
        trading_date.toordinal() + 1
    )

    end_new_york = datetime(
        next_date.year,
        next_date.month,
        next_date.day,
        tzinfo=NEW_YORK,
    )

    start_utc = start_new_york.astimezone(UTC)
    end_utc = end_new_york.astimezone(UTC)

    return start_utc, end_utc