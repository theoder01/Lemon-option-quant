# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 28, 2026

"""Offline example only. All quotes below are hypothetical, not live IREN data."""

from datetime import date

from option_quant.analytics.put_annualized_return import (
    YieldThresholds,
    calculate_initial_annualized_return,
    calculate_remaining_annualized_return,
)


# Example configuration, not an investment recommendation or trading rule.
THRESHOLDS_BY_UNDERLYING = {
    'US.IREN': YieldThresholds(open_above=0.30, consider_close_below=0.20),
}


def main():
    thresholds = THRESHOLDS_BY_UNDERLYING['US.IREN']
    initial = calculate_initial_annualized_return(
        strike=50, premium=2, contracts=1,
        as_of=date(2026, 9, 28), expiration=date(2026, 10, 28),
    )
    remaining = calculate_remaining_annualized_return(
        strike=50, close_premium=0.30, contracts=1,
        as_of=date(2026, 10, 14), expiration=date(2026, 10, 28),
    )
    print('US.IREN - hypothetical offline example; no orders placed')
    for result in (initial, remaining):
        print(f'\n{result.phase}: {result.annualized_return:.2%} simple annualized')
        print(f'Days remaining: {result.remaining_days:g}')
        print(f'Capital: ${result.capital:,.2f} ({result.capital_basis.value})')
        print(f'Conditional potential profit: ${result.potential_profit:,.2f}')
        print(f'Estimated transaction fee: ${result.transaction_fee:.2f} ({result.fee_source})')
        print(f'Yield-only assessment: {thresholds.evaluate(result)}')
    print(f'\n{initial.risk_notice}')


if __name__ == '__main__':
    main()
