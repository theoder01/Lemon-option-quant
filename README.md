Copyright © 2026 Bo Hu. All rights reserved.

Created: September 13, 2026

Updated: September 28, 2026

# Lemon Option Quant

A local research tool for collecting U.S. option snapshots and evaluating cash-secured short puts. Market-data collection uses Futu OpenAPI; the desktop GUI analyzes a user-entered Put against the existing SQLite history without connecting to OpenD or placing orders.

## Current Features

- Daily historical snapshots with OTM Put filtering, validation, duplicate protection, UTC timestamps, and New York trading-date handling.
- Historical comparable selection by moneyness and days to expiration (DTE).
- Normalized premium statistics and percentile; historical IV percentile and descriptive statistics.
- Initial and remaining-holding-period annualized-return calculations with estimated Futu HK fixed-plan fees.
- A simple Tkinter GUI for **one standard Put**: historical premium percentile, initial annualized return, reference-only historical IV percentile, and supporting data.

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
2. Click **Load Historical Price and Expirations** to load a timestamped historical stock price and known future expiration dates, or enter the values manually.
3. Select an expiration from the historical dropdown, use the adjacent **Calendar** button, or type `YYYY-MM-DD`.
4. Enter the option premium **per share**, strike, and underlying price. Prefer stock and option quotes from the same valuation time.
5. Click **Calculate Percentile and Initial Annualized Return**.

Numeric fields allow normal Backspace/Delete, Ctrl+A selection and copy/paste,
including empty or partial values while editing. Final numeric validation runs
when calculating. The calendar preserves ISO dates and existing expiration rules;
it introduces no dependency or calculation change.

The window shows:

| Output | Meaning |
|---|---|
| Historical premium percentile | Relative position of current premium / stock price among comparable historical Put snapshots |
| Initial annualized return | Simple ACT/365 return after estimated opening fees, using full strike collateral |
| Historical IV percentile | Latest stored IV for the exact Put versus valid prior premium-comparable observations; reference only, not a trading signal |
| Sample coverage | Valid snapshot count, distinct New York dates, and historical date range |
| Supporting values | DTE, moneyness, collateral, gross/net premium, fees, and historical premium-ratio median/range |

**Historical reference prices are not live quotes.** The expiration list comes from the database and may not include every currently listed contract. The database is opened read-only. Missing history or missing stock price does not prevent annualized-return calculation; unavailable percentiles are not displayed as zero.

IV is matched by underlying, Put type, expiration, and exact strike, with its source
contract and timestamp shown in the details. It is not inferred from the entered
premium. IV peers reuse the premium peer set but must precede the stored IV
timestamp, so IV and premium sample counts can differ. The existing IV analyzer
uses a strict-below percentile and accepts any nonempty valid set; zero valid
prior observations show **Insufficient historical IV data**, while fewer than
20 snapshots or 5 trading dates show a limited-coverage warning. No IV score,
entry threshold, or buy/sell recommendation is introduced.

The same window has **New Position** and **Existing Position** tabs. Switching tabs preserves each page's inputs and results. Existing Position accepts underlying, expiration, strike per share, current executable buyback premium per share (normally Ask), positive integer contracts (default 1), and current underlying price per share. Its three cards show remaining annualized return, remaining potential profit, and gross collateral. Details include buyback cost, avoided buy-to-close fee and source, period return, and OTM/ATM/ITM with strike/spot moneyness. Spot is context only and never enters the remaining-return calculation. Existing Position does not load historical percentiles or ask for opening cash flows. Both pages share immediate English/Chinese switching, numeric editing, and the date picker. Same-day expiration, adjusted contracts, and live quotes are not supported; New Position still uses one contract.

Both tabs share a light workbench layout, with inputs beside results on wide windows and stacked on smaller windows. The header contains the language selector; calculation details group capital, fees, returns, and reference information. Styling does not encode trade recommendations.

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
Gross collateral = K × M
Initial annualized return = (P0 × M − opening_fee) / collateral × 365 / initial_D
Remaining annualized return = (Pt × M + closing_fee) / collateral × 365 / remaining_D
```

Remaining return compares holding to worthless expiry with closing now. The original premium and opening fee cancel from this comparison. The closing fee is added because holding avoids that immediate expense. Worthless expiration requires no transaction and incurs no transaction fee.

Fees default to a **Futu HK fixed-plan US equity-option estimate**, using the rate snapshot checked on September 28, 2026. Minimum commissions and sell-only charges are handled separately. Actual statement fees may override the estimate; broker rounding, execution splits, discounts, and future rate changes may differ.

New Position uses one contract; Existing Position accepts a positive integer contract count. Both use full strike collateral and calendar days from today's New York date. The independent module also supports multiple contracts and timezone-aware timestamps with fractional days. It rejects nonpositive time to expiration. Returns are simple annualizations, not compounded or guaranteed returns, and assume worthless expiry without assignment.

The analytics layer returns objective values only and makes no open, hold, or close recommendations.

See [formulas, collateral, fees, and examples](docs/put_annualized_return.md). For an offline example:

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
├── date_picker.py
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
- One offline GUI with New Position historical analysis and Existing Position remaining-return analysis.

### Next Candidates

- Accumulate more historical data and assess sample coverage.
- Evaluate historical strategy performance and, later, candidate scanning when justified by the research.

Risk Analysis and Event Analysis remain deferred. The application does not perform automatic trading.

## Disclaimer

This project is intended for quantitative research and educational purposes only. It does not constitute financial or investment advice. Cash-secured Puts can be assigned before expiry, require purchasing shares at the strike, and can lose far more than the premium received.

## Local Windows executable

See [Windows build instructions](docs/windows-build.md) for the reproducible PyInstaller onedir build and runtime database paths.
