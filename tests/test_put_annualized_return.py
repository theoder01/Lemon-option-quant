# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 28, 2026

from inspect import signature
from datetime import date, datetime, timedelta, timezone
import unittest

from option_quant.analytics.put_annualized_return import (
    actual_remaining_days,
    calculate_initial_annualized_return,
    calculate_remaining_annualized_return,
)


class PutAnnualizedReturnTests(unittest.TestCase):
    def setUp(self):
        self.args = dict(
            strike=50, as_of=date(2026, 9, 28),
            expiration=date(2026, 10, 28),
        )

    def initial(self, **changes):
        return calculate_initial_annualized_return(**(dict(self.args, premium=2, opening_fee=0) | changes))

    def remaining(self, **changes):
        return calculate_remaining_annualized_return(**(dict(self.args, close_premium=0.5, closing_fee=0) | changes))

    def test_initial_gross_and_total_fees(self):
        result = self.initial(contracts=2, opening_fee=3)
        self.assertEqual(result.gross_collateral, 10000)
        self.assertEqual(result.potential_profit, 397)
        self.assertAlmostEqual(result.annualized_return, 397 / 10000 * 365 / 30)

    def test_remaining_is_avoided_buyback_plus_fee(self):
        result = self.remaining(contracts=2, closing_fee=3)
        self.assertEqual(result.potential_profit, 103)
        self.assertAlmostEqual(result.annualized_return, 103 / 10000 * 365 / 30)

    def test_remaining_matches_difference_between_terminal_profits(self):
        # Different historical credits/fees cancel from the hold-close choice.
        for credit, opening_fee in [(200, 1), (800, 5)]:
            closing_cost, closing_fee = 50, 2
            hold_profit = credit - opening_fee
            close_profit = credit - opening_fee - closing_cost - closing_fee
            result = self.remaining(closing_fee=closing_fee)
            self.assertEqual(result.potential_profit, hold_profit - close_profit)

    def test_initial_explicit_formula(self):
        result = self.initial(strike=100, premium=1.92, opening_fee=2.50)
        self.assertEqual(result.gross_collateral, 100 * 100)
        self.assertEqual(result.potential_profit, 1.92 * 100 - 2.50)
        self.assertEqual(result.period_return, result.potential_profit / 10000)
        self.assertEqual(result.annualized_return, result.potential_profit / 10000 * 365 / 30)
        self.assertEqual(result.transaction_fee, 2.50)

    def test_remaining_explicit_formula(self):
        result = self.remaining(strike=100, close_premium=0.30, closing_fee=2.50,
                                expiration=self.args['as_of'] + timedelta(days=20))
        self.assertEqual(result.gross_collateral, 10000)
        self.assertEqual(result.potential_profit, 32.50)
        self.assertEqual(result.period_return, 32.50 / 10000)
        self.assertEqual(result.annualized_return, 32.50 / 10000 * 365 / 20)
        self.assertAlmostEqual(result.annualized_return, 0.0593125)
        self.assertEqual(result.transaction_fee, 2.50)

    def test_remaining_inputs_only_describe_current_position(self):
        self.assertEqual(set(signature(calculate_remaining_annualized_return).parameters),
                         {'strike', 'close_premium', 'as_of', 'expiration', 'contracts', 'closing_fee'})

    def test_explicit_zero_fees_override_estimates(self):
        for result in [self.initial(), self.remaining()]:
            self.assertEqual(result.transaction_fee, 0)
            self.assertIsNone(result.fee_estimate)
            self.assertEqual(result.fee_source, 'manual')
        self.assertEqual(self.remaining().potential_profit, 50)

    def test_remaining_invalid_dates_and_collateral_rejected(self):
        for expiry in [self.args['as_of'], self.args['as_of'] - timedelta(days=1)]:
            with self.subTest(expiry=expiry), self.assertRaises(ValueError):
                self.remaining(expiration=expiry)
        for strike in [0, -1, float('nan'), float('inf'), True]:
            with self.subTest(strike=strike), self.assertRaises(ValueError):
                self.remaining(strike=strike)

    def test_contract_scaling_with_proportional_fees(self):
        one = self.initial(opening_fee=1)
        three = self.initial(contracts=3, opening_fee=3)
        self.assertEqual(three.potential_profit, one.potential_profit * 3)
        self.assertEqual(three.annualized_return, one.annualized_return)

    def test_actual_calendar_days_include_leap_day(self):
        self.assertEqual(actual_remaining_days(date(2028, 2, 28), date(2028, 3, 1)), 2)
        result = self.initial(as_of=date(2028, 2, 28), expiration=date(2028, 3, 1))
        self.assertEqual(result.annualized_return, 0.04 * 365 / 2)

    def test_intraday_fraction_and_offsets(self):
        start = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
        end = datetime(2026, 9, 28, 20, tzinfo=timezone(timedelta(hours=2)))
        result = self.remaining(as_of=start, expiration=end)
        self.assertEqual(result.remaining_days, 0.25)
        self.assertEqual(result.annualized_return, 0.01 * 365 / 0.25)

    def test_changed_utc_offset_uses_elapsed_time(self):
        start = datetime(2026, 3, 7, 16, tzinfo=timezone(timedelta(hours=-5)))
        end = datetime(2026, 3, 8, 16, tzinfo=timezone(timedelta(hours=-4)))
        self.assertEqual(actual_remaining_days(start, end), 23 / 24)

    def test_invalid_dates_rejected(self):
        for end in [self.args['as_of'], date(2026, 9, 27), '2026-10-28', datetime(2026, 10, 28)]:
            with self.subTest(end=end), self.assertRaises(ValueError):
                self.initial(expiration=end)
        with self.assertRaises(ValueError):
            actual_remaining_days(datetime(2026, 9, 28), datetime(2026, 10, 28))

    def test_invalid_numbers_rejected(self):
        for field in ['strike', 'premium', 'opening_fee']:
            for value in [-1, float('nan'), float('inf'), True]:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.initial(**{field: value})
        for field in ['close_premium', 'closing_fee']:
            for value in [-1, float('nan'), float('inf'), True]:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.remaining(**{field: value})
        with self.assertRaises(ValueError):
            self.initial(strike=0)

    def test_contract_count_must_be_positive_integer(self):
        for value in [0, -1, 1.5, True, '2']:
            for function in [self.initial, self.remaining]:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    function(contracts=value)

    def test_zero_and_negative_net_returns_preserved(self):
        self.assertEqual(self.initial(premium=0).annualized_return, 0)
        self.assertEqual(self.remaining(close_premium=0).annualized_return, 0)
        self.assertLess(self.initial(premium=0, opening_fee=1).annualized_return, 0)

    def test_default_fees_are_automatic(self):
        initial = calculate_initial_annualized_return(**self.args, premium=2)
        remaining = calculate_remaining_annualized_return(**self.args, close_premium=0.30)
        self.assertAlmostEqual(initial.transaction_fee, 2.5275)
        self.assertAlmostEqual(initial.potential_profit, 200 - 2.5275)
        self.assertAlmostEqual(initial.annualized_return, (200 - 2.5275) / 5000 * 365 / 30)
        self.assertAlmostEqual(remaining.transaction_fee, 2.5075)
        self.assertAlmostEqual(remaining.potential_profit, 30 + 2.5075)
        self.assertAlmostEqual(remaining.annualized_return, (30 + 2.5075) / 5000 * 365 / 30)
        self.assertIsNotNone(initial.fee_estimate)
        self.assertGreater(initial.fee_estimate.sec, 0)
        self.assertGreater(initial.fee_estimate.trading_activity, 0)
        self.assertEqual(remaining.fee_estimate.sec, 0)
        self.assertEqual(remaining.fee_estimate.trading_activity, 0)
        self.assertIn('2026-09-28', remaining.fee_source)

    def test_explicit_override_not_added_to_estimate(self):
        result = self.remaining(closing_fee=1.25)
        self.assertEqual(result.transaction_fee, 1.25)
        self.assertEqual(result.potential_profit, 51.25)
        self.assertIsNone(result.fee_estimate)
        self.assertEqual(result.fee_source, 'manual')

    def test_risk_notice_travels_with_result(self):
        for result in [self.initial(), self.remaining()]:
            self.assertIn('not a guaranteed', result.risk_notice)
            self.assertIn('assignment', result.risk_notice)


if __name__ == '__main__':
    unittest.main()
