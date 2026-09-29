Copyright © 2026 Bo Hu. All rights reserved.

Created: September 28, 2026

# Put Analysis Window

Run `python scripts/launch_put_gui.py` from the project environment. The launcher
locates the source tree and `data/options.db`; the GUI can also select another
existing database. Tkinter is included with Python. No new dependency is needed.

## Language

English is the default. Use the **Language** selector at the bottom of the window
to choose **English** or **简体中文**. Labels, the title, current result details,
warnings, reference-price descriptions, and validation errors update immediately.
Inputs, numeric results, historical selections, and database contents are preserved;
switching languages does not rerun analysis or reload history.

The launcher saves only `{"language": "en"}` or `{"language": "zh_CN"}` in
`data/gui_preferences.json`, separate from SQLite. This ignored local file persists
the preference for this checkout. Missing, unreadable, malformed, and unsupported
preferences default to English. A save failure displays a notice and does not stop
the language change. A previously running version needs one relaunch to load this
update; subsequent language changes do not require restarting.

## Workflow and calculation conventions

Enter one standard US equity Put: underlying (IREN or US.IREN), expiration date,
premium per share, strike price, and underlying spot price. All amounts are USD.
**Load Historical Price and Expirations** fills the latest historical spot price
and displays its UTC timestamp. It is not live data. Expirations from history may
not include all currently listed contracts; YYYY-MM-DD can also be entered.
Use spot and premium from the same valuation time. Changing the ticker clears
the old spot price.

**Calculate Percentile and Initial Annualized Return** displays:

- Historical premium percentile: existing comparable-option and premium analysis,
  using past Put snapshots for the same underlying, strike/spot within 2 percentage
  points and DTE within 5 days. Only premium/spot ratios strictly below the current
  ratio count; ties do not. This is not a win probability.
- Net initial annualized return: one contract / 100 shares, full strike cash
  collateral, after estimated Futu HK fixed-plan opening fees. Existing fee and
  annualized-return calculations are unchanged.
- Sample count, trading-date coverage, history range, premium ratios, collateral,
  net premium, fees, DTE, and moneyness. The existing IREN >30% example threshold is
  advisory, not a trading instruction.

Annualization uses calendar days from today's New York date to expiration and
simple ACT/365. Same-day expiration and adjusted or multi-leg contracts are not
supported. Return assumes worthless expiration without assignment; it is not
guaranteed. Assignment requires buying 100 shares at the strike, and losses may
exceed the premium.

The database is read-only. The window does not collect quotes, connect to OpenD,
or place orders. Missing history, spot, or comparable samples still allow the
annualized calculation. Percentile is unavailable rather than zero. In-the-money
Puts have no percentile because the existing collection covers out-of-the-money
Puts. Invalid values, calls, and future snapshots are excluded.

Snapshots are row-weighted, not equally weighted by day or independent trades.
Fewer than 20 snapshots or 5 trading dates triggers a limited-history warning.
Historical last prices may differ from currently executable quotes.

## Localization architecture

`put_gui.py` contains one widget tree and one set of callbacks. `gui_strings.py`
contains English and Simplified Chinese resources under stable English keys.
`gui_i18n.py` provides retained `Message` values, nested formatting, joining,
English fallback, and preference loading/saving. The window retains these values
alongside display variables and renders them again when the language changes.
Formatted result messages retain their original numeric values and timestamps.

Business logic never imports GUI resources or receives a language. Existing
`put_preview.py` notes and validation messages are now English; their conditions
and calculations are unchanged. The GUI adapter maps those English messages to
translation keys. Update that mapping/catalog when changing a business message;
tests cover current note and validation literals. New languages require resources
and a selector name, without changing analysis logic.

All application-owned GUI prose is centralized. Numeric values, ticker symbols,
paths, timestamps, the brand name, and technical terms such as USD/DTE/UTC remain
language-independent. Unknown OS/library diagnostics are retained verbatim inside
a translated error wrapper. Native file-dialog buttons and shell content use the
operating-system language; the application supplies a translated title and filters.

## Validation

From the repository root:

```powershell
$env:PYTHONPATH = "$PWD/src"
python -B -m pytest -q
```

Tk tests need a desktop-capable Tk environment. Tests cover catalog/placeholder
parity, English defaults and fallback, preferences and failure handling, translated
errors/reference text/file-dialog arguments, and immediate switching after a
calculation. A real temporary SQLite fixture is compared byte-for-byte before and
after switching; mocks assert no analysis or database call occurs on switching.
Existing premium, fee, comparable-option, and annualized-return tests remain part
of the suite. GUI source checks reject literal widget text and Chinese prose.

Manual check: launch, load reference data, enter a contract, calculate, switch
languages both ways, and confirm the numeric results and inputs stay fixed. Test
invalid input and missing history in both languages, then relaunch to check the
preference. Native dialogs follow the OS locale as described above.

The window currently exposes new-position Put analysis only. Existing-position
remaining annualized return and implied-volatility analysis remain in their
existing modules and are not added to the GUI by this localization task.

[Project](../README.md) · [Architecture](architecture.md) ·
[Return and fee conventions](put_annualized_return.md) · [Data schema](data_schema.md)
