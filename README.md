Copyright © 2026 Bo Hu. All rights reserved.

Created: September 13, 2026

Updated: September 28, 2026

# Lemon Option Quant

A local research tool for collecting U.S. option snapshots and evaluating cash-secured short puts. Market-data collection uses Futu OpenAPI; the desktop GUI analyzes a user-entered Put against the existing SQLite history without connecting to OpenD or placing orders.

## Current Features

- Daily historical snapshots with OTM Put filtering, validation, duplicate protection, UTC timestamps, and New York trading-date handling.
- Historical comparable selection by moneyness and days to expiration (DTE).
- Normalized premium statistics and percentile; historical IV statistics in the analysis module.
- Initial and remaining-holding-period annualized-return calculations with estimated Futu HK fixed-plan fees.
- A simple Tkinter GUI for **one standard Put**: historical premium percentile, initial annualized return, and supporting data.

## Quick Start

Use Python 3.11 or later in your project environment. Install the project from its root:

```powershell
python -m pip install -e .
```

The project declares `futu-api==10.10.7008` and `pandas`. The desktop window also requires Tkinter, normally included with the standard Windows Python distribution. No additional third-party GUI package is required.

### Open the Put GUI

```powershell
python scripts/launch_put_gui.py
```

The launcher resolves this checkout's source and `data/options.db` relative to its own location. It can also be launched from another working directory using the script's full path.

1. Enter an underlying, such as `IREN` or `US.NVDA`.
2. Click **读取历史参考价与到期日** to load a timestamped historical stock price and known future expiration dates, or enter the values manually.
3. Select an expiration or type `YYYY-MM-DD`.
4. Enter the option premium **per share**, strike, and underlying price. Prefer stock and option quotes from the same valuation time.
5. Click **计算百分位与初始年化**.

The window shows:

| Output | Meaning |
|---|---|
| Historical premium percentile | Relative position of current premium / stock price among comparable historical Put snapshots |
| Initial annualized return | Simple ACT/365 return after estimated opening fees, using full strike collateral |
| Sample coverage | Valid snapshot count, distinct New York dates, and historical date range |
| Supporting values | DTE, moneyness, collateral, gross/net premium, fees, and historical premium-ratio median/range |
| IREN example threshold | Whether initial annualized return is strictly greater than 30%; advisory only |

**Historical reference prices are not live quotes.** The expiration list comes from the database and may not include every currently listed contract. The database is opened read-only. Missing history or missing stock price does not prevent annualized-return calculation; unavailable percentiles are not displayed as zero.

The GUI currently covers opening analysis only. Remaining-holding-period return and the below-20% example threshold are available in the calculation module, not yet in the window. Same-day expiration, adjusted contracts, multiple-contract input, and live quotes are not supported by this first GUI.

See [GUI usage and limitations](docs/put_gui.md).

English is the default GUI language. The **Language** selector switches immediately
between **English** and **简体中文**, including existing result details and warnings,
without changing inputs, recalculating, or writing to the historical database.
The launcher remembers the choice in the ignored `data/gui_preferences.json` file.
English remains the canonical language of the code and analysis messages.

### Collect Historical Data

Start and log in to Futu OpenD with the appropriate market-data access, then run from the project root:

```powershell
python scripts/collect_options.py
```

Connection settings and the collection universe are in [config.py](src/option_quant/config.py):

```python
FUTU_HOST = "127.0.0.1"
FUTU_PORT = 11111
UNDERLYINGS = ["US.NVDA", "US.GOOG", "US.SPCX", "US.IREN"]
```

Collection is manual; approximately 10:30 AM New York time once per U.S. trading day is the intended schedule, not an installed scheduler. Unlike the GUI, this command writes validated snapshots to the database.

## Analysis Conventions

### Historical Premium Percentile

```text
moneyness = strike / underlying_price
premium_ratio = option_premium / underlying_price
percentile = 100 × count(historical premium_ratio < current premium_ratio) / sample_count
```

The GUI uses the same underlying, moneyness within ±0.02 (two percentage points), and DTE within ±5 days. Only snapshots strictly earlier than the current valuation timestamp are eligible. Calls, invalid prices, invalid DTEs, and invalid timestamps are excluded before comparison.

Historical premium uses `last / underlying_price`. Equal values do not contribute to the strict-less-than percentile. Each snapshot row has equal weight; repeated observations across contracts and dates are not independent trades. The window flags fewer than 20 samples or fewer than 5 distinct trading dates as limited coverage. These are informational thresholds, not a statistical confidence guarantee.

The existing collector focuses on OTM Puts, so the GUI does not report percentiles for ITM Puts. A high percentile is not a win probability or a standalone trading recommendation.

