# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 7, 2026

from types import TracebackType

import pandas as pd

from .config import FUTU_HOST, FUTU_PORT


class FutuDataError(RuntimeError):
    """OpenD request failure; partial history must not be used."""


class FutuClient:
    def __init__(self, host: str = FUTU_HOST, port: int = FUTU_PORT):
        self.host = host
        self.port = port
        self._context = None
        self._ret_ok = 0

    def __enter__(self) -> "FutuClient":
        from futu import OpenQuoteContext, RET_OK

        self._ret_ok = RET_OK
        self._context = OpenQuoteContext(host=self.host, port=self.port)
        return self

    def __exit__(self, exc_type: type[BaseException] | None,
                 exc: BaseException | None, traceback: TracebackType | None) -> None:
        self.close()

    def close(self) -> None:
        if self._context is not None:
            context, self._context = self._context, None
            context.close()

    def _connected(self):
        if self._context is None:
            raise FutuDataError("Use FutuClient inside a with statement.")
        return self._context

    def get_overview(self, symbol: str) -> pd.DataFrame:
        ret, data = self._connected().get_option_underlying_overview([symbol])
        if ret != self._ret_ok:
            raise FutuDataError(f"{symbol}: underlying overview failed: {data}")
        return data

    def get_history(self, symbol: str, begin: str, end: str) -> pd.DataFrame:
        pages = []
        page_key = None
        seen_keys = set()
        while True:
            ret, data, next_key = self._connected().get_option_underlying_his_volatility(
                symbol, begin_time=begin, end_time=end, page_req_key=page_key,
            )
            if ret != self._ret_ok:
                raise FutuDataError(f"{symbol}: historical volatility failed: {data}")
            pages.append(data)
            if next_key is None:
                break
            if next_key in seen_keys:
                raise FutuDataError(f"{symbol}: repeated historical pagination key")
            seen_keys.add(next_key)
            page_key = next_key
        return pd.concat(pages, ignore_index=True)
