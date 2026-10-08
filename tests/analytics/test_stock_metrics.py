# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

from dataclasses import fields
from datetime import datetime, timezone

from option_quant.analytics.stock_metrics import StockMetrics


def test_normal_construction_preserves_all_fields_and_units():
    timestamp = datetime(2026, 10, 8, 15, tzinfo=timezone.utc)
    metrics = StockMetrics("US.NVDA", timestamp, 100.0, 55.5, -5.0, 50.0, 8.0)
    assert metrics.ticker == "US.NVDA"
    assert metrics.snapshot_time == timestamp
    assert (metrics.spot, metrics.iv_rank, metrics.iv_hv, metrics.drawdown_52w,
            metrics.put_call_skew) == (100.0, 55.5, -5.0, 50.0, 8.0)


def test_model_has_exactly_the_required_context_and_four_metrics():
    assert [field.name for field in fields(StockMetrics)] == [
        "ticker", "snapshot_time", "spot", "iv_rank", "iv_hv", "drawdown_52w", "put_call_skew",
    ]
