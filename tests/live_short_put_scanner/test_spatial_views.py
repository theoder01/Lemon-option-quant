# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 7, 2026

from dataclasses import replace
import unittest

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backend_bases import MouseEvent
from mpl_toolkits.mplot3d import proj3d

from live_short_put_scanner.chart import (
    create_opportunity_map, prepare_chart_data, prepare_projections,
    reference_planes, tooltip_text,
)
from live_short_put_scanner.models import UnderlyingSnapshot


def sample(symbol='US.NBIS'):
    return UnderlyingSnapshot(symbol, 'Company', 38, 60, 40, 20, 20, 75, 76, 50, '2026-10-07')


class SpatialViewTests(unittest.TestCase):
    def tearDown(self):
        plt.close('all')

    def test_reference_planes_at_iv_midpoint_and_vrp_zero(self):
        planes = reference_planes((-10, 25), (-5, 80))
        self.assertEqual(len(planes), 2)
        self.assertEqual({point[0] for point in planes[0]}, {50})
        self.assertEqual({point[1] for point in planes[1]}, {0})
        self.assertEqual({point[1] for point in planes[0]}, {-10, 25})
        for plane in planes:
            self.assertEqual({point[2] for point in plane}, {-5, 80})

    def test_projections_keep_raw_values_and_order(self):
        rows = [sample(), replace(sample('US.NVDA'), iv_rank=5, vrp_rank=65, drawdown_from_52w_high=3)]
        data = prepare_projections(prepare_chart_data(rows))
        self.assertEqual(data['iv_vrp'], [('NBIS', 20, 20), ('NVDA', 5, 20)])
        self.assertEqual(data['iv_drawdown'], [('NBIS', 20, 50), ('NVDA', 5, 3)])
        self.assertEqual(data['vrp_drawdown'], [('NBIS', 20, 50), ('NVDA', 20, 3)])

    def test_empty_and_invalid_input(self):
        self.assertTrue(all(not rows for rows in prepare_projections([]).values()))
        self.assertIsNone(create_opportunity_map([replace(sample(), iv_rank=None)]))
        self.assertEqual(plt.get_fignums(), [])

    def test_four_views_have_same_points_and_no_drawdown_threshold(self):
        figure = create_opportunity_map([sample(), sample('US.NVDA')])
        self.assertEqual(len(figure.axes), 4)
        for axes in figure.axes:
            self.assertEqual(len(axes.collections[0].get_offsets()), 2)
        primary = figure.axes[1]
        self.assertEqual(len(primary.lines), 2)
        self.assertEqual(list(primary.lines[0].get_xdata()), [50, 50])
        self.assertEqual(list(primary.lines[1].get_ydata()), [0, 0])
        for axes, boundary in zip(figure.axes[2:], (50, 0)):
            self.assertEqual(len(axes.lines), 1)
            self.assertEqual(list(axes.lines[0].get_xdata()), [boundary, boundary])

    def test_tooltip_exact_values(self):
        self.assertEqual(tooltip_text(sample()),
                         'Symbol: NBIS\nPrice: 38.00\nIV: 60.00\nHV: 40.00\nIV Rank: 20.00\nVRP: +20.00\nVRP Rank: 75.00\n52W Drawdown: 50.00%')

    def test_hover_each_view_and_clear_on_leave(self):
        figure = create_opportunity_map([sample()])
        figure.canvas.draw()
        for index, axes in enumerate(figure.axes):
            coords = [(20, 20), (20, 20), (20, 50), (20, 50)][index]
            if index == 0:
                coords = proj3d.proj_transform(20, 20, 50, axes.get_proj())[:2]
            x, y = axes.transData.transform(coords)
            event = MouseEvent('motion_notify_event', figure.canvas, x, y)
            figure.canvas.callbacks.process('motion_notify_event', event)
            tooltip = axes.texts[-1]
            self.assertTrue(tooltip.get_visible())
            self.assertIn('Symbol: NBIS', tooltip.get_text())
        figure.canvas.callbacks.process('motion_notify_event', MouseEvent('motion_notify_event', figure.canvas, 0, 0))
        self.assertTrue(all(not axes.texts[-1].get_visible() for axes in figure.axes))

    def test_hover_tracks_rotated_3d_view(self):
        figure = create_opportunity_map([sample()])
        axes = figure.axes[0]
        axes.view_init(elev=35, azim=30)
        figure.canvas.draw()
        coords = proj3d.proj_transform(20, 20, 50, axes.get_proj())[:2]
        x, y = axes.transData.transform(coords)
        figure.canvas.callbacks.process('motion_notify_event', MouseEvent('motion_notify_event', figure.canvas, x, y))
        self.assertTrue(axes.texts[-1].get_visible())
        self.assertIn('VRP Rank: 75.00', axes.texts[-1].get_text())
