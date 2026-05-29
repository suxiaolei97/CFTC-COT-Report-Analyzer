from __future__ import annotations

import re as _re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests

_TENCENT_QUOTE_URL = "http://qt.gtimg.cn/q="

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
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=6)
        self._quotes: dict[str, dict] = {}
        self._quotes_updated: bool = False
        self._chart_ready: bool = False
        self._chart_prices: list[float] = []

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)

    def fetch_all(self, symbols: list[str] | None = None) -> None:
        self._quotes = {}
        self._executor.submit(self._do_fetch_all, list(symbols or MAJOR_STOCKS))

    def fetch_chart(self, symbol: str) -> None:
        self._chart_ready = False
        self._executor.submit(self._do_fetch_chart, symbol)

    def dynamic_fetch(self, symbol: str) -> None:
        self._executor.submit(self._do_dynamic_fetch, symbol)

    def _fetch_quote(self, sym: str) -> dict:
        url = f"https://api.nasdaq.com/api/quote/{sym}/info?assetclass=stocks"
        default = {"symbol": sym, "price": 0, "change": 0, "change_pct": 0, "name": sym, "nodata": True}
        try:
            hdr = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
            r = requests.get(url, headers=hdr, timeout=6)
            if r.status_code != 200:
                return default
            d = r.json()
            data = d.get("data", {}) or {}
            primary = data.get("primaryData", {}) or {}
            ps = primary.get("lastSalePrice", "").replace("$", "").replace(",", "")
            cs = primary.get("netChange", "").replace("$", "").replace(",", "")
            pcts = primary.get("percentageChange", "").replace("%", "")
            price = float(ps) if ps and ps != "N/A" else 0
            chg = float(cs) if cs and cs != "N/A" else 0
            chg_pct = float(pcts) if pcts and pcts != "N/A" else 0
            summary = data.get("summaryData", {}) or {}
            pe = (summary.get("P/E", {}) or {}).get("value", "")
            return {"symbol": sym, "price": price, "change": chg, "change_pct": chg_pct,
                    "name": data.get("companyName", sym) or sym, "pe": pe}
        except Exception:
            return default

    def _do_fetch_all(self, symbols: list[str]) -> None:
        result = {}
        batch_size = 60
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            qs = ",".join(f"us{s}" for s in batch)
            try:
                r = requests.get(_TENCENT_QUOTE_URL + qs, timeout=15)
                if r.status_code == 200:
                    for line in r.text.strip().split("\n"):
                        line = line.strip()
                        if not line or "=" not in line:
                            continue
                        m = _re.search(r'v_us(\w+)="(.*)"', line)
                        if m:
                            sym = m.group(1)
                            vals = m.group(2).split("~")
                            if len(vals) > 33:
                                result[sym] = {
                                    "symbol": sym,
                                    "price": float(vals[3]) if vals[3] else 0,
                                    "change": float(vals[31]) if vals[31] else 0,
                                    "change_pct": float(vals[32]) if vals[32] else 0,
                                    "name": vals[46] if len(vals) > 46 and vals[46] else vals[1],
                                    "market_cap": vals[44] if len(vals) > 44 else "",
                                    "pe": vals[47] if len(vals) > 47 else "",
                                    "high_52w": vals[48] if len(vals) > 48 else "",
                                    "low_52w": vals[49] if len(vals) > 49 else "",
                                    "high": vals[33] if len(vals) > 33 else "",
                                    "low": vals[34] if len(vals) > 34 else "",
                                }
            except Exception:
                pass
        self._quotes = result
        self._quotes_updated = True

    def _do_dynamic_fetch(self, symbol: str) -> None:
        self._quotes[symbol] = self._fetch_quote(symbol)
        self._quotes_updated = True

    def _do_fetch_chart(self, symbol: str) -> None:
        prices: list[float] = []
        hdr = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        try:
            r = requests.get(
                f"https://api.nasdaq.com/api/quote/{symbol}/chart?assetclass=stocks&fromdate=2026-04-01&todate=2026-05-31",
                headers=hdr, timeout=10)
            if r.status_code == 200:
                d = r.json()
                chart = (d.get("data", {}) or {}).get("chart", []) or []
                for c in chart:
                    try:
                        p = float(c.get("z", {}).get("close", 0) or 0)
                        if p:
                            prices.append(p)
                    except (ValueError, TypeError):
                        pass
        except Exception:
            pass
        self._chart_prices = prices
        self._chart_ready = True

    @staticmethod
    def sparkline(prices: list[float], width: int = 25) -> str:
        clean = [p for p in prices if p > 0]
        if len(clean) < 2:
            return ""
        lo, hi = min(clean), max(clean)
        if hi == lo:
            return "\u2500" * width
        chars = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
        n = len(chars) - 1
        step = max(width // len(clean), 1)
        result = ""
        for v in clean:
            idx = max(0, min(n, int((v - lo) / (hi - lo) * n)))
            result += chars[idx] * step
        return result
