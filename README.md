Copyright © 2026 Bo Hu. All rights reserved.

Created: September 13, 2026

# Options Quant Research

A quantitative research project for collecting, storing, and analyzing historical U.S. options market data using the Futu OpenAPI.

The project has two core objectives:

1. Build a long-term historical options database from daily option snapshots.
2. Develop an options analysis and strategy framework for evaluating and selecting put options using historical market data.

The initial research focus is on **selling out-of-the-money put options**.

## Core Objectives

### 1. Historical Options Database

Historical option snapshots are collected and stored locally because complete historical option-chain snapshots cannot be reconstructed later through the Futu OpenAPI.

The database is intended to accumulate continuously over time and provide the foundation for quantitative research.

The collection pipeline currently includes:

- Futu OpenAPI data collection
- Full option-chain retrieval across available expirations
- Put option filtering
- Data validation and cleaning
- Duplicate protection
- UTC and New York trading-date handling
- API rate limiting and retry handling
- SQLite persistence

### 2. Option Analysis and Strategy

Historical data is used to evaluate current option opportunities.

The analysis framework currently supports:

- Moneyness calculation
- Historical comparable-option selection
- Implied volatility comparison
- Normalized option-premium comparison

Comparable options are selected using similar:

- Moneyness
- Days to expiration (DTE)

The long-term goal is to develop a quantitative strategy that can be used in two ways:

- Analyze a specific option selected by the user
- Scan current option chains and identify options that satisfy the strategy

The same strategy framework can later be evaluated using historical backtesting.

## Data Source

Market data is collected through:

- Futu OpenD
- Futu Python API

## Initial Underlyings

The current research universe includes:

- NVIDIA (NVDA)
- Alphabet / Google (GOOG)
- SpaceX (SPCX)

Additional underlyings may be added later.

## Option Selection

The current data collection focuses exclusively on **out-of-the-money put options**.

Options are filtered using:

```text
0.60 × underlying_price <= strike < underlying_price
```

This removes:

- In-the-money puts
- Extremely deep out-of-the-money puts

Available expiration dates up to approximately one year are retained.

## Option Snapshot Data

Each option snapshot currently contains the following 17 fields:

| Field | Description |
|---|---|
| `snapshot_time` | UTC time when the market snapshot was collected |
| `underlying` | Underlying symbol |
| `underlying_price` | Underlying market price at snapshot time |
| `option_code` | Unique option contract code |
| `expiry` | Option expiration date |
| `strike` | Strike price |
| `dte` | Days to expiration |
| `last` | Last traded option price |
| `bid` | Best bid price |
| `ask` | Best ask price |
| `volume` | Daily trading volume |
| `open_interest` | Open interest |
| `iv` | Implied volatility |
| `delta` | Option Delta |
| `gamma` | Option Gamma |
| `vega` | Option Vega |
| `theta` | Option Theta |

Derived variables are calculated during analysis rather than stored as raw market data.

Examples include:

- Moneyness
- Normalized premium
- Historical comparable-option statistics
- Historical IV statistics

## Historical Comparable Analysis

For a current option, moneyness is defined as:

```text
moneyness = strike / underlying_price
```

Historical options with similar moneyness and DTE can then be selected from the database.

For example:

```text
Current option:

Underlying: NVDA
Spot:       $222.27
Strike:     $190
Moneyness:  85.48%
DTE:        30
```

The analysis searches the historical database for options with approximately similar moneyness and time to expiration.

These comparable samples can then be used to evaluate the current option relative to historical observations.

## IV Analysis

The current implied volatility can be compared with historical comparable options.

The analysis currently calculates:

- Sample count
- Mean IV
- Median IV
- Minimum IV
- Maximum IV

More advanced relative-value statistics may be added as the historical dataset grows.

## Premium Analysis

Raw option premiums are not directly comparable when the underlying price changes.

Premium is therefore normalized as:

```text
premium_ratio = option_premium / underlying_price
```

The current premium ratio can then be compared with historical comparable options.

The analysis currently calculates:

- Sample count
- Mean premium ratio
- Median premium ratio
- Minimum premium ratio
- Maximum premium ratio

## Data Collection

Option snapshots are collected manually approximately once per U.S. trading day while the market is open.

The intended collection time is approximately:

```text
10:30 AM New York time
```

Missing an occasional trading day is acceptable.

The primary objective is to build a long-term dataset over months and years rather than reproduce every intraday market movement.

## Project Structure

```text
src/option_quant/
├── analytics/
│   ├── moneyness.py
│   ├── comparable_options.py
│   ├── iv_analysis.py
│   └── premium_analysis.py
├── collection_result.py
├── collection_service.py
├── collector.py
├── config.py
├── database.py
├── filters.py
├── futu_client.py
├── rate_limiter.py
├── retry.py
├── time_utils.py
└── validator.py

scripts/
└── collect_options.py

tests/
```

## Project Roadmap

### Completed

- Futu OpenAPI connection
- Full option-chain collection
- OTM put filtering
- SQLite historical database
- Duplicate protection
- UTC / New York trading-date handling
- API rate limiting and retry
- Data validation and cleaning
- Structured collection service
- Historical comparable-option analysis
- IV analysis
- Normalized premium analysis

### Research in Progress

- Historical relative-value analysis
- Development of option-selection metrics
- Development of a quantitative sell-put strategy

### Future

- Strategy validation using historical backtesting
- Automatic scanning for options matching the strategy
- Analysis of user-selected options
- Optional graphical user interface

## Disclaimer

This project is intended for quantitative research and educational purposes only. It does not constitute financial or investment advice.