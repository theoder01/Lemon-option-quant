Copyright © 2026 Bo Hu. All rights reserved.

Created: September 13, 2026

# Option Snapshot Data Schema

Historical snapshots of out-of-the-money U.S. put options.

## Collection Rules

Only Put options are collected.

Strike range:

0.60 × underlying_price <= strike < underlying_price

All available expiration dates are retained.

Planned collection time: approximately 10:30 AM America/New_York.

## Data Fields

| Field | Description |
|---|---|
| snapshot_time | Time when the snapshot was collected |
| underlying | Underlying code, e.g. US.NVDA |
| underlying_price | Underlying market price |
| option_code | Futu option contract code |
| expiry | Expiration date |
| strike | Strike price |
| dte | Days to expiration |
| last | Last traded option price |
| bid | Best bid price |
| ask | Best ask price |
| volume | Daily trading volume |
| open_interest | Open interest |
| iv | Implied volatility (%) |
| delta | Option Delta |
| gamma | Option Gamma |
| vega | Option Vega |
| theta | Option Theta |

## Notes

- IV is stored in the original Futu scale. For example, 36.82 means 36.82%.
- Last price is retained as reference data; Bid/Ask are preferred for executable-price analysis.
- Derived values such as moneyness, mid price and bid-ask spread are calculated during analysis and are not stored as raw data.
- Raw market data in the `data/` directory is private and excluded from Git.