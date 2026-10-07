# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 7, 2026

from contextlib import redirect_stdout
from dataclasses import replace
import io
import unittest

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from live_short_put_scanner.chart import (
    create_opportunity_map, padded_zero_range, prepare_chart_data,
    prepare_projections, tooltip_text,
)
from live_short_put_scanner.main import print_results
from live_short_put_scanner.models import ScanResult, UnderlyingSnapshot


def snapshot(vrp):
    return UnderlyingSnapshot('US.NVDA', 'NVIDIA', 80, 30, 30-vrp,
                              40, vrp, 60, 100, 20, '2026-10-07')


class RawVRPTests(unittest.TestCase):
    def tearDown(self):
        plt.close('all')

    def test_positive_negative_and_zero_are_raw_coordinates(self):
        for value in (12, -5, 0):
            with self.subTest(vrp=value):
                data = prepare_chart_data([snapshot(value)])
                self.assertEqual(data, [('NVDA', 40, value, 20)])
                projections = prepare_projections(data)
                self.assertEqual(projections['iv_vrp'], [('NVDA', 40, value)])
                self.assertEqual(projections['vrp_drawdown'], [('NVDA', value, 20)])

    def test_range_includes_zero_for_all_signs_and_constant_data(self):
        for values in ([4, 9], [-12, -5], [-8, 6], [0], [7, 7], []):
            low, high = padded_zero_range(values)
            self.assertLess(low, min([0, *values]))
            self.assertGreater(high, max([0, *values]))

    def test_negative_vrp_not_clipped_in_any_view(self):
        figure = create_opportunity_map([snapshot(-5), replace(snapshot(12), symbol='US.MSFT')])
        axes3d, primary, _, support = figure.axes
        self.assertEqual(list(axes3d.collections[0]._offsets3d[1]), [-5, 12])
        self.assertEqual(list(primary.collections[0].get_offsets()[:, 1]), [-5, 12])
        self.assertEqual(list(support.collections[0].get_offsets()[:, 0]), [-5, 12])
        self.assertEqual(axes3d.get_ylim(), primary.get_ylim())
        self.assertEqual(axes3d.get_ylim(), support.get_xlim())
        self.assertLess(primary.get_ylim()[0], -5)
        self.assertGreater(primary.get_ylim()[1], 12)

    def test_zero_observation_visible_and_origin_in_bounds(self):
        figure = create_opportunity_map([snapshot(0)])
        axes = figure.axes[0]
        for low, high in (axes.get_xlim(), axes.get_ylim(), axes.get_zlim()):
            self.assertLessEqual(low, 0)
            self.assertGreater(high, 0)
        self.assertIn('O (0, 0, 0)', [text.get_text().strip() for text in axes.texts])
        self.assertEqual(list(figure.axes[1].collections[0].get_offsets()[:, 1]), [0])
        figure.canvas.draw()

    def test_vrp_rank_is_context_not_primary_coordinate(self):
        row = snapshot(-5)
        self.assertEqual(row.vrp_rank, 60)
        self.assertEqual(prepare_chart_data([row])[0][2], -5)
        self.assertIn('VRP: -5.00', tooltip_text(row))
        self.assertIn('VRP Rank: 60.00', tooltip_text(row))
        self.assertIn('IV: 30.00', tooltip_text(row))
        self.assertIn('HV: 35.00', tooltip_text(row))

    def test_terminal_preserves_rank_and_signed_raw_premium(self):
        for value, expected in ((12, '+12.00'), (-5, '-5.00'), (0, '+0.00')):
            output = io.StringIO()
            with redirect_stdout(output):
                print_results(ScanResult(['US.NVDA'], [snapshot(value)], {}))
            self.assertIn('VRP Rank', output.getvalue())
            self.assertIn(expected, output.getvalue())
