# Daily Stock Metrics

From the project root, with Futu OpenD running and the project's dependencies installed:

```powershell
python scripts/run_stock_metrics.py
```

The runner reads `live_short_put_scanner.config.UNDERLYINGS` on each run and
processes tickers in configured order. It uses the existing scanner host/port
settings and stores successful rows in `data/stock_metrics.db`.

Sources:

| Field | Existing source |
| --- | --- |
| `spot` | Futu live underlying market snapshot via `get_last_price` |
| `iv_rank` | Futu current underlying overview through scanner `get_snapshot` |
| `iv_hv` | Scanner's latest historical IV minus HV, in percentage points |
| `drawdown_52w` | Existing drawdown function, using live spot and scanner's highest historical underlying price in its existing one-year window |
| `put_call_skew` | Live PUT/CALL chain and batched option snapshots, followed by existing `calculate_30d_skew` |

IV/HV retain the scanner's latest historical observation source; they are not
intraday IV/HV observations. Retrieval is sequential, not an atomic market
snapshot. All stock rows and temporary option rows share one UTC runner timestamp
to identify the same run. No stored historical metric is used as a fallback.

The option-chain path reuses the collector's expiration-window and snapshot-batch
helpers. It does not invoke option filters, collection validation or persistence.
Temporary option rows remain in memory. No access to `options.db` is required.

Each ticker requires valid spot and all four metrics. Missing or invalid data,
unavailable 30D brackets and ticker-specific API/storage failures produce a SKIP
reason; remaining tickers continue. Valid zero and negative metric values retain
their existing meaning. Spot must be positive and official IV Rank remains in
the scanner's 0–100 range.

`DailyStockMetricsRunner.run()` returns `DailyRunResult` with one ordered
`TickerResult` per ticker. It exposes `total_tickers`, `successful_tickers`,
`saved_rows`, `duplicate_rows`, and `skipped_tickers` (records with ticker/reason).
Successful results retain their `StockMetrics` object.

The database's existing ticker + New York date rule remains first-write-wins:
rerunning reports duplicate rows without replacing the original daily values.
The script closes both Futu clients on success, error or interruption. It returns
exit code 0 when every ticker succeeds (duplicates count as success), otherwise 1.

No scheduling, charts, scoring, recommendations or option-contract selection are
performed by this command.
