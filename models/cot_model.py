from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

import cot_reports as cot


@dataclass
class CotData:
    report_type: str
    year: int
    df: pd.DataFrame = field(default_factory=pd.DataFrame)
    _markets: list[str] = field(default_factory=list)
    _dates: list[str] = field(default_factory=list)
    start_year: int = 2020

    COL_MARKET = "Market and Exchange Names"
    COL_DATE = "As of Date in Form YYYY-MM-DD"

    CATEGORIES = [
        ("noncommercial", "\u975e\u5546\u4e1a"),
        ("commercial", "\u5546\u4e1a"),
        ("nonreportable", "\u975e\u62a5\u544a"),
        ("total_reportable", "\u62a5\u544a\u5408\u8ba1"),
    ]

    TXT_MAP = {
        "legacy_fut": "annual.txt",
        "legacy_futopt": "annualof.txt",
        "supplemental_futopt": "annualci.txt",
        "disaggregated_fut": "f_year.txt",
        "disaggregated_futopt": "c_year.txt",
        "traders_in_financial_futures_fut": "FinFutYY.txt",
        "traders_in_financial_futures_futopt": "FinComYY.txt",
    }

    def _find_date_col(self) -> str:
        for col in self.df.columns:
            col_lower = col.lower()
            if "date" in col_lower and "yyyy-mm-dd" in col_lower:
                return col
        for col in self.df.columns:
            col_lower = col.lower()
            if "date" in col_lower and ("yyyy" in col_lower or "yymmdd" in col_lower):
                return col
        for col in self.df.columns:
            if "date" in col.lower() and "report" not in col.lower():
                return col
        return self.COL_DATE

    def _find_market_col(self) -> str:
        for col in self.df.columns:
            col_lower = col.lower()
            if "market" in col_lower and "exchange" in col_lower:
                return col
        for col in self.df.columns:
            if "market" in col_lower:
                return col
        return self.COL_MARKET

    def load(self, status_callback: object = None) -> None:
        base = self.TXT_MAP.get(self.report_type, "annualof.txt")
        parts = base.rsplit(".", 1)
        cache_file = f"{parts[0]}_{self.start_year}_{self.year}.{parts[1]}" if self.start_year < self.year else base

        if os.path.exists(cache_file):
            if status_callback:
                status_callback(f"Reading cached {cache_file} ...")
            self.df = pd.read_csv(cache_file, low_memory=False)
        elif os.path.exists(base):
            if status_callback:
                status_callback(f"Reading cached {base} ...")
            self.df = pd.read_csv(base, low_memory=False)
        else:
            if self.report_type not in self.TXT_MAP:
                raise ValueError(f"Unknown report type: {self.report_type}. Valid: {list(self.TXT_MAP)}")
            frames = []
            for y in range(self.start_year, self.year + 1):
                if status_callback:
                    status_callback(f"Downloading {self.report_type} ({y}) ...")
                df_y = cot.cot_year(year=y, cot_report_type=self.report_type, verbose=False)
                frames.append(df_y)
            self.df = pd.concat(frames, ignore_index=True)
            if status_callback:
                status_callback(f"Saving {cache_file} ...")
            try:
                self.df.to_csv(cache_file, index=False)
            except Exception:
                pass

        self._col_date = self._find_date_col()
        self._col_market = self._find_market_col()

        if status_callback:
            status_callback("Parsing dates ...")
        self.df[self._col_date] = pd.to_datetime(self.df[self._col_date], errors="coerce")
        self._markets = sorted(
            str(m) for m in self.df[self._col_market].dropna().unique()
        )
        self._dates = sorted(
            str(d.date()) for d in self.df[self._col_date].dropna().unique()
        )

    @property
    def markets(self) -> list[str]:
        return self._markets

    @property
    def dates(self) -> list[str]:
        return self._dates

    @property
    def latest_date(self) -> str:
        return self._dates[-1] if self._dates else "N/A"

    @property
    def market_count(self) -> int:
        return len(self._markets)

    def filter_by_market(self, market: str) -> pd.DataFrame:
        return self.df[self.df[self._col_market] == market].sort_values(
            self._col_date, ascending=False
        )

    def filter_latest(self) -> pd.DataFrame:
        if self._dates:
            latest = self._dates[-1]
            return self.df[pd.to_datetime(self.df[self._col_date]).dt.date.astype(str) == latest]
        return self.df

    def search_markets(self, query: str) -> list[str]:
        q = query.lower()
        return [m for m in self._markets if q in m.lower()]

    def _cat_rx(self, category: str) -> str:
        parts = category.split("_")
        return r"\b" + r"\s+".join(parts) + r"\b"

    def _col(self, pattern: str) -> str | None:
        rx = re.compile(pattern, re.IGNORECASE)
        for c in self.df.columns:
            if rx.search(c):
                return c
        return None

    def get_oi_col(self) -> str | None:
        return self._col(r"^open\s*interest")

    def get_oi_change_col(self) -> str | None:
        return self._col(r"^change\s+in\s+open\s*interest")

    def get_long_col(self, category: str) -> str | None:
        return self._col(rf"{self._cat_rx(category)}.*positions?\W*[-–]?\W*long")

    def get_short_col(self, category: str) -> str | None:
        return self._col(rf"{self._cat_rx(category)}.*positions?\W*[-–]?\W*short")

    def get_spread_col(self, category: str) -> str | None:
        return self._col(rf"{self._cat_rx(category)}.*positions?\W*[-–]?\W*spread")

    def get_long_change_col(self, category: str) -> str | None:
        return self._col(rf"change\s+in\s+{self._cat_rx(category)}\W*[-–]?\W*long")

    def get_short_change_col(self, category: str) -> str | None:
        return self._col(rf"change\s+in\s+{self._cat_rx(category)}\W*[-–]?\W*short")

    def get_pct_long_col(self, category: str) -> str | None:
        return self._col(rf"%\s*(of\s*oi)?\W*{self._cat_rx(category)}.*long")

    def get_pct_short_col(self, category: str) -> str | None:
        return self._col(rf"%\s*(of\s*oi)?\W*{self._cat_rx(category)}.*short")

    def safe_val(self, row: pd.Series, col: str | None) -> float:
        if col is None or col not in row.index:
            return 0.0
        v = row[col]
        try:
            return float(str(v).replace(",", ""))
        except (ValueError, TypeError):
            return 0.0

    def safe_str(self, row: pd.Series, col: str | None) -> str:
        if col is None or col not in row.index:
            return "-"
        return str(row[col])

    def get_market_summary(self, market: str) -> list[dict[str, Any]]:
        """Return a list of rows for the data table (one per date)."""
        sub = self.filter_by_market(market)
        rows = []
        cat_map = {k: v for k, v in self.CATEGORIES}

        for _, row in sub.iterrows():
            r: dict[str, Any] = {
                "date": str(row[self._col_date].date()) if pd.notna(row[self._col_date]) else "-",
                "market": str(row[self._col_market]),
                "oi": self.safe_val(row, self.get_oi_col()),
            }
            for cat_key, cat_label in self.CATEGORIES:
                longs = self.safe_val(row, self.get_long_col(cat_key))
                shorts = self.safe_val(row, self.get_short_col(cat_key))
                r[f"{cat_key}_long"] = longs
                r[f"{cat_key}_short"] = shorts
                r[f"{cat_key}_net"] = longs - shorts
                r[f"{cat_key}_change_long"] = self.safe_val(row, self.get_long_change_col(cat_key))
                r[f"{cat_key}_change_short"] = self.safe_val(row, self.get_short_change_col(cat_key))
                r[f"{cat_key}_spread"] = self.safe_val(row, self.get_spread_col(cat_key))
            rows.append(r)
        return rows

    def get_market_detail(self, market: str, date_str: str | None = None) -> dict[str, Any]:
        sub = self.filter_by_market(market)
        if sub.empty:
            return {}

        if date_str:
            mask = pd.to_datetime(sub[self._col_date]).dt.date.astype(str) == date_str
            if mask.any():
                sub = sub[mask]

        row = sub.iloc[0]
        detail: dict[str, Any] = {
            "market": str(row[self._col_market]),
            "date": str(row[self._col_date].date()) if pd.notna(row[self._col_date]) else "-",
            "oi": self.safe_val(row, self.get_oi_col()),
            "oi_change": self.safe_val(row, self.get_oi_change_col()),
        }
        detail["categories"] = {}
        for cat_key, cat_label in self.CATEGORIES:
            longs = self.safe_val(row, self.get_long_col(cat_key))
            shorts = self.safe_val(row, self.get_short_col(cat_key))
            spread = self.safe_val(row, self.get_spread_col(cat_key))
            chg_longs = self.safe_val(row, self.get_long_change_col(cat_key))
            chg_shorts = self.safe_val(row, self.get_short_change_col(cat_key))
            pct_longs = self.safe_val(row, self.get_pct_long_col(cat_key))
            pct_shorts = self.safe_val(row, self.get_pct_short_col(cat_key))

            detail["categories"][cat_label] = {
                "long": longs,
                "short": shorts,
                "net": longs - shorts,
                "spread": spread,
                "change_long": chg_longs,
                "change_short": chg_shorts,
                "pct_long": pct_longs,
                "pct_short": pct_shorts,
            }
        return detail

    def to_analysis_context(self, market_filter: str | None = None) -> str:
        """Build a text prompt for DeepSeek analysis from current data."""
        lines = [
            f"CFTC {self.report_type} report, year {self.year}",
            f"Latest report date: {self.latest_date}",
        ]

        if market_filter:
            market_detail = self.get_market_detail(market_filter)
            if market_detail:
                lines.append(f"Selected Market: {market_filter}")
                lines.append(f"Open Interest: {market_detail.get('oi', 0):,.0f}")
                oi_chg = market_detail.get("oi_change", 0)
                lines.append(f"OI Change: {oi_chg:+,.0f}")
                lines.append("")
                for cat_label, cat_data in market_detail.get("categories", {}).items():
                    net = cat_data["net"]
                    lines.append(f"{cat_label} (非商业/商业/非报告/报告合计):")
                    lines.append(f"  Long: {cat_data['long']:>10,.0f}  Short: {cat_data['short']:>10,.0f}  Net: {net:+,.0f}  Spread: {cat_data.get('spread', 0):,.0f}")
                    chg_l = cat_data.get("change_long", 0)
                    chg_s = cat_data.get("change_short", 0)
                    lines.append(f"  Change: Long {chg_l:+,.0f}  Short {chg_s:+,.0f}")
                    lines.append("")

        sub = self.filter_latest()
        lines.append("---")
        lines.append(f"Total markets in latest report: {len(sub)}")

        nc_long = self.get_long_col("noncommercial")
        nc_short = self.get_short_col("noncommercial")

        if nc_long and nc_short:
            sub_copy = sub.copy()
            sub_copy["__nc_net"] = (sub_copy[nc_long].fillna(0).astype(float) -
                                     sub_copy[nc_short].fillna(0).astype(float))
            top_long = sub_copy.nlargest(5, "__nc_net")
            top_short = sub_copy.nsmallest(5, "__nc_net")

            lines.append("")
            lines.append("Top 5 Non-commercial Net Long (全部市场):")
            for _, r in top_long.iterrows():
                lines.append(
                    f"  {r[self._col_market]}: 多头 {self.safe_val(r, nc_long)}  "
                    f"空头 {self.safe_val(r, nc_short)}  净 {self.safe_val(r, nc_long) - self.safe_val(r, nc_short)}"
                )
            lines.append("")
            lines.append("Top 5 Non-commercial Net Short (全部市场):")
            for _, r in top_short.iterrows():
                lines.append(
                    f"  {r[self._col_market]}: 多头 {self.safe_val(r, nc_long)}  "
                    f"空头 {self.safe_val(r, nc_short)}  净 {self.safe_val(r, nc_long) - self.safe_val(r, nc_short)}"
                )

        return "\n".join(lines)

    def get_cot_index(self, market: str, category: str = "noncommercial") -> float | None:
        """COT Index: where current net position sits in historical range (0-100).
        > 80 = extreme long, < 20 = extreme short."""
        long_col = self.get_long_col(category)
        short_col = self.get_short_col(category)
        if not long_col or not short_col:
            return None
        sub = self.filter_by_market(market)
        if sub.empty:
            return None
        nets = (sub[long_col].fillna(0).astype(float) - sub[short_col].fillna(0).astype(float))
        if len(nets) < 2:
            return None
        lo, hi = nets.min(), nets.max()
        if hi == lo:
            return 50.0
        current = nets.iloc[0]
        return round((current - lo) / (hi - lo) * 100, 1)

    def get_sparkline(self, market: str, category: str = "noncommercial", width: int = 30) -> str:
        """ASCII sparkline of net position trend over time."""
        long_col = self.get_long_col(category)
        short_col = self.get_short_col(category)
        if not long_col or not short_col:
            return ""
        sub = self.filter_by_market(market)
        if sub.empty:
            return ""
        nets = (sub[long_col].fillna(0).astype(float) - sub[short_col].fillna(0).astype(float))
        if len(nets) < 2:
            return ""
        values = nets.values[::-1]
        lo, hi = values.min(), values.max()
        if hi == lo:
            return "\u2500" * width
        chars = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
        n = len(chars) - 1
        step = max(width // len(values), 1)
        result = ""
        for i, v in enumerate(values):
            idx = max(0, min(n, int((v - lo) / (hi - lo) * n)))
            result += chars[idx] * step
        return result
