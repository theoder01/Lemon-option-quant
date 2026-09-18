# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 13, 2026

import futu as ft
from option_quant.rate_limiter import RateLimiter
from option_quant.retry import retry

class FutuClient:
    """
    Thin wrapper around Futu OpenAPI quote context.

    This class is responsible only for communication with Futu OpenD.
    Strategy logic, option filtering, and database operations are handled
    elsewhere.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 11111,
    ):
        self.host = host
        self.port = port

        self.option_chain_limiter = RateLimiter(
            max_calls=9,
            period_seconds=31,
        )

        
        self.quote_ctx = ft.OpenQuoteContext(
            host=self.host,
            port=self.port,
        )

    def close(self):
        """Close the connection to Futu OpenD."""
        self.quote_ctx.close()

    def get_market_snapshot(self, codes):
        """
        Get market snapshots for one or more securities.

        Parameters
        ----------
        codes : list[str]
            Futu security codes, for example:
            ["US.NVDA"]
            or
            ["US.NVDA260914P200000"]

        Returns
        -------
        pandas.DataFrame
            Snapshot data returned by Futu.
        """

        ret, data = self.quote_ctx.get_market_snapshot(codes)

        if ret != ft.RET_OK:
            raise RuntimeError(
                f"Failed to get market snapshot: {data}"
            )

        return data

    def get_option_chain(
        self,
        code,
        start=None,
        end=None,
    ):
        """
        Get option chain for an underlying
        within a specified date range.

        Requests are rate-limited and retried
        when a temporary API failure occurs.
        """

        def operation():

            self.option_chain_limiter.wait()

            ret, data = self.quote_ctx.get_option_chain(
                code=code,
                start=start,
                end=end,
            )

            if ret != ft.RET_OK:
                raise RuntimeError(
                    f"Failed to get option chain "
                    f"for {code}: {data}"
                )

            return data

        return retry(
            operation=operation,
            max_attempts=3,
            delay_seconds=5,
        )

    def get_option_expiration_dates(self, code):
        """
        Get all available option expiration dates
        for an underlying.
        """

        ret, data = (
            self.quote_ctx.get_option_expiration_date(
                code=code
            )
        )

        if ret != ft.RET_OK:
            raise RuntimeError(
                f"Failed to get option expiration dates "
                f"for {code}: {data}"
            )

        return data

    def get_last_price(self, code):
        """
        Get the latest traded price of an underlying.

        Parameters
        ----------
        code : str
            Futu security code.

        Returns
        -------
        float
            Latest traded price.
        """

        data = self.get_market_snapshot([code])

        return float(
            data.iloc[0]["last_price"]
        )