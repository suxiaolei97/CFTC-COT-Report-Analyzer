from __future__ import annotations

import re as _re
from concurrent.futures import ThreadPoolExecutor

import requests

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Input, Label, RichLog, Static

from rich.text import Text as RichText

from i18n import t

_TENCENT = "http://qt.gtimg.cn/q="

MAJOR_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRKB",
    "JPM", "V", "JNJ", "WMT", "UNH", "MA", "PG", "HD", "BAC", "XOM",
    "CVX", "PFE", "ABBV", "KO", "PEP", "MRK", "AVGO", "COST", "TMO",
    "CSCO", "ORCL", "ADBE", "CRM", "AMD", "INTC", "QCOM", "INTU", "TXN",
    "NFLX", "DIS", "CMCSA", "VZ", "T", "NKE", "PYPL", "ABT", "DHR",
    "IBM", "GE", "CAT", "BA", "HON", "LMT", "RTX", "GS", "MS", "C",
    "WFC", "BLK", "AXP", "SPGI", "PLTR", "UBER", "SQ", "SNAP", "ZM",
    "DOCU", "CRWD", "SNOW", "MRNA", "PINS", "NET", "DDOG", "ZS", "OKTA",
    "TEAM", "SPOT", "RBLX", "COIN", "HOOD", "RIVN", "LCID", "AFRM",
    "ETSY", "DASH", "ABNB", "ROKU", "TTD", "DKNG", "SOFI", "UPST",
]


class StockModel:
    def __init__(self):
        self._exec = ThreadPoolExecutor(max_workers=8)
        self._quotes: dict = {}
        self._quotes_updated = False
        self._info: dict = {}
        self._info_ready = False

    def shutdown(self):
        self._exec.shutdown(wait=False)

    def fetch_all(self, syms=None):
        self._quotes = {}
        self._exec.submit(self._do_fetch_all, list(syms or MAJOR_STOCKS))

    def fetch_detail(self, sym):
        self._info_ready = False
        self._exec.submit(self._do_fetch_detail, sym)

    def dynamic_fetch(self, sym):
        self._exec.submit(self._do_dynamic, sym)

    def _do_fetch_all(self, syms):
        result = {}
        for i in range(0, len(syms), 60):
            batch = syms[i:i + 60]
            qs = ",".join(f"us{s}" for s in batch)
            try:
                r = requests.get(_TENCENT + qs, timeout=15)
                if r.status_code == 200:
                    for line in r.text.strip().split("\n"):
                        line = line.strip()
                        if not line or "=" not in line:
                            continue
                        m = _re.search(r'v_us(\w+)="(.*)"', line)
                        if m:
                            s = m.group(1)
                            v = m.group(2).split("~")
                            if len(v) > 49:
                                result[s] = {
                                    "symbol": s, "price": self._f(v, 3),
                                    "prev_close": self._f(v, 4), "open": self._f(v, 5),
                                    "volume": v[6] if v[6] else "0",
                                    "high": self._f(v, 33), "low": self._f(v, 34),
                                    "change": self._f(v, 31), "change_pct": self._f(v, 32),
                                    "name": v[46] if len(v) > 46 and v[46] else v[1],
                                    "pe": v[47] if len(v) > 47 else "",
                                    "market_cap": v[44] if len(v) > 44 else "",
                                    "high_52w": v[48] if len(v) > 48 else "",
                                    "low_52w": v[49] if len(v) > 49 else "",
                                    "amplitude": v[38] if len(v) > 38 else "",
                                    "turnover": v[39] if len(v) > 39 else "",
                                    "amount": v[37] if len(v) > 37 else "",
                                    "bid": self._f(v, 9), "ask": self._f(v, 19),
                                    "currency": "USD",
                                }
            except Exception:
                pass
        self._quotes = result
        self._quotes_updated = True

    def _do_dynamic(self, sym):
        qs = f"us{sym}"
        try:
            r = requests.get(_TENCENT + qs, timeout=8)
            if r.status_code == 200:
                for line in r.text.strip().split("\n"):
                    m = _re.search(r'v_us(\w+)="(.*)"', line.strip())
                    if m:
                        v = m.group(2).split("~")
                        if len(v) > 49:
                            self._quotes[m.group(1)] = {
                                "symbol": m.group(1), "price": self._f(v, 3),
                                "prev_close": self._f(v, 4), "open": self._f(v, 5),
                                "volume": v[6] if v[6] else "0",
                                "high": self._f(v, 33), "low": self._f(v, 34),
                                "change": self._f(v, 31), "change_pct": self._f(v, 32),
                                "name": v[46] if len(v) > 46 and v[46] else v[1],
                                "pe": v[47] if len(v) > 47 else "",
                                "market_cap": v[44] if len(v) > 44 else "",
                                "high_52w": v[48] if len(v) > 48 else "",
                                "low_52w": v[49] if len(v) > 49 else "",
                                "amplitude": v[38] if len(v) > 38 else "",
                                "turnover": v[39] if len(v) > 39 else "",
                                "amount": v[37] if len(v) > 37 else "",
                                "bid": self._f(v, 9), "ask": self._f(v, 19),
                                "currency": "USD",
                            }
        except Exception:
            pass
        self._quotes_updated = True

    def _do_fetch_detail(self, sym):
        info = {"symbol": sym, "name": sym}
        try:
            hdr = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
            r = requests.get(
                f"https://api.nasdaq.com/api/quote/{sym}/info?assetclass=stocks",
                headers=hdr, timeout=8)
            if r.status_code == 200:
                d = r.json().get("data", {}) or {}
                info["name"] = d.get("companyName", sym) or sym
                info["exchange"] = d.get("exchange", "")
                info["sector"] = d.get("sector", "")
                info["industry"] = d.get("industry", "")
                summary = d.get("summaryData", {}) or {}
                for k in summary:
                    info[k] = summary[k]
                ks = d.get("keyStats", {}) or {}
                for k in ks:
                    info[k] = ks[k]
        except Exception:
            pass
        info.update(self._quotes.get(sym, {}))
        self._info = info
        self._info_ready = True

    @staticmethod
    def _f(arr, idx):
        try:
            return float(arr[idx]) if arr[idx] else 0.0
        except (ValueError, IndexError):
            return 0.0


