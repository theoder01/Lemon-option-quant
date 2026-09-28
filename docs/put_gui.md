Copyright © 2026 Bo Hu. All rights reserved.

Created: September 28, 2026

# Put 分析小窗口

在项目根目录运行 `python scripts/launch_put_gui.py`，使用项目已有 Python 环境即可，不新增第三方依赖。窗口使用 Python 自带 Tkinter；启动脚本会定位本项目源码及 `data/options.db`，也可在界面选择其它已有数据库。

输入一张标准美股 Put：Underlying（可输入 IREN 或 US.IREN）、到期日、每股权利金、行权价以及标的现价。点击“读取历史参考价与到期日”可填入最新历史股价并显示 UTC 时间；它不是实时行情。到期日下拉框来自历史库，支持手输 YYYY-MM-DD，不保证列出当前全部挂牌日期。权利金需手动输入，标的现价最好与权利金来自同一时刻。切换标的会清除旧现价。

点击“计算百分位与初始年化”得到：

- 历史权利金百分位：复用已有 `find_comparable_options` 与 `analyze_premium`。同标的历史 Put、行权价/股价相差不超过 2 个百分点、DTE 相差不超过 5 天，只用估值时间以前的数据。比较历史 last/股价与输入权利金/现价，严格小于当前比例的样本占比即百分位；相等不计入。
- 初始年化：一张、100 股、全额行权现金担保，自动扣除富途香港固定式套餐估算开仓费。复用已验证的年化与费用模块。
- 补充：有效快照样本数、覆盖交易日期数及区间、历史中位权利金比例、现金担保、净权利金、费用、DTE、价内外程度。IREN 显示已有 >30% 示例阈值是否满足，非交易指令。

年化使用纽约当天至到期日的自然日数、ACT/365 简单年化。第一版不支持当天到期；日内精确截止时刻留待后续。仅支持一张未调整的标准 Put，不处理调整合约或组合。

历史库只读，不采集行情、不连接 OpenD、不下单。数据库缺失、标的无历史、现价未填或无匹配样本时，仍可计算年化；百分位显示不可用而非虚构为零。现有库主要采集价外 Put，价内 Put 暂不输出百分位。无效历史数值、看涨合约和未来快照均不进入比较。

百分位按快照行加权，不按日期等权，也不是独立交易胜率。少于 20 条快照或少于 5 个交易日期时显示样本不足提示；这些是提示阈值，不是统计显著性保证。历史 last 与当前可成交报价可能不同。年化假设无价值到期且未接货，不保证实现。

测试：

```powershell
$env:PYTHONPATH = "$PWD/src"
python -B -m unittest discover -s tests -p test_put_preview.py -v
python -B -m unittest discover -s tests -p test_put_gui.py -v
```

GUI 测试需要可用的 Tk 环境，使用隐藏测试窗口。手动检查：启动→读取 IREN 历史参考价→选择到期日→输入行权价与权利金→计算；再切换标的或输入无效数字，旧结果应清空。

## 与分析模块的关系

启动入口为 `scripts/launch_put_gui.py`，窗口类为 `PutAnalysisWindow`。界面调用 `analytics/put_preview.py` 聚合已有历史比较、权利金统计及初始年化功能。`ReadOnlyOptionDatabase` 复用 `OptionDatabase` 的查询接口，以 SQLite `mode=ro` 打开文件，不新建缺失数据库，使用完后关闭连接。

当前窗口仅用于开仓分析，尚未展示剩余持有期年化；该计算已在 `put_annualized_return.py` 中实现。界面也不展示现有 IV 分析模块的结果，不新增 Risk Analysis、Event Analysis 或自动交易。

[项目说明](../README.md) · [架构与类图](architecture.md) · [年化与手续费口径](put_annualized_return.md) · [数据结构](data_schema.md)
