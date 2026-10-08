# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 8, 2026

"""Automatically archive one latest-day dashboard, without connecting to Futu."""

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT_ROOT), str(PROJECT_ROOT / "src")]

from option_quant.analytics.stock_metrics_charts import (
    create_stock_scanner_dashboard, load_latest_chart_data, save_stock_scanner_dashboard,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save-dir", type=Path, help="Override the default outputs/stock_scanner directory")
    parser.add_argument("--no-show", action="store_true", help="Save without opening GUI windows")
    args = parser.parse_args(argv)
    figure = None
    try:
        data = load_latest_chart_data()
        if data.empty:
            print("No stored stock metrics available. No charts created.")
            return 0
        if args.no_show:
            import matplotlib
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        figure = create_stock_scanner_dashboard(data)
        print(f"New York trading date: {data.iloc[0]['trading_date']}; tickers: {len(data)}")
        path = save_stock_scanner_dashboard(figure, data, args.save_dir)
        print(f"Saved: {path}")
        if not args.no_show:
            plt.show()
        return 0
    except Exception as error:
        print(f"Cannot display stock metrics charts: {error}", file=sys.stderr)
        return 1
    finally:
        if figure is not None:
            import matplotlib.pyplot as plt
            plt.close(figure)


if __name__ == "__main__":
    raise SystemExit(main())
