# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 7, 2026

from contextlib import redirect_stdout
from dataclasses import replace
import io
import unittest
from unittest.mock import Mock, patch

from live_short_put_scanner.config import UNDERLYINGS
from live_short_put_scanner.main import main
from live_short_put_scanner.market_data import scan_underlyings
from live_short_put_scanner.models import ScanResult, UnderlyingSnapshot


def sample(symbol):
    return UnderlyingSnapshot(symbol, 'Company', 80, 50, 30, 25, 20, 60, 100, 20, '2026-10-07')


class ScanTests(unittest.TestCase):
    def test_configured_universe_is_scanned_in_order(self):
        with patch('live_short_put_scanner.market_data.get_snapshot',
                   side_effect=lambda client, symbol: sample(symbol)) as get:
            result = scan_underlyings(Mock(), UNDERLYINGS)
        self.assertEqual([call.args[1] for call in get.call_args_list], UNDERLYINGS)
        self.assertEqual(result.requested, UNDERLYINGS)
        self.assertEqual([row.symbol for row in result.snapshots], UNDERLYINGS)
        self.assertEqual(len(result.snapshots), len(UNDERLYINGS))
        self.assertEqual(result.skipped, {})

    def test_all_symbols_attempted_despite_errors_and_missing_data(self):
        def fetch(client, symbol):
            if symbol == 'US.SPCX':
                raise RuntimeError('API unavailable')
            if symbol == 'US.SKHY':
                return replace(sample(symbol), hv=None)
            return sample(symbol)
        with patch('live_short_put_scanner.market_data.get_snapshot', side_effect=fetch) as get:
            result = scan_underlyings(Mock(), UNDERLYINGS)
        self.assertEqual([c.args[1] for c in get.call_args_list], UNDERLYINGS)
        self.assertEqual(result.requested, UNDERLYINGS)
        self.assertEqual(list(result.skipped),
                         [symbol for symbol in UNDERLYINGS if symbol in ('US.SPCX', 'US.SKHY')])
        self.assertEqual([s.symbol for s in result.snapshots], [s for s in UNDERLYINGS if s not in result.skipped])
        self.assertIn('API unavailable', result.skipped['US.SPCX'])
        self.assertIn('hv', result.skipped['US.SKHY'])

    def test_undefined_history_rank_skipped(self):
        with patch('live_short_put_scanner.market_data.get_snapshot', return_value=replace(sample('US.NVDA'), vrp_rank=None)):
            result = scan_underlyings(Mock(), ['US.NVDA'])
        self.assertEqual(result.snapshots, [])
        self.assertIn('history', result.skipped['US.NVDA'])

    def test_connection_closed_before_chart_and_summary_printed(self):
        result = ScanResult(['US.NVDA', 'US.SPCX'], [sample('US.NVDA')], {'US.SPCX': 'no data'})
        with patch('live_short_put_scanner.main.FutuClient') as client, \
             patch('live_short_put_scanner.main.scan_underlyings', return_value=result), \
             patch('live_short_put_scanner.main.show_opportunity_map') as show:
            def verify_closed(snapshots):
                client.return_value.__exit__.assert_called_once()
                self.assertEqual(snapshots, result.snapshots)
            show.side_effect = verify_closed
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(), 1)
        self.assertIn('Requested symbols (2)', output.getvalue())
        self.assertIn('Successfully calculated symbols: 1', output.getvalue())
        self.assertIn('WARNING US.SPCX: no data', output.getvalue())

    def test_empty_results_do_not_open_chart(self):
        with patch('live_short_put_scanner.main.FutuClient'), \
             patch('live_short_put_scanner.main.scan_underlyings', return_value=ScanResult(['US.NVDA'], [], {'US.NVDA': 'missing IV'})), \
             patch('live_short_put_scanner.main.show_opportunity_map') as show, redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 1)
            show.assert_not_called()

    def test_connection_error_reports_entire_requested_universe(self):
        with patch('live_short_put_scanner.main.FutuClient', side_effect=RuntimeError('connection refused')), \
             patch('live_short_put_scanner.main.show_opportunity_map') as show:
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(), 1)
            show.assert_not_called()
        self.assertIn(f'Skipped symbols: {len(UNDERLYINGS)}', output.getvalue())
        self.assertIn(f'Requested symbols ({len(UNDERLYINGS)})', output.getvalue())
        for symbol in UNDERLYINGS:
            self.assertIn(f'WARNING {symbol}:', output.getvalue())
