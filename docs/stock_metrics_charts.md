# Stored Stock Metrics Charts

From the project root:

```powershell
python scripts/show_stock_metrics_charts.py
```

This automatically saves one landscape Matplotlib dashboard to
`outputs/stock_scanner/YYYYMMDD_stock_scanner_dashboard.jpg` and displays it.
Its two scatter panels use only the rows from the latest stored New York
trading date in `data/stock_metrics.db`. No Futu connection is needed.
The query uses SQLite read-only mode, selects `MAX(trading_date)` and returns all
rows for that date ordered by ticker. Missing files, absent tables and empty
history are reported cleanly without creating a database. Earlier dates are
never mixed into the dashboard; tickers missing on the latest date are not
backfilled. The shared date, ticker count and filename use the same database slice.

- Volatility Premium Map: X = IV − HV (percentage points), Y = IV Rank. Reference
  lines at 0 and 50 delimit the upper-right light-green visual region.
- Drawdown / Skew Sweet Zone Map: X = 30D 25Δ Put-Call Skew (vol points),
  Y = 52W Drawdown (%). A soft green middle is centered on (3.5, 22.5%),
  with the agreed sweet zone at skew 2–5 and drawdown 15–30%. A pale, smooth
  background extends beyond this zone through yellow, orange and red towards
  either extreme. Colors represent display distance from the middle, not
  financial thresholds or scores. Named constants keep the zone easy to change.

Both charts include direct ticker labels, simple collision avoidance, and hover
details for ticker, spot, IV Rank, IV−HV, drawdown and skew. The existing
`assets/branding/logo-128.png` appears once in the overall upper-left header,
at its original aspect ratio and outside the data area. The asset is reused in place.

Automatic saving uses 200 DPI, JPEG quality 95 and a white background. The
output directory is created automatically. Running twice for the same database
date refreshes that date's JPEG. Optional directory override and headless export:

```powershell
python scripts/show_stock_metrics_charts.py --save-dir charts
python scripts/show_stock_metrics_charts.py --save-dir charts --no-show
```

Exports contain date-stamped filenames; hover is available in the interactive GUI
window, not the static JPEG. Headless exports use the Agg backend. Rendering uses
the project's existing Matplotlib library. If it is absent from your environment,
install it before running the command.

No metric formula, daily runner, database schema or duplicate rule is changed.
The backgrounds are display elements only; no score, ranking or recommendation
is calculated. `options.db` is never read or written by this command.
