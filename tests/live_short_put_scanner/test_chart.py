# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 7, 2026

from dataclasses import replace
import unittest
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from live_short_put_scanner.chart import (
    create_opportunity_map, display_ticker, prepare_chart_data, show_opportunity_map,
)
from live_short_put_scanner.models import UnderlyingSnapshot


def sample(symbol="US.NVDA", **changes):
    snapshot = UnderlyingSnapshot(symbol, "Company", 80, 50, 30, 25, 20, 60, 100, 20, "2026-10-07")
    return replace(snapshot, **changes)


class ChartTests(unittest.TestCase):
    def tearDown(self):
        plt.close('all')

    def test_ticker_conversion(self):
        self.assertEqual(display_ticker('US.NVDA'), 'NVDA')
        self.assertEqual(display_ticker('NVDA'), 'NVDA')
        self.assertEqual(display_ticker('HK.00700'), 'HK.00700')

    def test_coordinate_mapping(self):
        self.assertEqual(prepare_chart_data([sample()]), [('NVDA', 25, 20, 20)])

    def test_multiple_symbols_preserve_order(self):
        snapshots = [sample('US.MSFT'), sample('US.AAPL', iv_rank=90, vrp_rank=10)]
        self.assertEqual(prepare_chart_data(snapshots), [('MSFT', 25, 20, 20), ('AAPL', 90, 20, 20)])

    def test_incomplete_or_nonfinite_coordinates_excluded(self):
        for field in ('iv_rank', 'vrp', 'vrp_rank', 'drawdown_from_52w_high'):
            for value in (None, float('nan'), float('inf'), float('-inf'), True, 'invalid'):
                with self.subTest(field=field, value=value):
                    self.assertEqual(prepare_chart_data([sample(**{field: value})]), [])

    def test_incomplete_source_metrics_excluded(self):
        for field in ('iv', 'hv', 'price'):
            self.assertEqual(prepare_chart_data([sample(**{field: None})]), [])

    def test_zero_rank_is_valid_not_missing(self):
        self.assertEqual(prepare_chart_data([sample(iv_rank=0, vrp_rank=0)]), [('NVDA', 0, 20, 20)])

    def test_invalid_ranks_not_silently_clipped(self):
        self.assertEqual(prepare_chart_data([sample(iv_rank=-1), sample(vrp_rank=101)]), [])

    def test_empty_input_creates_no_window(self):
        self.assertEqual(prepare_chart_data([]), [])
        self.assertIsNone(create_opportunity_map([]))
        self.assertFalse(show_opportunity_map([]))
        self.assertEqual(plt.get_fignums(), [])

    def test_axes_labels_points_and_padded_z_range(self):
        figure = create_opportunity_map([
            sample('US.NVDA', drawdown_from_52w_high=-5),
            sample('US.MSFT', drawdown_from_52w_high=120)])
        axes = figure.axes[0]
        self.assertEqual(axes.get_xlim(), (0, 100))
        self.assertLess(axes.get_ylim()[0], 0)
        self.assertGreater(axes.get_ylim()[1], 20)
        self.assertLess(axes.get_zlim()[0], -5)
        self.assertGreater(axes.get_zlim()[1], 120)
        self.assertEqual(axes.get_xlabel(), 'IV Rank')
        self.assertEqual(axes.get_ylabel(), 'VRP (IV - HV, pp)')
        self.assertEqual(axes.get_zlabel(), '52W Drawdown (%)')
        labels = [text.get_text().strip() for text in axes.texts]
        self.assertIn('NVDA', labels)
        self.assertIn('MSFT', labels)
        self.assertIn('O (0, 0, 0)', labels)
        self.assertEqual(len(axes.collections[0]._offsets3d[0]), 2)
        figure.canvas.draw()

    def test_single_point_has_nonzero_z_range(self):
        axes = create_opportunity_map([sample()]).axes[0]
        self.assertLess(axes.get_zlim()[0], 20)
        self.assertGreater(axes.get_zlim()[1], 20)

    def test_show_closes_figure_even_on_error(self):
        with patch.object(plt, 'show', side_effect=RuntimeError('display failed')):
            with self.assertRaises(RuntimeError):
                show_opportunity_map([sample()])
        self.assertEqual(plt.get_fignums(), [])
