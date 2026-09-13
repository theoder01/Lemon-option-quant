Copyright © 2026 Bo Hu. All rights reserved.

Created: September 13, 2026

# Architecture

This document describes the software architecture and data collection flow of the Lemon Option Quant project.

The system collects historical snapshots of U.S. put options through Futu OpenAPI and stores the processed data in a local SQLite database.

---

## Project Structure

```text
Lemon-option-quant/
│
├── README.md
├── pyproject.toml
├── requirements.txt
├── .gitignore
│
├── docs/
│   ├── architecture.md
│   └── data_schema.md
│
├── scripts/
│   ├── collect_options.py
│   └── test_connection.py
│
├── src/
│   └── option_quant/
│       ├── __init__.py
│       ├── config.py
│       ├── futu_client.py
│       ├── filters.py
│       ├── collector.py
│       └── database.py
│
└── data/
    └── options.db
```

The `data/` directory contains private market data and is excluded from Git through `.gitignore`.

---

## Class Diagram

```mermaid
classDiagram

    class FutuClient {
        -host
        -port
        -quote_ctx
        +__init__(host, port)
        +close()
        +get_last_price(code)
        +get_option_expiration_dates(code)
        +get_option_chain(code, start, end)
        +get_market_snapshot(codes)
    }

    class Collector {
        <<module>>
        +_get_full_option_chain(client, underlying)
        +_get_option_snapshots(client, option_codes)
        +collect_option_snapshot(client, underlying)
    }

    class Filters {
        <<module>>
        +filter_otm_puts(option_chain, underlying_price, min_strike_ratio)
    }

    class OptionDatabase {
        -database_path
        +__init__(database_path)
        -_connect()
        +save_snapshots(df)
        +load_all()
        +load_underlying(underlying)
    }

    Collector --> FutuClient : requests market data
    Collector --> Filters : filters option chain
    Collector --> OptionDatabase : snapshot output
```

---

## Data Collection Flow

```mermaid
flowchart TD

    A[collect_options.py] --> B[Create FutuClient]
    A --> C[Create OptionDatabase]

    B --> D[collect_option_snapshot]

    D --> E[get_last_price]
    D --> F[get_option_expiration_dates]

    F --> G[Keep expirations from today to 1 year]

    G --> H[_get_full_option_chain]

    H --> I[get_option_chain]
    I --> J[Combine option chains]

    J --> K[filter_otm_puts]

    K --> L["Keep Put options<br/>0.60 × Underlying Price ≤ Strike &lt; Underlying Price"]

    L --> M[_get_option_snapshots]

    M --> N[get_market_snapshot]

    N --> O[Build 17-column DataFrame]

    O --> P[save_snapshots]

    P --> Q[(data/options.db)]
```

---

## Main Collection Sequence

```mermaid
sequenceDiagram

    participant Script as collect_options.py
    participant Client as FutuClient
    participant Collector as collector.py
    participant Filter as filters.py
    participant DB as OptionDatabase
    participant Futu as Futu OpenD

    Script->>Client: Create connection
    Script->>Collector: collect_option_snapshot()

    Collector->>Client: get_last_price()
    Client->>Futu: Request underlying snapshot
    Futu-->>Client: Underlying price
    Client-->>Collector: underlying_price

    Collector->>Client: get_option_expiration_dates()
    Client->>Futu: Request expiration dates
    Futu-->>Client: Available expirations
    Client-->>Collector: Expiration dates

    Collector->>Collector: Keep today to 1 year

    Collector->>Client: get_option_chain()
    Client->>Futu: Request option chains
    Futu-->>Client: Raw option chain
    Client-->>Collector: Option chain

    Collector->>Filter: filter_otm_puts()
    Filter-->>Collector: Filtered Put contracts

    Collector->>Client: get_market_snapshot()
    Client->>Futu: Request option snapshots
    Futu-->>Client: Prices, IV, Greeks, volume, OI
    Client-->>Collector: Market snapshots

    Collector->>Collector: Build 17-column DataFrame

    Collector-->>Script: DataFrame

    Script->>DB: save_snapshots(df)
    DB-->>Script: Saved

    Script->>Client: close()
```

---

## Option Filtering Rules

The current option universe is restricted to put options.

The strike price must satisfy:

```text
0.60 × underlying_price <= strike < underlying_price
```

Therefore:

- Call options are excluded.
- In-the-money put options are excluded.
- Extremely deep out-of-the-money put options are excluded.
- Only expiration dates from today up to one year are collected.

The minimum strike ratio is currently:

```text
0.60
```

and can be adjusted later.

---

## Data Pipeline

The complete pipeline can be summarized as:

```mermaid
flowchart LR

    A[Futu OpenD]
    --> B[FutuClient]
    --> C[Collector]
    --> D[Filters]
    --> E[17-column DataFrame]
    --> F[OptionDatabase]
    --> G[(SQLite)]
```

---

## Module Responsibilities

### `futu_client.py`

Responsible only for communication with Futu OpenAPI.

Main responsibilities:

- Connect to Futu OpenD
- Retrieve underlying prices
- Retrieve option expiration dates
- Retrieve option chains
- Retrieve option market snapshots

### `filters.py`

Responsible for option selection rules.

Current rules:

```text
Put only
OTM only
Strike >= 60% of underlying price
Strike < underlying price
```

### `collector.py`

Responsible for coordinating market-data collection.

It:

1. Retrieves the underlying price.
2. Retrieves available expiration dates.
3. Keeps expirations from today up to one year.
4. Retrieves option chains.
5. Applies option filters.
6. Retrieves market snapshots.
7. Builds the final 17-column DataFrame.

### `database.py`

Responsible for persistent historical storage.

Current database:

```text
data/options.db
```

Storage engine:

```text
SQLite
```

The database is private and is not committed to GitHub.

### `collect_options.py`

Main executable entry point for the data collection pipeline.

Run from the project root with:

```powershell
python scripts/collect_options.py
```

---

## Current Development Underlying

During the current testing phase:

```text
US.NVDA
```

is enabled.

Other planned underlyings are temporarily disabled in `config.py`:

```python
UNDERLYINGS = [
    "US.NVDA",
    # "US.GOOG",
    # "US.IREN",
    # "US.SPCX",
]
```

They can be enabled after the NVDA collection pipeline has been fully validated.