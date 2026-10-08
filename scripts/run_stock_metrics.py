# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

"""Run daily stock metrics, save them, export the latest dashboard, then exit."""

from contextlib import ExitStack, closing
from pathlib import Path
import sys

# Support direct execution without requiring an editable installation.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(PROJECT_ROOT),
    str(PROJECT_ROOT / "src"),
]

from live_short_put_scanner import config
from live_short_put_scanner.futu_client import (
    FutuClient as ScannerClient,
)

from option_quant.analytics.daily_stock_metrics import (
    DailyRunResult,
    DailyStockMetricsRunner,
    TickerResult,
    print_results,
    runner_time,
)
from option_quant.analytics.daily_stock_metrics_market_data import (
    FutuStockMetricsSource,
)
from option_quant.analytics.stock_metrics_database import (
    StockMetricsDatabase,
)
from option_quant.time_utils import get_trading_date


def create_option_client():
    """Create the Futu option client only when the script actually runs."""

    from option_quant.futu_client import FutuClient

    return FutuClient(
        host=config.FUTU_HOST,
        port=config.FUTU_PORT,
    )


def export_dashboard(expected_trading_date: str) -> bool:
    """
    Export the latest stored Stock Scanner dashboard without opening a GUI.

    Returns True when a dashboard was successfully exported.

    The latest database trading date must match the trading date of the
    current collection run. This prevents accidentally exporting yesterday's
    data when today's Futu run failed before saving anything.
    """

    # This script is intended to run unattended.
    # Use a non-interactive Matplotlib backend before importing pyplot or
    # the chart module.
    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.pyplot as plt

    from option_quant.analytics.stock_metrics_charts import (
        create_stock_scanner_dashboard,
        load_latest_chart_data,
        save_stock_scanner_dashboard,
    )

    figure = None

    try:
        data = load_latest_chart_data()

        if data.empty:
            print()
            print("Dashboard Export")
            print("----------------")
            print("No stored stock metrics available. Dashboard not created.")
            return False

        actual_trading_date = str(
            data.iloc[0]["trading_date"]
        )

        if actual_trading_date != expected_trading_date:
            print()
            print("Dashboard Export")
            print("----------------")
            print(
                "Dashboard not created: latest database trading date "
                f"is {actual_trading_date}, but this run is for "
                f"{expected_trading_date}."
            )
            return False

        figure = create_stock_scanner_dashboard(
            data
        )

        path = save_stock_scanner_dashboard(
            figure,
            data,
        )

        print()
        print("Dashboard Export")
        print("----------------")
        print(
            f"New York trading date: {actual_trading_date}; "
            f"tickers: {len(data)}"
        )
        print(f"Saved: {path}")

        return True

    except Exception as error:
        reason = (
            " ".join(str(error).split())
            or type(error).__name__
        )

        print(
            f"Dashboard export failed: {reason}",
            file=sys.stderr,
        )

        return False

    finally:
        if figure is not None:
            plt.close(figure)


def main() -> int:
    timestamp = runner_time()
    trading_date = str(
        get_trading_date(
            timestamp
        )
    )

    result = None
    resource_error = False

    # -------------------------------------------------
    # 1. Collect and save today's stock metrics.
    # -------------------------------------------------

    try:
        with ExitStack() as resources:

            scanner = resources.enter_context(
                ScannerClient(
                    config.FUTU_HOST,
                    config.FUTU_PORT,
                )
            )

            options = resources.enter_context(
                closing(
                    create_option_client()
                )
            )

            source = FutuStockMetricsSource(
                scanner,
                options,
            )

            result = DailyStockMetricsRunner(
                source,
                StockMetricsDatabase(),
            ).run(
                timestamp
            )

    except Exception as error:
        resource_error = True

        reason = (
            "Run initialization/resource error: "
            + (
                " ".join(
                    str(error).split()
                )
                or type(error).__name__
            )
        )

        if result is None:
            result = DailyRunResult(
                timestamp,
                [
                    TickerResult(
                        ticker,
                        reason=reason,
                    )
                    for ticker in config.UNDERLYINGS
                ],
            )
        else:
            # Cleanup errors must not relabel rows that
            # were already successfully saved.
            print(
                reason,
                file=sys.stderr,
            )

    # -------------------------------------------------
    # 2. Print collection result.
    # -------------------------------------------------

    print(
        "Sources: live spot/options; "
        "Futu overview IV Rank; "
        "latest scanner history IV/HV."
    )

    print_results(
        result
    )

    # -------------------------------------------------
    # 3. Export today's dashboard automatically.
    #
    # No plt.show().
    # No GUI mainloop.
    # Save JPEG and exit.
    # -------------------------------------------------

    dashboard_ok = export_dashboard(
        trading_date
    )

    # -------------------------------------------------
    # 4. Exit status.
    # -------------------------------------------------

    if resource_error:
        return 1

    if result.skipped_tickers:
        return 1

    if not dashboard_ok:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )