# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 7, 2026

from datetime import date
import unittest
from unittest.mock import Mock

import pandas as pd

from live_short_put_scanner.futu_client import FutuClient, FutuDataError
from live_short_put_scanner.market_data import get_snapshot


class MarketDataTests(unittest.TestCase):
    def test_latest_by_time_and_consistent_sources(self):
        rows = [
            ('2026-10-06', 50, 30, 80),
            ('2026-10-01', 30, 25, 100),
            ('2026-10-04', 40, 30, 90),
            ('invalid', 999, 0, 999),
            ('2024-01-01', 999, 0, 999),
        ]
        for ordered in (rows, list(reversed(rows))):
            client = Mock()
            client.get_overview.return_value = pd.DataFrame([
                {'code': 'US.NVDA', 'name': 'NVIDIA', 'iv_rank': 73, 'iv': 999}])
            history = pd.DataFrame(ordered, columns=['time', 'iv', 'hv', 'underlying_price'])
            history['code'] = 'US.NVDA'
            client.get_history.return_value = history
            result = get_snapshot(client, 'US.NVDA', date(2026, 10, 7))
            self.assertEqual((result.price, result.iv, result.hv, result.iv_rank), (80, 50, 30, 73))
            self.assertEqual((result.vrp, result.vrp_rank, result.high_52w_close), (20, 100, 100))
            self.assertEqual(result.drawdown_from_52w_high, 20)

    def test_empty_history_is_explicit_error(self):
        client = Mock()
        client.get_overview.return_value = pd.DataFrame([{'code': 'US.NVDA', 'iv_rank': 50}])
        client.get_history.return_value = pd.DataFrame(columns=['code', 'time', 'iv', 'hv', 'underlying_price'])
        with self.assertRaises(FutuDataError):
            get_snapshot(client, 'US.NVDA', date(2026, 10, 7))

    def test_latest_missing_values_do_not_fall_back(self):
        client = Mock()
        client.get_overview.return_value = pd.DataFrame([{'code': 'US.NVDA', 'iv_rank': 50, 'iv': 80}])
        client.get_history.return_value = pd.DataFrame([
            {'code': 'US.NVDA', 'time': '2026-10-06', 'iv': None, 'hv': 30, 'underlying_price': None},
            {'code': 'US.NVDA', 'time': '2026-10-01', 'iv': 40, 'hv': 20, 'underlying_price': 100},
        ])
        result = get_snapshot(client, 'US.NVDA', date(2026, 10, 7))
        self.assertIsNone(result.iv)
        self.assertIsNone(result.price)
        self.assertIsNone(result.vrp)

    def test_all_pages_including_empty_page(self):
        client = FutuClient()
        client._context = Mock()
        client._context.get_option_underlying_his_volatility.side_effect = [
            (0, pd.DataFrame({'iv': [10]}), b'next'),
            (0, pd.DataFrame({'iv': []}), b'last'),
            (0, pd.DataFrame({'iv': [20]}), None),
        ]
        result = client.get_history('US.NVDA', '2025-10-07', '2026-10-07')
        self.assertEqual(result['iv'].tolist(), [10, 20])
        calls = client._context.get_option_underlying_his_volatility.call_args_list
        self.assertEqual([call.kwargs['page_req_key'] for call in calls], [None, b'next', b'last'])

    def test_page_error_rejects_partial_history(self):
        client = FutuClient()
        client._context = Mock()
        client._context.get_option_underlying_his_volatility.side_effect = [
            (0, pd.DataFrame({'iv': [10]}), b'next'), (-1, 'denied', None)]
        with self.assertRaisesRegex(FutuDataError, 'denied'):
            client.get_history('US.NVDA', '2025-10-07', '2026-10-07')

    def test_repeated_page_key_rejected(self):
        client = FutuClient()
        client._context = Mock()
        client._context.get_option_underlying_his_volatility.return_value = (0, pd.DataFrame(), b'next')
        with self.assertRaisesRegex(FutuDataError, 'repeated'):
            client.get_history('US.NVDA', '2025-10-07', '2026-10-07')

    def test_exit_closes_even_on_exception(self):
        client = FutuClient()
        context = Mock()
        client._context = context
        client.__exit__(ValueError, ValueError('failed'), None)
        client.close()
        context.close.assert_called_once()
