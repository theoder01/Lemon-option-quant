# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 13, 2026

"""GUI-only English and Simplified Chinese resources, keyed by English identifiers."""

LANGUAGES = {"en": "English", "zh_CN": "简体中文"}

STRINGS = {'app_name': {'en': 'Lemon Option Quant', 'zh_CN': 'Lemon Option Quant'},
 'window_title': {'en': 'Lemon Option Quant — Put Analysis', 'zh_CN': 'Lemon Option Quant — Put 分析'},
 'language': {'en': 'Language', 'zh_CN': '语言'},
 'subtitle': {'en': 'New Position Analysis · Sell Put · 1 contract / 100 shares · Local history',
              'zh_CN': '卖 Put 开仓分析 · 1 张 / 100 股 · 本地历史库'},
 'database': {'en': 'Historical Database', 'zh_CN': '历史数据库'},
 'choose_file': {'en': 'Choose File', 'zh_CN': '选择文件'},
 'contract_inputs': {'en': 'Contract Inputs', 'zh_CN': '合约输入'},
 'underlying': {'en': 'Underlying', 'zh_CN': '标的'},
 'expiry': {'en': 'Expiration Date', 'zh_CN': '到期日'},
 'expiry_hint': {'en': 'Choose a historical date or enter YYYY-MM-DD', 'zh_CN': '可选择历史库中的日期，或输入 YYYY-MM-DD'},
 'premium': {'en': 'Premium / Share', 'zh_CN': '权利金 / 股'},
 'strike': {'en': 'Strike Price', 'zh_CN': '行权价 Strike'},
 'spot': {'en': 'Underlying Price / Share', 'zh_CN': '标的现价 / 股'},
 'load_reference': {'en': 'Load Historical Price and Expirations', 'zh_CN': '读取历史参考价与到期日'},
 'calculate': {'en': 'Calculate Percentile and Initial Annualized Return', 'zh_CN': '计算百分位与初始年化'},
 'historical_percentile': {'en': 'Historical Premium Percentile', 'zh_CN': '历史权利金百分位'},
 'net_annualized_return': {'en': 'Net Initial Annualized Return · After Opening Fees',
                           'zh_CN': '初始简单年化 · 扣开仓费'},
 'comparison': {'en': 'Comparison: same underlying Put; strike/spot within ±2 percentage points; DTE within '
                      '±5 days.',
                'zh_CN': '比较：同标的 Put；行权价/现价 ±2 个百分点；DTE ±5 天。'},
 'percentile_explanation': {'en': 'Percentile: share of historical premium/spot ratios strictly below the '
                                  'current ratio; not a win probability.',
                            'zh_CN': '百分位 = 历史权利金/股价严格低于当前比例的样本占比；不代表胜率。'},
 'details_heading': {'en': 'Calculation Details and Data Coverage', 'zh_CN': '计算明细与数据覆盖'},
 'risk_notice': {'en': 'Annualized return assumes worthless expiration without assignment; it is not '
                       'guaranteed. Assignment requires buying 100 shares at the strike. Losses can far '
                       'exceed the premium.',
                 'zh_CN': '年化假设期权无价值到期且未接货，不是保证收益。接货须按行权价买入 100 股，损失可能远超权利金。'},
 'manual_spot_hint': {'en': 'Enter a spot price manually; historical reference prices are not live quotes.',
                      'zh_CN': '现价可手动填写；历史参考价不是实时行情。'},
 'initial_status': {'en': 'Enter one standard Put; all prices are in USD.', 'zh_CN': '填写一张标准 Put；所有价格以美元计。'},
 'inputs_updated': {'en': 'Inputs changed. Please calculate again.', 'zh_CN': '输入已更新，请重新计算。'},
 'underlying_changed': {'en': 'Underlying changed. Enter a spot price or reload the historical reference.',
                        'zh_CN': '标的已更改，请输入现价或重新读取历史参考价。'},
 'manual_spot_source': {'en': 'Spot source: manual entry. Use the same valuation time as the premium.',
                        'zh_CN': '现价来源：手动输入，请与权利金使用同一估值时刻。'},
 'choose_database': {'en': 'Choose Option History Database', 'zh_CN': '选择期权历史库'},
 'sqlite_files': {'en': 'SQLite Databases', 'zh_CN': 'SQLite 数据库'},
 'all_files': {'en': 'All Files', 'zh_CN': '所有文件'},
 'no_historical_price': {'en': 'No valid historical spot price found. Enter a spot price manually.',
                         'zh_CN': '未找到有效历史股价，请手动输入现价。'},
 'reference_loaded': {'en': 'Historical references loaded. Expirations come from history and may not include '
                            'all currently listed contracts.',
                      'zh_CN': '已读取历史参考数据。到期日列表来自历史库，不保证包含当前全部挂牌合约。'},
 'invalid_expiry_format': {'en': 'Use YYYY-MM-DD for the expiration date.', 'zh_CN': '到期日请使用 YYYY-MM-DD 格式。'},
 'no_comparable_data': {'en': 'No Comparable Data', 'zh_CN': '暂无可比数据'},
 'fees_explanation': {'en': 'Fees: Futu HK fixed plan, rate snapshot 2026-09-28; actual invoice rounding may '
                            'differ.',
                      'zh_CN': '费用：富途香港固定式套餐，2026-09-28 费率快照；实际账单取整可能不同。'},
 'annual_formula': {'en': 'Annualized return = net premium / full strike cash collateral × 365 / remaining '
                          'calendar days.',
                    'zh_CN': '年化 = 净权利金 / 全额行权现金担保 × 365 / 剩余自然日。'},
 'historical_quote_basis': {'en': 'Historical quote basis: last; execution conditions may differ from the '
                                  'entered premium.',
                            'zh_CN': '历史报价口径：last；输入权利金与历史 last 的成交条件可能不同。'},
 'threshold_met': {'en': 'IREN example threshold: initial annualized return >30% met; for further assessment '
                         'only.',
                   'zh_CN': 'IREN 示例阈值：满足初始年化 >30%，仅供进一步判断。'},
 'threshold_not_met': {'en': 'IREN example threshold: initial annualized return >30% not met.',
                       'zh_CN': 'IREN 示例阈值：未满足初始年化 >30%。'},
 'historical_spot_note': {'en': 'Using a historical spot price. Verify the percentile with a spot price from '
                                'the same time as the premium.',
                          'zh_CN': '当前使用历史参考股价，建议用与权利金同步的现价核对百分位。'},
 'calculation_complete': {'en': 'Calculation complete. Percentile indicates historical relative position '
                                'only, not a trading recommendation.',
                          'zh_CN': '计算完成。百分位只反映历史相对位置，不是买卖建议。'},
 'message_separator': {'en': '; ', 'zh_CN': '；'},
 'unknown_error': {'en': 'Unexpected error. Check inputs and database access. Technical details: {detail}',
                   'zh_CN': '发生意外错误，请检查输入及数据库访问权限。技术详情：{detail}'},
 'database_open_error': {'en': 'Unable to open the database file.', 'zh_CN': '无法打开数据库文件。'},
 'database_schema_error': {'en': 'The database does not contain the expected option history schema.',
                           'zh_CN': '数据库缺少预期的期权历史表或字段。'},
 'preference_not_saved': {'en': 'Language changed, but the preference could not be saved.',
                          'zh_CN': '语言已切换，但无法保存语言偏好。'},
 'database_temporarily_unavailable': {'en': 'History unavailable; annualized return can still be calculated: '
                                            '{error}',
                                      'zh_CN': '历史库暂不可用，仍可计算年化：{error}'},
 'historical_reference': {'en': 'Historical reference · {underlying} · {timestamp} (UTC; not live; editable)',
                          'zh_CN': '历史参考价 · {underlying} · {timestamp}（UTC；非实时，可手动覆盖）'},
 'reference_failed': {'en': 'Reference lookup failed; enter values manually to continue: {error}',
                      'zh_CN': '读取失败，可手动输入继续：{error}'},
 'database_unavailable': {'en': 'History database unavailable: {error}', 'zh_CN': '历史库不可用：{error}'},
 'contract_detail': {'en': '{underlying} Put  |  Expires {expiry}  |  1 contract / 100 shares',
                     'zh_CN': '{underlying} Put  |  {expiry} 到期  |  1 张 / 100 股'},
 'valuation_detail': {'en': 'Valuation time: {as_of}  |  New York date: {trading_date}',
                      'zh_CN': '估值时间：{as_of}  |  纽约日期：{trading_date}'},
 'capital_detail': {'en': 'Remaining calendar days: {remaining_days:g}  |  Strike cash collateral: '
                          '${capital:,.2f}',
                    'zh_CN': '剩余自然日：{remaining_days:g}  |  行权现金担保：${capital:,.2f}'},
 'premium_detail': {'en': 'Premium income: ${premium_income:,.2f}  |  Estimated opening fee: '
                          '${transaction_fee:.2f}  |  Net premium: ${net_premium:,.2f}',
                    'zh_CN': '权利金收入：${premium_income:,.2f}  |  估算开仓费：${transaction_fee:.2f}  |  '
                             '净权利金：${net_premium:,.2f}'},
 'moneyness_detail': {'en': 'Strike/spot: {moneyness:.2%}', 'zh_CN': '行权价/现价：{moneyness:.2%}'},
 'sample_detail': {'en': 'Valid historical samples: {sample_count} snapshots over {trading_days} trading '
                         'dates (not independent trades)',
                   'zh_CN': '有效历史样本：{sample_count} 条快照，覆盖 {trading_days} 个交易日期（非独立交易样本）'},
 'history_range': {'en': 'History range: {start} to {end}', 'zh_CN': '历史区间：{start} 至 {end}'},
 'ratio_detail': {'en': 'Premium/spot: current {current:.3%}; historical median {median:.3%}; range '
                        '{minimum:.3%}–{maximum:.3%}',
                  'zh_CN': '权利金/股价：当前 {current:.3%}；历史中位数 {median:.3%}；范围 {minimum:.3%}–{maximum:.3%}'},
 'calculation_failed': {'en': 'Unable to calculate: {error}', 'zh_CN': '无法计算：{error}'},
 'invalid_underlying': {'en': 'Enter a US stock symbol, such as IREN or US.NVDA.',
                        'zh_CN': '请输入美股代码，例如 IREN 或 US.NVDA。'},
 'aware_valuation_required': {'en': 'Valuation time must be timezone-aware.', 'zh_CN': '估值时间必须带时区。'},
 'missing_history_fields': {'en': 'History is missing underlying or snapshot_time fields.',
                            'zh_CN': '历史库缺少 underlying 或 snapshot_time 字段。'},
 'future_expiry_required': {'en': 'Expiration must be after today in New York; same-day expiration is not '
                                  'supported.',
                            'zh_CN': '到期日须晚于纽约今天；第一版暂不计算到期日当天的合约。'},
 'spot_required_for_percentile': {'en': 'Enter a spot price to calculate historical percentile; annualized '
                                        'return does not require it.',
                                  'zh_CN': '补充标的现价后可计算历史百分位；年化不需要现价。'},
 'itm_percentile_unavailable': {'en': 'This Put is in the money; history only collects out-of-the-money '
                                      'Puts, so percentile is unavailable.',
                                'zh_CN': '当前为价内 Put；现有历史库只采集价外 Put，暂不提供历史百分位。'},
 'no_underlying_history': {'en': 'No history for this underlying; initial annualized return is still '
                                 'available.',
                           'zh_CN': '没有该标的历史记录；仍可计算初始年化。'},
 'missing_comparison_fields': {'en': 'History is missing price, option code, or DTE fields; percentile is '
                                     'unavailable.',
                               'zh_CN': '历史库缺少价格、合约代码或 DTE 字段，无法计算百分位。'},
 'limited_history': {'en': 'Historical samples or date coverage are limited; percentile is for reference '
                           'only.',
                     'zh_CN': '历史样本较少或覆盖天数较短，百分位仅供参考。'},
 'no_matching_samples': {'en': 'No valid historical Put samples with similar moneyness and DTE.',
                         'zh_CN': '没有满足相近价内外程度和 DTE 的有效历史 Put 样本。'},
 'premium_valid': {'en': 'Premium per share must be a valid number.', 'zh_CN': '每股权利金必须是有效数字。'},
 'premium_positive': {'en': 'Premium per share must be finite and positive.', 'zh_CN': '每股权利金必须大于零，且为有限数字。'},
 'premium_nonnegative': {'en': 'Premium per share must be finite and nonnegative.',
                         'zh_CN': '每股权利金必须不小于零，且为有限数字。'},
 'strike_valid': {'en': 'Strike price must be a valid number.', 'zh_CN': '行权价必须是有效数字。'},
 'strike_positive': {'en': 'Strike price must be finite and positive.', 'zh_CN': '行权价必须大于零，且为有限数字。'},
 'strike_nonnegative': {'en': 'Strike price must be finite and nonnegative.', 'zh_CN': '行权价必须不小于零，且为有限数字。'},
 'spot_valid': {'en': 'Spot price must be a valid number.', 'zh_CN': '标的现价必须是有效数字。'},
 'spot_positive': {'en': 'Spot price must be finite and positive.', 'zh_CN': '标的现价必须大于零，且为有限数字。'},
 'spot_nonnegative': {'en': 'Spot price must be finite and nonnegative.', 'zh_CN': '标的现价必须不小于零，且为有限数字。'}}
