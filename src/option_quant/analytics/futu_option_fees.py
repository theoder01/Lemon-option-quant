# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 28, 2026

"""Estimated Futu HK fixed-plan fees for one US equity-option order.

Rate snapshot checked September 28, 2026; ORF effective September 1, 2026.
Source: https://www.futuhk.com/hans/support/topic2_283 (section 4).
One order, one execution, one leg; no discounts, index surcharges, assignment,
or tiered plans. Broker per-fill rounding may differ from this raw estimate.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


FEE_SCHEDULE = "Futu HK fixed plan / US equity options / checked 2026-09-28"


@dataclass(frozen=True)
class OptionFeeEstimate:
    commission: Decimal
    platform: Decimal
    option_regulatory: Decimal
    clearing: Decimal
    settlement: Decimal
    audit_trail: Decimal
    sec: Decimal
    trading_activity: Decimal
    schedule: str = FEE_SCHEDULE

    @property
    def total(self) -> Decimal:
        """Unrounded estimate; do not interpret as an exact broker debit."""
        return sum((
            self.commission, self.platform, self.option_regulatory,
            self.clearing, self.settlement, self.audit_trail,
            self.sec, self.trading_activity,
        ), Decimal("0"))


def estimate_futu_option_fees(
    *, premium: float, contracts: int = 1, side: str,
) -> OptionFeeEstimate:
    """USD fees for one order. Premium is per share; each contract is 100 shares.

    Rates are an explicit snapshot, not automatically updated market data.
    Minimum commission applies once per order, not once per contract.
    SEC and trading activity fees apply only to sales. Preserve precision in
    calculations; round only for display. Actual statement fees can override
    this estimate in the annualized-return calculation.
    """
    if isinstance(contracts, bool) or not isinstance(contracts, int) or contracts <= 0:
        raise ValueError("contracts must be a positive integer.")
    if side not in ("buy", "sell"):
        raise ValueError("side must be 'buy' or 'sell'.")
    if isinstance(premium, bool):
        raise ValueError("premium must be finite and nonnegative.")
    try:
        quote = Decimal(str(premium))
    except (InvalidOperation, ValueError) as error:
        raise ValueError("premium must be finite and nonnegative.") from error
    if not quote.is_finite() or quote < 0:
        raise ValueError("premium must be finite and nonnegative.")

    n = Decimal(contracts)
    commission_rate = Decimal("0.15") if quote <= Decimal("0.10") else Decimal("0.65")
    return OptionFeeEstimate(
        commission=max(commission_rate * n, Decimal("1.99")),
        platform=Decimal("0.30") * n,
        option_regulatory=Decimal("0.0122") * n,
        clearing=Decimal("0.025") * n,
        settlement=Decimal("0.18") * n,
        audit_trail=Decimal("0.0003") * n,
        sec=max(Decimal("0.0000206") * quote * 100 * n, Decimal("0.01")) if side == "sell" else Decimal("0"),
        trading_activity=max(Decimal("0.00329") * n, Decimal("0.01")) if side == "sell" else Decimal("0"),
    )
