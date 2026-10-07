# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 7, 2026

import unittest

from live_short_put_scanner.calculations import (
    calculate_distance_from_high, calculate_high_52w_close,
    calculate_vrp, calculate_vrp_rank,
)


class CalculationTests(unittest.TestCase):
    def test_vrp_percentage_points(self):
        self.assertAlmostEqual(calculate_vrp(74.32, 67.338), 6.982)

    def test_vrp_missing(self):
        for missing in (None, float('nan'), float('inf'), 'invalid'):
            self.assertIsNone(calculate_vrp(missing, 10))
            self.assertIsNone(calculate_vrp(10, missing))

    def test_vrp_rank_normal(self):
        self.assertEqual(calculate_vrp_rank(5, [-5, 5, 15]), 50)

    def test_vrp_rank_minimum(self):
        self.assertEqual(calculate_vrp_rank(-5, [-5, 5, 15]), 0)

    def test_vrp_rank_maximum(self):
        self.assertEqual(calculate_vrp_rank(15, [-5, 5, 15]), 100)

    def test_rank_zero_range(self):
        self.assertIsNone(calculate_vrp_rank(5, [5, 5]))

    def test_rank_missing(self):
        self.assertEqual(calculate_vrp_rank(5, [0, None, float('nan'), float('inf'), 10]), 50)
        for values in ([], [None, float('nan')]):
            self.assertIsNone(calculate_vrp_rank(5, values))
        self.assertIsNone(calculate_vrp_rank(None, [0, 10]))
        self.assertIsNone(calculate_vrp_rank(float('nan'), [0, 10]))

    def test_rank_outside_range(self):
        self.assertEqual(calculate_vrp_rank(-20, [0, 10]), 0)
        self.assertEqual(calculate_vrp_rank(20, [0, 10]), 100)

    def test_highest_close(self):
        self.assertEqual(calculate_high_52w_close([235.78, 286.69, None, float('nan'), 250]), 286.69)
        self.assertIsNone(calculate_high_52w_close([]))
        self.assertIsNone(calculate_high_52w_close([None, -1, 0, float('inf')]))

    def test_distance(self):
        self.assertAlmostEqual(calculate_distance_from_high(235.78, 286.69), (286.69-235.78)/286.69*100)
        self.assertEqual(calculate_distance_from_high(100, 100), 0)
        self.assertEqual(calculate_distance_from_high(110, 100), -10)

    def test_distance_missing_or_invalid(self):
        for value in (None, 0, -1, float('nan'), float('inf')):
            self.assertIsNone(calculate_distance_from_high(100, value))
            self.assertIsNone(calculate_distance_from_high(value, 100))

    def test_overflow_never_returns_nonfinite(self):
        self.assertIsNone(calculate_vrp(1e308, -1e308))
        self.assertIsNone(calculate_vrp_rank(0, [-1e308, 1e308]))