### Cash-Secured Put Returns

For `N` standard contracts, `M = 100 × N`, strike `K`, initial per-share premium `P0`, current buyback premium `Pt`, and actual remaining days `D`:

```text
Default collateral = K × M
Initial annualized return = (P0 × M − opening_fee − expiration_fee) / collateral × 365 / initial_D
Remaining annualized return = (Pt × M + closing_fee − expiration_fee) / collateral × 365 / remaining_D
```

Remaining return compares holding to worthless expiry with closing now. The original premium and opening fee cancel from this comparison. The closing fee is added because holding avoids that immediate expense. Worthless-expiry fees default to zero.

Fees default to a **Futu HK fixed-plan US equity-option estimate**, using the rate snapshot checked on September 28, 2026. Minimum commissions and sell-only charges are handled separately. Actual statement fees may override the estimate; broker rounding, execution splits, discounts, and future rate changes may differ.

The GUI uses one contract, full strike collateral, and calendar days from today's New York date. The independent module also supports multiple contracts, timezone-aware timestamps with fractional days, and an explicit net-capital denominator. It rejects nonpositive time to expiration. Returns are simple annualizations, not compounded or guaranteed returns, and assume worthless expiry without assignment.

IREN's configurable example thresholds are initial return **>30%** and remaining return **<20%** to consider closing. Equality does not trigger either condition. No orders are generated.

See [formulas, denominator choices, fees, and examples](docs/put_annualized_return.md). For an offline example:

```powershell
python scripts/analyze_put_return.py
```

## Historical Data

Collection currently keeps Put contracts satisfying:

```text
0.60 × underlying_price <= strike < underlying_price
```

The collector retrieves option chains across available expirations from today to approximately one year ahead. `CollectionService` validates snapshots before storage and reports collected, rejected, saved, and duplicate row counts.

SQLite table `option_snapshots` stores 17 raw fields: snapshot time, underlying, underlying price, option code, expiry, strike, DTE, last, bid, ask, volume, open interest, IV, delta, gamma, vega, and theta. Premium ratios, percentiles, fees, annualized returns, and GUI inputs are calculated in memory rather than added to the historical table.

Timestamps are stored in UTC. Duplicate protection uses underlying + option code + New York trading date. `data/` contains private market data and is excluded from Git. See the [data schema](docs/data_schema.md).

## Project Structure

```text
src/option_quant/
├── analytics/
│   ├── comparable_options.py
│   ├── futu_option_fees.py
│   ├── iv_analysis.py
│   ├── moneyness.py
│   ├── premium_analysis.py
│   ├── put_annualized_return.py
│   └── put_preview.py
├── collection_result.py
├── collection_service.py
├── collector.py
├── config.py
├── database.py
├── filters.py
├── futu_client.py
├── gui_i18n.py
├── gui_strings.py
├── put_gui.py
├── rate_limiter.py
├── retry.py
├── time_utils.py
└── validator.py
scripts/
├── collect_options.py
├── analyze_put_return.py
└── launch_put_gui.py
docs/
├── architecture.md
├── data_schema.md
├── put_annualized_return.md
└── put_gui.md
tests/
```

See [architecture and class diagrams](docs/architecture.md) for the collection and GUI paths.

## Tests

Run the automated suite from the project root:

```powershell
$env:PYTHONPATH = "$PWD/src"
python -B -m pytest -q
```

These cover return formulas, fee estimates, percentile selection, read-only database access, input validation, GUI callbacks, English/Chinese resources, immediate switching, and language preferences. GUI tests need a usable Tk environment and create hidden windows; database tests use temporary databases.

Some older `tests/test_*.py` files are manually runnable examples or integration scripts that require OpenD or an existing historical database. They should not be treated as a fully offline unit-test suite.

## Project Roadmap

### Completed

- Historical collection, filtering, validation, persistence, duplicate protection, rate limiting, and retry.
- Comparable-option selection, historical IV statistics, and normalized premium percentile.
- Initial and remaining cash-secured Put return modules with estimated fees.
- Offline single-Put opening-analysis GUI with historical reference prices and selectable expirations.

### Next Candidates

- Accumulate more historical data and assess sample coverage.
- Add a holding-period view to the GUI using the existing remaining-return module.
- Evaluate historical strategy performance and, later, candidate scanning when justified by the research.

Risk Analysis and Event Analysis remain deferred. The application does not perform automatic trading.

## Disclaimer

This project is intended for quantitative research and educational purposes only. It does not constitute financial or investment advice. Cash-secured Puts can be assigned before expiry, require purchasing shares at the strike, and can lose far more than the premium received.
