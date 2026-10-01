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

## Navigation and Existing Position

Use the **New Position** / **Existing Position** tabs in the same application
window. Inputs and calculated results stay on their page throughout the session.
Language selection is shared; it immediately translates both pages, tab titles,
current details, validation messages, and an open calendar without recalculation.
Enter calculates the active page; confirming a language choice does not calculate.

Existing Position accepts underlying, expiration, strike per share, current
buyback premium per share, contracts (default 1), and current underlying price
per share. Enter the executable buyback quote, normally Ask. Strike and spot must
be finite and positive, premium finite and nonnegative, and contracts a positive
integer. Validation occurs on Calculate, using the same unrestricted editing and
ICU-safe numeric entries as New Position. Dates use the existing calendar and
New York calendar-day convention; expiration must be after today.

The three result cards show **Remaining Annualized Return**, **Remaining
Potential Profit**, and **Gross Collateral**. Calculation Details show the
contract, all input prices, contract count, remaining DTE, collateral, current
buyback cost, estimated buy-to-close fee, remaining potential profit, period and
annualized returns, and fee source. The fee is an avoided cost when holding to
worthless expiration, not a holding charge. The GUI calls the existing remaining
return function with automatic buy-side fees; there is no manual-fee field.

Spot is position context only. A Put is OTM when spot exceeds strike, ATM at
equality, and ITM below strike. Moneyness uses the existing strike/spot helper
and displays a percentage. Spot never enters the remaining-return function.
The analytics risk notice states the conditional worthless-expiration assumption,
possible early assignment, 100 shares per contract, and potential stock losses.
Remaining return is not guaranteed or expected return, assignment probability,
or downside safety. There are no opening-premium/fee inputs, trade P&L, strategy
judgments, or historical premium/IV analytics on Existing Position.

## New Position workflow and calculation conventions

Enter one standard US equity Put: underlying (IREN or US.IREN), expiration date,
premium per share, strike price, and underlying spot price. All amounts are USD.
**Load Historical Price and Expirations** fills the latest historical spot price
and displays its UTC timestamp. It is not live data. Expirations from history may
not include all currently listed contracts; YYYY-MM-DD can also be entered.
Use spot and premium from the same valuation time. Changing the ticker clears
the old spot price.

Numeric inputs permit normal text editing, including temporarily empty text,
partial numbers, Backspace/Delete, Ctrl+A to select all, and copy/paste. Strict
validation occurs on Calculate: premium must be finite and nonnegative, strike
must be finite and positive, and a supplied spot must be finite and positive.
Blank spot retains the existing annual-only behavior; premium and strike are
required. Editing clears stale results rather than blocking the keystroke.

The expiration dropdown continues to offer dates loaded from the database.
The **Calendar** button beside it opens a lightweight Tk calendar with previous
and next month controls. Select a day to populate the same expiration input in
ISO `YYYY-MM-DD` format, including dates absent from the historical dropdown.
It initially shows the entered date, or today's New York date if the input is
empty or invalid. **Today** selects that New York date; **Cancel** or Escape
closes without changing the input. Past and same-day dates remain selectable,
but Calculate enforces the existing expiration rules. Selecting a date does not
calculate automatically or change the database's dropdown choices.

The calendar is non-modal, so the main language selector remains usable while
it is open. Its title, month names, weekdays and controls update immediately
between English and Simplified Chinese. It uses only Python's standard-library
`calendar`, `datetime` and Tkinter; no new dependency is needed.

**Calculate Percentile and Initial Annualized Return** displays:

- Historical premium percentile: existing comparable-option and premium analysis,
  using past Put snapshots for the same underlying, strike/spot within 2 percentage
  points and DTE within 5 days. Only premium/spot ratios strictly below the current
  ratio count; ties do not. This is not a win probability.
- Net initial annualized return: one contract / 100 shares, full strike cash
  collateral, after estimated Futu HK fixed-plan opening fees. Existing fee and
  annualized-return calculations are unchanged.
- Historical IV percentile: the selected Put's latest stored IV compared with
  valid prior premium-comparable snapshots. This third card is reference only.
- Sample count, trading-date coverage, history range, premium ratios, collateral,
  net premium, fees, DTE, and moneyness.

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

## Historical IV reference

The third result card shows **Historical IV Percentile**, **Current IV**, and
**Reference only**. This supplements premium analysis and net annualized return;
it does not classify entries, generate a
buy/sell recommendation, or combine the percentiles into a score. No manual IV
input or separate analysis page is added.

The latest stored observation strictly before valuation time is selected by
underlying, Put type, expiration date, and exact strike. IV units are percentage
points (`52.4` means `52.4%`). The contract code and UTC timestamp are shown in
details. This is a historical reference, not a live quote or the IV implied by
the manually entered premium. No different strike/expiration or older valid IV
is substituted if the latest matching IV is invalid. Ambiguous latest snapshots
produce an unavailable state rather than an arbitrary choice.

`analyze_put_preview()` retains the existing premium-comparable DataFrame and
passes it to `analyze_put_iv_reference()`. That helper restricts IV peers to
timestamps strictly earlier than the selected IV source snapshot. Thus the source
observation, simultaneous snapshots, and later observations cannot enter its own
comparison. Both analyses use the entered strike/spot ±2 percentage points and
current calendar DTE ±5 days, same underlying Put, and existing valid-price/Put
filters. No second peer-selection algorithm exists. Premium keeps its original
valuation-time cutoff, so sample counts can differ; details state this explicitly.

Existing `analytics/iv_analysis.py::analyze_iv()` supplies the percentile and
statistics. Its stored-value filtering is shared through `valid_iv_values()`:
nulls, nonnumeric values, nonfinite values, zero/negative values and IV above 500%
are excluded. The existing strict-below definition is unchanged:

`100 × count(valid prior IV < current IV) / count(valid prior IV)`.

There is no existing statistical minimum beyond a nonempty valid IV set, so no
new cutoff is invented. Zero valid prior samples display **Insufficient historical
IV data**, a dash instead of a numeric percentile, and sample count zero. Nonempty
sets retain the analyzer's percentile, including a genuine 0%; fewer than 20
snapshots or 5 New York dates receive the GUI's existing limited-history warning
policy. These warnings are descriptive, not IV thresholds or trading signals.

Details contain current IV, percentile, valid snapshot and trading-date counts,
median, range, source timestamp, peer criteria and percentile definition. Without
valid current IV or eligible spot/moneyness inputs, coverage is marked not
evaluated. Premium and annualized calculations still work as before. Input edits
clear stale IV output; language switching rerenders retained IV results without
recalculation or database writes. All added text uses the existing English/Chinese
resources.

IV tests cover exact contract/time lookup, strict ties, source and later-snapshot
exclusion, moneyness/DTE boundaries, invalid IV, missing/ambiguous sources, limited
history, unchanged premium/annual/fee results, SQLite-backed loading, and both
GUI languages. The old `tests/test_iv_analysis.py` remains a manual example;
`tests/test_put_iv_preview.py` provides automated integration coverage.

Existing Position integration tests cover analytics reuse, fee estimation, input
validation, moneyness, navigation, calendars, and immediate translation. Numeric
editing tests exercise both pages, including simulated Tk ICU failures.

[Project](../README.md) · [Architecture](architecture.md) ·
[Return and fee conventions](put_annualized_return.md) · [Data schema](data_schema.md)
