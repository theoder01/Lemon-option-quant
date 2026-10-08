# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

"""Already-calculated stock selection metrics for one timestamp."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class StockMetrics:
    ticker: str
    snapshot_time: datetime
    spot: float
    iv_rank: float
    iv_hv: float
    drawdown_52w: float
    put_call_skew: float
