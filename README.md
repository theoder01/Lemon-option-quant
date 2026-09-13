Copyright © 2026 Bo Hu. All rights reserved.

Created: September 13, 2026

# Options Quant Research

A quantitative research project for collecting, storing, and analyzing historical U.S. options market data using the Futu OpenAPI.

The primary goal of this project is to build a long-term historical options database and use historical market data to evaluate whether an option premium provides sufficient compensation for its underlying risk.

The initial research focus is on **selling out-of-the-money put options**.

## Project Goals

- Collect historical option chain snapshots
- Build a long-term options database
- Analyze option premiums using historical data
- Analyze implied volatility and option Greeks
- Estimate historical risk and probability distributions
- Evaluate risk/reward of selling put options
- Backtest option-selling strategies

## Data Source

Market data is collected through:

- Futu OpenD
- Futu Python API

## Initial Underlyings

The initial research universe includes:

- NVIDIA (NVDA)
- Alphabet / Google (GOOG / GOOGL)
- IREN (IREN)

Additional underlyings may be added later.

## Option Selection

The initial strategy focuses exclusively on **out-of-the-money put options**.

Options are currently selected using:

```text
0.60 × underlying_price <= strike < underlying_price
```

This removes:

- In-the-money puts
- Extremely deep out-of-the-money puts

All available expiration dates are retained.

## Option Snapshot Data

Each option snapshot currently contains the following 17 fields:

| Field | Description |
|---|---|
| `snapshot_time` | Time when the market snapshot was collected |
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

Derived variables such as moneyness, mid price, bid-ask spread, IV rank, and historical return statistics will be calculated during analysis rather than stored as raw market data.

## Data Collection

The planned collection frequency is:

- Once per U.S. trading day
- During regular market hours
- Target time: approximately **10:30 AM New York time**

The database is intended to accumulate continuously over multiple years.

## Project Roadmap

1. Futu OpenAPI connection
2. Option chain collection
3. Option filtering
4. Historical database
5. Automated daily data collection
6. Options analytics
7. Historical relative-value analysis
8. Sell-put strategy backtesting
9. Statistical and quantitative models

## Disclaimer

This project is intended for quantitative research and educational purposes only. It does not constitute financial or investment advice.
