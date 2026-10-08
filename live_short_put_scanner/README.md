# Lemon Live Short Put Scanner

Independent real-time scanner foundation for potential Cash-Secured Short Put
environments. Task 01 established Futu OpenD data access and calculations.
Task 02 adds a 13-symbol universe and an interactive matplotlib 3D Opportunity Map:
one snapshot per run, without recommendations, a separate GUI application or storage.
Task 03 supplements the 3D context with three 2D projections and exact-value hover.
Task 04 uses raw VRP as the primary Y axis and makes the common origin explicit.
It does not import `option_quant`, access `options.db`, use the Lemon Option Quant
historical collector, or create a database. All market data comes from Futu.

## Run

From `D:\S\my_quant_project`, use Python 3.11+ with `futu-api`, `pandas` and `matplotlib` installed.
Start and log into OpenD on `127.0.0.1:11111`, with market data permissions, then:

```powershell
python -m live_short_put_scanner.main
python -m pytest --import-mode=importlib -o consider_namespace_packages=true tests/live_short_put_scanner -q
```

The SDK must expose `get_option_underlying_overview` and
`get_option_underlying_his_volatility`. Errors are reported per symbol and cause
a nonzero exit code. The connection is closed on success and exceptions.
The exact independent universe, in table/scan order, is:
NVDA, GOOG, TSLA, SPCX, NBIS, RKLB, IREN, BE, MU, SKHY, SNDK, AAPL, MSFT.
The codes in `config.py` use the `US.` prefix. No symbols are added automatically,
and there is no dependency on the historical collector's universe.

Normal execution scans all 13 symbols, prints the table and requested/successful/
skipped counts with reasons, then opens the map. Drag the matplotlib 3D view to
rotate it and use its toolbar for available navigation/export controls. Close the
window to end the command. OpenD is closed before the blocking chart window opens.
The chart requires a graphical matplotlib backend (for example TkAgg) and a desktop
session. The existing Lemon Option Quant GUI is not changed or used.

An individual API or data failure does not stop the scan. Missing/nonfinite metrics,
negative IV/HV, nonpositive prices, undefined VRP Rank, and ranks outside 0–100 are
reported and skipped, never converted to zero. Valid zero ranks are retained.
Only complete snapshots enter the table and map. If no results are valid, the
summary still prints and no window is opened. Partial scans still show the valid
points and return exit code 1 after the window closes; a complete scan returns 0.
Negative historical IV/HV observations are excluded from the rank sample.

## Data conventions

Task 08 prepares exactly four stock-selection metrics: IV Rank, IV-HV,
52W Drawdown and 25-delta Put-Call Skew. Spot is contextual display data.
No aggregate file, score, option-contract selection or annualized return is added.
Existing charts and VRP Rank context are unchanged by this preparation task.

Reusable metric entry points:

- `normalize_official_iv_rank(value)` in `calculations.py`: a deterministic adapter
  for the Futu overview's official `iv_rank`, using the existing finite/missing
  value policy. This is the only IV Rank source. There is no local historical IV
  Rank formula. A flat or short local history does not override an available
  official rank; missing official values stay unavailable. An empty historical
  dataset still raises the existing snapshot data error. Snapshot range checks
  remain separate. Provider formula validation requires provider documentation
  or reference data; synthetic unit tests only verify faithful value handling.
- `calculate_vrp(iv, hv)`: reused for IV-HV, with signed percentage-point output.
- `calculate_high_52w_close(prices)` and `calculate_distance_from_high(price, high)`:
  reused for raw percentage drawdown. Above-high prices retain negative drawdown;
  nonpositive/invalid highs produce unavailable values.
- `option_quant.analytics.skew.calculate_25delta_skew(...)`: the existing pure
  group-level 25-delta PUT IV minus CALL IV calculation. Its algorithm and tests
  remain unchanged. This documents the future aggregator's available entry point;
  the scanner does not import or integrate skew in Task 08.

- Price, IV and HV come from the same newest historical observation, selected by
  parsed `time`, regardless of API row order. The observation time is displayed.
  These are not promised to be streaming quotes. Missing newest values stay
  unavailable; older or overview values are not silently substituted.
- Official IV Rank comes directly from the current Futu overview, whose update
  time can differ from the historical observation. It is not locally reproduced.
- VRP = IV - HV, in percentage points. Historical VRPs use paired observations.
- VRP Rank = (current VRP - historical minimum) / historical range * 100,
  clipped to 0–100. Invalid pairs are ignored; empty or constant history gives
  `None`, displayed as `N/A`. Nonfinite values never propagate as numeric results.