class StockScreen(Screen[None]):
    CSS = """
    StockScreen { layout: horizontal; background: #0f0f1a; }
    #stock-left { width: 3fr; height: 100%; padding: 1; border-right: thick #2a2a5a; }
    #stock-right { width: 4fr; height: 100%; padding: 1; }
    #stock-search { width: 100%; margin-bottom: 1; }
    #stock-table-container { height: 100%; border: solid #2a2a5a; background: #16162a; }
    #stock-table { height: 100%; }
    #stock-info { height: 100%; border: solid #2a2a5a; background: #16162a; }
    #stock-info-title { color: #7aafff; text-style: bold; height: 1; padding: 0 1; background: #1a1a3a; }
    #stock-info-log { height: 1fr; }
    #stock-hint { height: 1; padding: 0 1; margin-top: 1; background: #1a1a3a; color: #c0c0e0; }
    #stock-count { color: #606080; }
    #stock-left-top { height: auto; margin-bottom: 1; }
    """

    def __init__(self):
        super().__init__()
        self.title = "Stock Market"
        self.model = StockModel()
        self._selected = ""
        self._last_query = ""
        self._last_count = 0

    def compose(self):
        with Container(id="stock-left"):
            with Horizontal(id="stock-left-top"):
                yield Input(placeholder=t("search"), id="stock-search")
                yield Static("Loading...", id="stock-count")
            with Container(id="stock-table-container"):
                yield DataTable(id="stock-table", cursor_type="row")
            yield Static(f"F3: COT  |  {t('stock_auto_refresh')}", id="stock-hint")

        with Container(id="stock-right"):
            with Container(id="stock-info"):
                yield Label(t("stock_detail"), id="stock-info-title")
                yield RichLog(id="stock-info-log", highlight=True, markup=True, wrap=True)

    def on_mount(self):
        self.model.fetch_all()
        self.set_interval(0.1, self._poll)

    def _poll(self):
        updated = False
        if self.model._quotes_updated:
            self.model._quotes_updated = False
            updated = True
        if self.model._info_ready:
            self._show_detail()
            self.model._info_ready = False
        if updated:
            self._update_table()
            self._last_count = len(self.model._quotes)
            try:
                self.query_one("#stock-count", Static).update(f"{self._last_count} stocks")
            except Exception:
                pass

    def _row(self, sym, q):
        pr = q.get("price", 0)
        pct = q.get("change_pct", 0)
        nm = q.get("name", sym)
        if not pr:
            return (sym, RichText(nm[:18], style="dim"), RichText("--", style="dim"), RichText("--", style="dim"))
        cs = "bold green" if pct >= 0 else "bold red"
        return (RichText(sym, style=cs), RichText(nm[:18], style=""),
                RichText(f"{pr:.2f}", style=cs),
                RichText(f"{pct:+.2f}%", style="bold green" if pct >= 0 else "bold red"))

    def _update_table(self):
        try:
            dt = self.query_one("#stock-table", DataTable)
            dt.clear(columns=True)
            dt.add_columns(t("symbol"), t("stock_name"), t("stock_price"), t("stock_change"))
            for s in sorted(self.model._quotes.keys()):
                dt.add_row(*self._row(s, self.model._quotes[s]))
        except Exception:
            pass

    def on_input_changed(self, event):
        if event.input.id != "stock-search":
            return
        q = event.value.strip().upper()
        if q == self._last_query:
            return
        self._last_query = q
        if not self.model._quotes:
            return
        try:
            dt = self.query_one("#stock-table", DataTable)
            dt.clear(columns=True)
            dt.add_columns(t("symbol"), t("stock_name"), t("stock_price"), t("stock_change"))
            for s in sorted(self.model._quotes.keys()):
                d = self.model._quotes[s]
                nm = str(d.get("name", s))
                if q and q not in s.upper() and q.upper() not in nm.upper():
                    continue
                dt.add_row(*self._row(s, d))
            if q and q not in self.model._quotes:
                self.model.dynamic_fetch(q)
        except Exception:
            pass

    def on_data_table_row_highlighted(self, event):
        try:
            dt = self.query_one("#stock-table", DataTable)
            sym = str(dt.get_row(event.row_key)[0])
            if sym == self._selected:
                return
            self._selected = sym
            self.model.fetch_detail(sym)
        except Exception:
            pass

    def _show_detail(self):
        try:
            log = self.query_one("#stock-info-log", RichLog)
            log.clear()
            q = self.model._info
            if not q:
                return
            sym = q.get("symbol", self._selected)
            name = q.get("name", sym)
            pr = q.get("price", 0)
            pct = q.get("change_pct", 0)
            c = "green" if pct >= 0 else "red"
            log.write(f"[bold]{name} ({sym})[/]")
            log.write(f"[{c}]${pr:.2f}  {pct:+.2f}%[/]")
            log.write("")
            rows = [
                (t("stock_sector"), q.get("sector", "")),
                ("Industry", q.get("industry", "")),
                ("Exchange", q.get("exchange", "")),
                ("", ""),
                ("Open", self._fmt(q, "open")),
                ("Prev Close", self._fmt(q, "prev_close")),
                ("High", self._fmt(q, "high")),
                ("Low", self._fmt(q, "low")),
                ("Bid", self._fmt_bidask(q, "bid")),
                ("Ask", self._fmt_bidask(q, "ask")),
                ("Volume", f"{q.get('volume', '0')}"),
                ("Amount", q.get("amount", "")),
                ("Amplitude", f"{q.get('amplitude', '')}%" if q.get("amplitude") else ""),
                ("Turnover", f"{q.get('turnover', '')}%" if q.get("turnover") else ""),
                ("", ""),
                ("PE", q.get("pe", "")),
                ("Market Cap", q.get("market_cap", "")),
                ("52W High", q.get("high_52w", "")),
                ("52W Low", q.get("low_52w", "")),
            ]
            for label, val in rows:
                if val:
                    log.write(f"{label}: {val}")
                else:
                    log.write(label)
        except Exception:
            pass

    @staticmethod
    def _fmt(q, key):
        v = q.get(key, 0)
        return f"{v:.2f}" if v else ""

    @staticmethod
    def _fmt_bidask(q, key):
        v = q.get(key, 0)
        return f"{v:.2f}" if v else ""
