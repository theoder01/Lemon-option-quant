# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 28, 2026

from decimal import Decimal
import unittest

from option_quant.analytics.futu_option_fees import estimate_futu_option_fees


class FutuOptionFeeTests(unittest.TestCase):
    def test_one_contract_sell_fee_components(self):
        fee = estimate_futu_option_fees(premium=2, side='sell')
        expected = dict(
            commission='1.99', platform='0.30', option_regulatory='0.0122',
            clearing='0.025', settlement='0.18', audit_trail='0.0003',
            sec='0.01', trading_activity='0.01', total='2.5275',
        )
        for name, value in expected.items():
            self.assertEqual(getattr(fee, name), Decimal(value))

    def test_buy_does_not_pay_sell_only_fees(self):
        fee = estimate_futu_option_fees(premium=0.30, side='buy')
        self.assertEqual(fee.sec, 0)
        self.assertEqual(fee.trading_activity, 0)
        self.assertEqual(fee.total, Decimal('2.5075'))

    def test_low_premium_boundary(self):
        for premium, commission in [('0.0999', '3'), ('0.10', '3'), ('0.1001', '13')]:
            fee = estimate_futu_option_fees(premium=premium, contracts=20, side='buy')
            self.assertEqual(fee.commission, Decimal(commission))
        self.assertEqual(estimate_futu_option_fees(premium=0.10, side='buy').commission, Decimal('1.99'))

    def test_order_minimum_not_per_contract(self):
        combined = estimate_futu_option_fees(premium=2, contracts=4, side='buy')
        single = estimate_futu_option_fees(premium=2, side='buy')
        self.assertEqual(combined.commission, Decimal('2.60'))
        self.assertLess(combined.total, single.total * 4)

    def test_ad_valorem_and_per_contract_charges(self):
        fee = estimate_futu_option_fees(premium=20, contracts=10, side='sell')
        self.assertEqual(fee.sec, Decimal('0.412'))
        self.assertEqual(fee.trading_activity, Decimal('0.03290'))
        self.assertEqual(fee.platform, Decimal('3'))

    def test_zero_quote_still_has_order_minimum(self):
        fee = estimate_futu_option_fees(premium=0, side='buy')
        self.assertEqual(fee.total, Decimal('2.5075'))

    def test_invalid_input(self):
        for value in [None, True, -1, float('inf'), float('nan'), 'invalid']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                estimate_futu_option_fees(premium=value, side='buy')
        for count in [0, -1, 1.5, True, '2']:
            with self.subTest(count=count), self.assertRaises(ValueError):
                estimate_futu_option_fees(premium=1, contracts=count, side='buy')
        with self.assertRaises(ValueError):
            estimate_futu_option_fees(premium=1, side='invalid')


if __name__ == '__main__':
    unittest.main()