- Historical requests cover 365 calendar days through today and fetch every page
  until the key is `None`. API failures reject partial results. Invalid dates and
  records outside the requested window are excluded. Short listing histories
  use the available observations, which may cover less than a year.
- 52-week highest close is the maximum positive `underlying_price`, not an
  intraday high. The installed SDK describes past values as closes and the
  current day as a mark price, so today's observation may still change.
  A future task may replace this approximation with historical K-line highs.
- 52W Drawdown = (highest close - current price) / highest close * 100. Missing or
  nonpositive prices yield `N/A`. A price above a supplied high yields a negative
  drawdown. No artificial opportunity score is calculated.

## Task 04: raw VRP and coordinate readability

One matplotlib figure contains four coordinated views of the same raw coordinates:

- 3D Opportunity Map: X=IV Rank, Y=VRP, Z=52W Drawdown. Transparent planes mark
  X=50 and Y=0. Three arrows start at the true O=(0,0,0), labeled X, Y and Z;
  a dotted extension shows the negative VRP direction. The origin is inside the
  plotted ranges and is not assumed to be the bounding box's minimum corner.
- IV Rank × VRP: the primary 2D view, divided by IV Rank=50 and VRP=0.
  A prominent zero line and subtle gray non-positive region expose the premium's sign.
- IV Rank × 52W Drawdown and VRP × 52W Drawdown separate the decline dimension
  from each primary volatility coordinate, without perspective ambiguity.

IV Rank=50 is only a neutral historical midpoint guide, not a hard strategy rule.
VRP=0 has a different meaning: above it IV > HV; at it IV = HV; below it IV < HV.
VRP <= 0 means no positive volatility premium under this definition and **Stand Down**
for the current Short Put workflow. Positive VRP is only a necessary first-stage
condition, not an automatic Sell recommendation. Non-positive points remain visible;
they are not removed from the scan. There is no Z decision plane or drawdown Sweet Spot.
The two 3D planes define regions, not eight octants; quadrants refer to the 2D view.

Each view retains short ticker labels and identical raw values. Small text offsets
and leader lines improve readability in the 2D views without moving stock points.
Hover near a point in any view for its ticker, price, IV, HV, IV Rank, signed raw
VRP, VRP Rank and 52W Drawdown. Raw VRP is in percentage points (pp).
The 3D hover follows the current rotation and hides while dragging or leaving points.
This uses matplotlib's own mouse events, with no additional hover dependency.
When points overlap exactly, the nearest-point hover selects one; the other views
and terminal table remain available for identifying the observations.

The four views show projections rather than four separate models. Coordinates are
not normalized or re-ranked within the 13-symbol universe.

## Three primary dimensions

X = IV Rank: implied volatility relative to the underlying's own historical range.
Y = VRP (IV - HV): the signed volatility premium in percentage points.
Z = 52W Drawdown (%): decline from the 52-week high close.

For example, a 52-week high of 76 and a current price of 38 gives 50% 52W Drawdown.
0% means at the high; 10%, 30% and 50% mean that percentage below the high.
Higher 52W Drawdown means a deeper decline, not automatically a better Short Put
opportunity. A moderate drawdown may offer a more attractive entry level, while
an extreme drawdown may indicate fundamental distress. No drawdown Sweet Spot
threshold is defined. The source, historical window and calculation are unchanged.
Internally, the single metric is named `drawdown_from_52w_high`, calculated by
`calculate_distance_from_high`; no duplicate metric is maintained.

VRP Rank remains calculated and available in snapshots, terminal output and hover
as secondary context: where does today's VRP sit in this stock's own historical
range? Raw VRP instead answers whether the premium is positive and how large it is.
A negative VRP can still have a high VRP Rank, which is why raw VRP replaced it on
the primary axis. Both formulas are unchanged; no new VRP calculation is introduced.

X spans 0–100. Raw VRP and drawdown axes span all observed values plus zero with
padding, including negative values; neither is forced to 0–100. Every valid snapshot has one neutral
blue point labeled with its short ticker. The chart consumes snapshots only and
never queries Futu or computes financial metrics. No composite score is used.
No Sweet Spot has been defined. No trade recommendation is generated.

These independent dimensions may identify interesting Short Put environments.
They are not assumed to be linearly "the higher the better": a large decline
may indicate distress. Apart from the explicit VRP<=0 stand-down boundary, no
strategy thresholds, weights, stock ranking or Buy/Sell labels are implemented.

Future tasks may add a larger stock universe, screening regions,
option-chain scanning, DTE/moneyness/Delta filters, premium analysis, annualized
return and Short Put candidate selection. Tests require no OpenD connection.
