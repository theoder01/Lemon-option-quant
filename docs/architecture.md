Copyright © 2026 Bo Hu. All rights reserved.

Created: September 13, 2026

# Architecture

## Data Collection Pipeline

python scripts/collect_options.py
              │
              ▼
            main()
              │
              ├──────────────► FutuClient
              │                  │
              │                  ├─ get_last_price()
              │                  ├─ get_option_expiration_dates()
              │                  ├─ get_option_chain()
              │                  └─ get_market_snapshot()
              │
              ▼
   collect_option_snapshot()
              │
              ├─ _get_full_option_chain()
              │        │
              │        └─ FutuClient.get_option_chain()
              │
              ├─ filter_otm_puts()
              │
              ├─ _get_option_snapshots()
              │        │
              │        └─ FutuClient.get_market_snapshot()
              │
              ▼
      17-column DataFrame
              │
              ▼
      OptionDatabase
              │
              └─ save_snapshots()
                     │
                     ▼
              data/options.db

## Class Diagram

+------------------------------------------------+
|                  FutuClient                    |
+------------------------------------------------+
| - host: str                                    |
| - port: int                                    |
| - quote_ctx                                    |
+------------------------------------------------+
| + __init__(host, port)                         |
| + close()                                      |
| + get_market_snapshot(codes)                   |
| + get_option_chain(code, start=None, end=None) |
| + get_option_expiration_dates(code)            |
| + get_last_price(code) -> float                |
+------------------------------------------------+


+------------------------------------------------+
|               OptionDatabase                   |
+------------------------------------------------+
| - database_path: Path                          |
+------------------------------------------------+
| + __init__(database_path)                      |
| - _connect()                                   |
| + save_snapshots(df)                           |
| + load_all() -> DataFrame                      |
| + load_underlying(symbol) -> DataFrame         |
+------------------------------------------------+

## Method Structure

main()
│
├─ FutuClient(...)
│
├─ collect_option_snapshot("US.NVDA")
│     │
│     ├─ get_last_price()
│     │      └─ 218.29
│     │
│     ├─ get_option_expiration_dates()
│     │      └─ 2026-09 ... 2027-06
│     │
│     ├─ _get_full_option_chain()
│     │      └─ 1586 Put contracts
│     │
│     ├─ filter_otm_puts()
│     │      └─ 0.60*S <= K < S
│     │      └─ 403 contracts
│     │
│     ├─ _get_option_snapshots()
│     │      └─ bid / ask / IV / Greeks / OI...
│     │
│     └─ DataFrame[403 x 17]
│
├─ OptionDatabase.save_snapshots()
│
└─ data/options.db
