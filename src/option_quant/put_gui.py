# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 28, 2026

"""Small offline Tk window for a single cash-secured Put."""

from datetime import date
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, ttk

import pandas as pd

from option_quant.analytics.put_preview import (
    ReadOnlyOptionDatabase,
    analyze_put_preview,
    latest_reference,
    normalize_underlying,
)
from option_quant.analytics.put_annualized_return import YieldThresholds
from option_quant.time_utils import now_utc, get_trading_date


class PutAnalysisWindow(ttk.Frame):
    def __init__(self, master, database_path: Path):
        super().__init__(master, padding=22)
        self.pack(fill="both", expand=True)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(10, weight=1)
        self.database_path = tk.StringVar(value=str(database_path))
        self.underlying = tk.StringVar(value="US.IREN")
        self.expiry = tk.StringVar()
        self.premium = tk.StringVar()
        self.strike = tk.StringVar()
        self.spot = tk.StringVar()
        self.spot_source = tk.StringVar(value="现价可手动填写；历史参考价不是实时行情。")
        self.status = tk.StringVar(value="填写一张标准 Put；所有价格以美元计。")
        self.annual_text = tk.StringVar(value="—")
        self.percentile_text = tk.StringVar(value="—")
        self._loading = False
        self._historical_spot = False

        ttk.Label(self, text="Lemon Option Quant", font=("Microsoft YaHei UI", 20, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(self, text="卖 Put 开仓分析 · 1 张 / 100 股 · 本地历史库").grid(row=1, column=0, columnspan=3, sticky="w", pady=(3, 18))
        ttk.Label(self, text="历史数据库").grid(row=2, column=0, sticky="w", padx=(0, 14))
        ttk.Entry(self, textvariable=self.database_path).grid(row=2, column=1, sticky="ew")
        ttk.Button(self, text="选择文件", command=self.choose_database).grid(row=2, column=2, padx=(8, 0))

        inputs = ttk.LabelFrame(self, text="合约输入", padding=14)
        inputs.grid(row=3, column=0, columnspan=3, sticky="ew", pady=14)
        inputs.columnconfigure(1, weight=1)
        inputs.columnconfigure(3, weight=1)
        ttk.Label(inputs, text="Underlying").grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.ticker_box = ttk.Combobox(inputs, textvariable=self.underlying, width=20)
        self.ticker_box.grid(row=0, column=1, sticky="ew")
        ttk.Label(inputs, text="到期日").grid(row=0, column=2, padx=(22, 12))
        self.expiry_box = ttk.Combobox(inputs, textvariable=self.expiry, width=20)
        self.expiry_box.grid(row=0, column=3, sticky="ew")
        ttk.Label(inputs, text="可选择历史库中的日期，或输入 YYYY-MM-DD").grid(row=1, column=2, columnspan=2, sticky="w", padx=(22, 0), pady=(4, 8))
        for column, label, variable in [(0, "权利金 / 股", self.premium), (2, "行权价 Strike", self.strike)]:
            ttk.Label(inputs, text=label).grid(row=2, column=column, sticky="w", padx=(0 if column == 0 else 22, 12))
            ttk.Entry(inputs, textvariable=variable).grid(row=2, column=column + 1, sticky="ew")
        ttk.Label(inputs, text="标的现价 / 股").grid(row=3, column=0, sticky="w", pady=(14, 0))
        ttk.Entry(inputs, textvariable=self.spot).grid(row=3, column=1, sticky="ew", pady=(14, 0))
        self.reference_button = ttk.Button(inputs, text="读取历史参考价与到期日", command=self.load_reference)
        self.reference_button.grid(row=3, column=2, columnspan=2, sticky="ew", padx=(22, 0), pady=(14, 0))
        ttk.Label(inputs, textvariable=self.spot_source, wraplength=740, foreground="#806019").grid(row=4, column=0, columnspan=4, sticky="w", pady=(10, 0))
        self.analyze_button = ttk.Button(self, text="计算百分位与初始年化", command=self.calculate)
        self.analyze_button.grid(row=4, column=0, columnspan=3, sticky="ew", ipady=6)
        ttk.Label(self, textvariable=self.status, wraplength=820, foreground="#805800").grid(row=5, column=0, columnspan=3, sticky="w", pady=10)

        cards = ttk.Frame(self)
        cards.grid(row=6, column=0, columnspan=3, sticky="ew")
        for col, title, var in [(0, "历史权利金百分位", self.percentile_text), (1, "初始简单年化 · 扣开仓费", self.annual_text)]:
            cards.columnconfigure(col, weight=1, uniform="card")
            frame = ttk.LabelFrame(cards, text=title, padding=15)
            frame.grid(row=0, column=col, sticky="nsew", padx=(0, 8) if col == 0 else (8, 0))
            ttk.Label(frame, textvariable=var, font=("Microsoft YaHei UI", 27, "bold"), foreground="#186a56").pack(anchor="w")
        ttk.Label(self, text="比较：同标的 Put；行权价/现价 ±2 个百分点；DTE ±5 天。", wraplength=820).grid(row=7, column=0, columnspan=3, sticky="w", pady=(14, 3))
        ttk.Label(self, text="百分位 = 历史权利金/股价严格低于当前比例的样本占比；不代表胜率。", wraplength=820).grid(row=8, column=0, columnspan=3, sticky="w")
        ttk.Label(self, text="计算明细与数据覆盖", font=("Microsoft YaHei UI", 11, "bold")).grid(row=9, column=0, columnspan=3, sticky="w", pady=(14, 5))
        self.details = tk.Text(self, height=11, wrap="word", relief="flat", padx=12, pady=10, font=("Microsoft YaHei UI", 10), background="#f3f5f4", state="disabled")
        self.details.grid(row=10, column=0, columnspan=3, sticky="nsew")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.details.yview)
        scrollbar.grid(row=10, column=3, sticky="ns")
        self.details.configure(yscrollcommand=scrollbar.set)
        ttk.Label(self, text="年化假设期权无价值到期且未接货，不是保证收益。接货须按行权价买入 100 股，损失可能远超权利金。", wraplength=820, foreground="#805800").grid(row=11, column=0, columnspan=3, sticky="w", pady=(12, 0))

        self.underlying.trace_add("write", self.ticker_changed)
        self.database_path.trace_add("write", self.database_changed)
        self.spot.trace_add("write", self.spot_changed)
        for var in [self.expiry, self.premium, self.strike]:
            var.trace_add("write", self.invalidate)
        self.reload_symbols()
        self.bind_all("<Return>", lambda event: self.calculate())

    def set_details(self, text):
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", text)
        self.details.configure(state="disabled")

    def invalidate(self, *args):
        self.annual_text.set("—")
        self.percentile_text.set("—")
        self.set_details("")
        self.status.set("输入已更新，请重新计算。")

    def ticker_changed(self, *args):
        self.expiry_box.configure(values=())
        self.spot.set("")
        self._historical_spot = False
        self.spot_source.set("标的已更改，请输入现价或重新读取历史参考价。")
        self.invalidate()

    def database_changed(self, *args):
        self.ticker_changed()
        self.ticker_box.configure(values=())

    def spot_changed(self, *args):
        if not self._loading:
            self._historical_spot = False
            self.spot_source.set("现价来源：手动输入，请与权利金使用同一估值时刻。")
        self.invalidate()

    def choose_database(self):
        path = filedialog.askopenfilename(title="选择期权历史库", filetypes=[("SQLite", "*.db"), ("All", "*.*")])
        if path:
            self.database_path.set(path)
            self.reload_symbols()

    def reload_symbols(self):
        try:
            symbols = ReadOnlyOptionDatabase(self.database_path.get()).underlyings()
            self.ticker_box.configure(values=symbols)
        except Exception as error:
            self.status.set(f"历史库暂不可用，仍可计算年化：{error}")

    def load_reference(self):
        try:
            underlying = normalize_underlying(self.underlying.get())
            history = ReadOnlyOptionDatabase(self.database_path.get()).load_underlying(underlying)
            price, timestamp, expirations = latest_reference(history, underlying, now_utc())
            self.expiry_box.configure(values=expirations)
            if not self.expiry.get() and expirations:
                self.expiry.set(expirations[0])
            self._loading = True
            self.spot.set("" if price is None else f"{price:g}")
            self._historical_spot = price is not None
            self.spot_source.set(f"历史参考价 · {underlying} · {timestamp}（UTC；非实时，可手动覆盖）" if price is not None else "未找到有效历史股价，请手动输入现价。")
            self.status.set("已读取历史参考数据。到期日列表来自历史库，不保证包含当前全部挂牌合约。")
        except Exception as error:
            self.invalidate()
            self.spot.set("")
            self.expiry_box.configure(values=())
            self.status.set(f"读取失败，可手动输入继续：{error}")
        finally:
            self._loading = False

    def calculate(self):
        self.invalidate()
        try:
            underlying = normalize_underlying(self.underlying.get())
            try:
                expiry = date.fromisoformat(self.expiry.get().strip())
            except ValueError as error:
                raise ValueError("到期日请使用 YYYY-MM-DD 格式。") from error
            database_note = ""
            try:
                history = ReadOnlyOptionDatabase(self.database_path.get()).load_underlying(underlying)
            except Exception as error:
                history = pd.DataFrame()
                database_note = f"历史库不可用：{error}"
            as_of = now_utc()
            result = analyze_put_preview(
                underlying=underlying, expiry=expiry, premium=self.premium.get(),
                strike=self.strike.get(), spot=self.spot.get() if self.spot.get().strip() else None,
                as_of=as_of, history=history,
            )
            annual = result.annual
            self.annual_text.set(f"{annual.annualized_return:.2%}")
            self.percentile_text.set(f"{result.premium.premium_percentile:.1f}%" if result.premium else "暂无可比数据")
            lines = [
                f"{underlying} Put  |  {expiry} 到期  |  1 张 / 100 股",
                f"估值时间：{as_of.isoformat()}  |  纽约日期：{get_trading_date(as_of)}",
                f"剩余自然日：{annual.remaining_days:g}  |  行权现金担保：${annual.capital:,.2f}",
                f"权利金收入：${float(self.premium.get()) * 100:,.2f}  |  估算开仓费：${annual.transaction_fee:.2f}  |  净权利金：${annual.potential_profit:,.2f}",
                "费用：富途香港固定式套餐，2026-09-28 费率快照；实际账单取整可能不同。",
                "年化 = 净权利金 / 全额行权现金担保 × 365 / 剩余自然日。",
            ]
            if result.moneyness is not None:
                lines.append(f"行权价/现价：{result.moneyness:.2%}")
            if result.premium:
                p = result.premium
                lines += [
                    f"有效历史样本：{p.sample_count} 条快照，覆盖 {result.trading_days} 个交易日期（非独立交易样本）",
                    f"历史区间：{result.sample_start} 至 {result.sample_end}",
                    f"权利金/股价：当前 {p.current_premium_ratio:.3%}；历史中位数 {p.median_premium_ratio:.3%}；范围 {p.min_premium_ratio:.3%}–{p.max_premium_ratio:.3%}",
                    "历史报价口径：last；输入权利金与历史 last 的成交条件可能不同。",
                ]
            if underlying == "US.IREN":
                met = YieldThresholds().evaluate(annual) == "entry_yield_met"
                lines.append("IREN 示例阈值：" + ("满足初始年化 >30%，仅供进一步判断。" if met else "未满足初始年化 >30%。"))
            notes = list(result.notes)
            if database_note:
                notes.append(database_note)
            if self._historical_spot:
                notes.append("当前使用历史参考股价，建议用与权利金同步的现价核对百分位。")
            self.status.set("；".join(notes) if notes else "计算完成。百分位只反映历史相对位置，不是买卖建议。")
            self.set_details("\n".join(lines))
        except Exception as error:
            self.status.set(f"无法计算：{error}")


def create_root():
    # Keep Windows coordinates consistent with screen pixels on high-DPI displays.
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    root = tk.Tk()
    root.title("Lemon Option Quant — Put 分析")
    scale = max(1, float(root.tk.call("tk", "scaling")) / (96 / 72))
    width = min(int(960 * scale), root.winfo_screenwidth() - 80)
    height = min(int(850 * scale), root.winfo_screenheight() - 100)
    root.geometry(f"{width}x{height}")
    root.minsize(min(int(880 * scale), width), min(int(760 * scale), height))
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", font=("Microsoft YaHei UI", 10))
    style.configure("TButton", padding=7)
    return root


def main(database_path=None):
    root = create_root()
    PutAnalysisWindow(root, Path(database_path) if database_path else Path("data/options.db"))
    root.mainloop()


if __name__ == "__main__":
    main()
