# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 28, 2026

"""Cash-secured standard equity puts: conditional, simple ACT/365 returns.

Quotes are per share; fees are totals for the entire position in the same
currency. Only unadjusted 100-share contracts are supported. No market data,
broker connection, probability forecast, or order placement is involved.
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
import math

from option_quant.analytics.futu_option_fees import (
    OptionFeeEstimate,
    estimate_futu_option_fees,
)


SHARES_PER_CONTRACT = 100
RISK_NOTICE = (
    "Conditional on expiration without value or assignment; not a guaranteed "
    "or expected return. Early assignment is possible. Assignment requires "
    "buying 100 shares per contract at the strike; subsequent stock losses "
    "can far exceed the premium. High annualized return is not a safety signal."
)


class CapitalBasis(str, Enum):
    """GROSS_COLLATERAL is the default and recommended comparison convention.

    NET_CAPITAL means external cash at opening, or cash available after
    closing during holding. It is not a broker margin requirement.
    """

    GROSS_COLLATERAL = "gross_collateral"
    NET_CAPITAL = "net_capital"


@dataclass(frozen=True)
class PutAnnualizedReturnResult:
    phase: str
    remaining_days: float
    contracts: int
    gross_collateral: float
    capital_basis: CapitalBasis
    capital: float
    potential_profit: float
    period_return: float
    annualized_return: float
    risk_notice: str = RISK_NOTICE
    transaction_fee: float = 0.0
    fee_estimate: OptionFeeEstimate | None = None
    fee_source: str = "manual"


def _number(name: str, value: float, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number.")
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a finite number.") from error
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}.")
    return value


def actual_remaining_days(as_of: date, expiration: date) -> float:
    """Calendar days for dates; exact elapsed days for aware datetimes.

    Datetimes are normalized to UTC (including across daylight-saving changes).
    Pass the contract's actual expiration cutoff, not a guessed midnight.
    Mixed dates/datetimes, naive datetimes, and expired contracts are rejected.
    """
    if isinstance(as_of, datetime) and isinstance(expiration, datetime):
        if as_of.utcoffset() is None or expiration.utcoffset() is None:
            raise ValueError("Datetimes must be timezone-aware.")
        days = (expiration.astimezone(timezone.utc) - as_of.astimezone(timezone.utc)).total_seconds() / 86400
    elif type(as_of) is date and type(expiration) is date:
        days = (expiration - as_of).days
    else:
        raise ValueError("Use two dates or two timezone-aware datetimes.")
    return _number("remaining_days", days, positive=True)


def _calculate(
    *, phase: str, strike: float, contracts: int, as_of: date,
    expiration: date, cash_flow: float, expiration_fee: float,
    capital_basis: CapitalBasis,
    transaction_fee: float,
    fee_estimate: OptionFeeEstimate | None,
) -> PutAnnualizedReturnResult:
    strike = _number("strike", strike, positive=True)
    if isinstance(contracts, bool) or not isinstance(contracts, int) or contracts <= 0:
        raise ValueError("contracts must be a positive integer.")
    basis = CapitalBasis(capital_basis)
    days = actual_remaining_days(as_of, expiration)
    collateral = _number("gross_collateral", strike * SHARES_PER_CONTRACT * contracts, positive=True)
    capital = collateral if basis == CapitalBasis.GROSS_COLLATERAL else collateral - cash_flow
    capital = _number("capital", capital, positive=True)
    profit = cash_flow - _number("expiration_fee", expiration_fee)
    period_return = profit / capital
    annualized_return = period_return * 365 / days
    if not all(math.isfinite(v) for v in (profit, period_return, annualized_return)):
        raise ValueError("Calculated values must be finite.")
    return PutAnnualizedReturnResult(
        phase, days, contracts, collateral, basis, capital,
        profit, period_return, annualized_return,
        transaction_fee=transaction_fee,
        fee_estimate=fee_estimate,
        fee_source=fee_estimate.schedule if fee_estimate else "manual",
    )


def calculate_initial_annualized_return(
    *, strike: float, premium: float, as_of: date, expiration: date,
    contracts: int = 1, opening_fee: float | None = None,
    expiration_fee: float = 0.0,
    capital_basis: CapitalBasis = CapitalBasis.GROSS_COLLATERAL,
) -> PutAnnualizedReturnResult:
    """Opening credit minus opening/expiration fees, assuming worthless expiry.

    opening_fee=None estimates Futu HK fixed-plan sell-order fees. Supply a
    total fee to override (0 explicitly disables fees); details are returned.
    Gross basis: K * 100 * N.
    Net basis: K * 100 * N - (premium * 100 * N - opening_fee).
    expiration_fee is only the estimated cost of worthless expiry, not an
    assignment fee. An executable sell quote is preferable to a stale last.
    """
    premium = _number("premium", premium)
    fee_estimate = (
        estimate_futu_option_fees(premium=premium, contracts=contracts, side="sell")
        if opening_fee is None else None
    )
    opening_fee = _number(
        "opening_fee", float(fee_estimate.total) if fee_estimate else opening_fee,
    )
    if isinstance(contracts, bool) or not isinstance(contracts, int) or contracts <= 0:
        raise ValueError("contracts must be a positive integer.")
    return _calculate(
        phase="initial", strike=strike, contracts=contracts, as_of=as_of,
        expiration=expiration, cash_flow=premium * SHARES_PER_CONTRACT * contracts - opening_fee,
        expiration_fee=expiration_fee, capital_basis=capital_basis,
        transaction_fee=opening_fee, fee_estimate=fee_estimate,
    )


def calculate_remaining_annualized_return(
    *, strike: float, close_premium: float, as_of: date, expiration: date,
    contracts: int = 1, closing_fee: float | None = None,
    expiration_fee: float = 0.0,
    capital_basis: CapitalBasis = CapitalBasis.GROSS_COLLATERAL,
) -> PutAnnualizedReturnResult:
    """Incremental gain from holding versus paying to close immediately.

    closing_fee=None estimates Futu HK fixed-plan buy-order fees. Supply a
    total fee to override (0 explicitly disables fees); details are returned.
    Potential gain = close_premium * 100 * N + closing_fee - expiration_fee.
    The closing fee is ADDED: holding to worthless expiry avoids paying it.
    Opening credit and opening fees are sunk and deliberately absent.
    Net capital = gross collateral - (buyback cost + closing_fee), i.e. cash
    available if closed now. Gross capital remains the default for stability.
    Use an executable buyback quote (usually ask), not profit earned so far.
    """
    close_premium = _number("close_premium", close_premium)
    fee_estimate = (
        estimate_futu_option_fees(premium=close_premium, contracts=contracts, side="buy")
        if closing_fee is None else None
    )
    closing_fee = _number(
        "closing_fee", float(fee_estimate.total) if fee_estimate else closing_fee,
    )
    if isinstance(contracts, bool) or not isinstance(contracts, int) or contracts <= 0:
        raise ValueError("contracts must be a positive integer.")
    return _calculate(
        phase="remaining", strike=strike, contracts=contracts, as_of=as_of,
        expiration=expiration, cash_flow=close_premium * SHARES_PER_CONTRACT * contracts + closing_fee,
        expiration_fee=expiration_fee, capital_basis=capital_basis,
        transaction_fee=closing_fee, fee_estimate=fee_estimate,
    )


@dataclass(frozen=True)
class YieldThresholds:
    """Decimal rates: 0.30 means 30%. Strict comparisons; advisory only."""

    open_above: float = 0.30
    consider_close_below: float = 0.20

    def __post_init__(self) -> None:
        object.__setattr__(self, "open_above", _number("open_above", self.open_above))
        object.__setattr__(self, "consider_close_below", _number("consider_close_below", self.consider_close_below))

    def evaluate(self, result: PutAnnualizedReturnResult) -> str:
        if not math.isfinite(result.annualized_return):
            raise ValueError("annualized_return must be finite.")
        if result.phase == "initial":
            return "entry_yield_met" if result.annualized_return > self.open_above else "entry_yield_not_met"
        if result.phase == "remaining":
            return "consider_closing" if result.annualized_return < self.consider_close_below else "closing_yield_not_triggered"
        raise ValueError("Unknown calculation phase.")
