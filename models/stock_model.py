from __future__ import annotations

import time as time_mod
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests

_NASDAQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

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
        self._quotes_done: bool = False
        self._info_ready: bool = False
        self._info: dict[str, Any] = {}
        self._chart_ready: bool = False
        self._chart_prices: list[float] = []

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)

    def fetch_all(self, symbols: list[str] | None = None) -> None:
        self._quotes = {}
        self._quotes_done = False
        self._quotes_updated = False
        self._executor.submit(self._do_fetch_all, list(symbols or MAJOR_STOCKS))

    def fetch_info(self, symbol: str) -> None:
        self._info_ready = False
        self._chart_ready = False
        self._info = {}
        self._executor.submit(self._do_fetch_info, symbol)
        self._executor.submit(self._do_fetch_chart, symbol)

    def _fetch_quote(self, sym: str) -> dict:
        url = f"https://api.nasdaq.com/api/quote/{sym}/info?assetclass=stocks"
        try:
            r = requests.get(url, headers=_NASDAQ_HEADERS, timeout=6)
            if r.status_code == 200:
                d = r.json()
                data = d.get("data", {}) or {}
                primary = data.get("primaryData", {}) or {}
                ps = primary.get("lastSalePrice", "").replace("$", "").replace(",", "")
                cs = primary.get("netChange", "").replace("$", "").replace(",", "")
                pcts = primary.get("percentageChange", "").replace("%", "")
                price = float(ps) if ps and ps != "N/A" else 0
                chg = float(cs) if cs and cs != "N/A" else 0
                chg_pct = float(pcts) if pcts and pcts != "N/A" else 0
                return {"symbol": sym, "price": price, "change": chg, "change_pct": chg_pct,
                        "name": data.get("companyName", sym) or sym}
        except Exception:
            pass
        return {"symbol": sym, "price": 0, "change": 0, "change_pct": 0, "name": sym, "nodata": True}

    def _do_fetch_all(self, symbols: list[str]) -> None:
        for sym in symbols:
            self._quotes[sym] = self._fetch_quote(sym)
            self._quotes_updated = True
            time_mod.sleep(0.02)
        self._quotes_done = True
        self._quotes_updated = True

    def _do_fetch_info(self, symbol: str) -> None:
        url = f"https://api.nasdaq.com/api/quote/{symbol}/info?assetclass=stocks"
        try:
            r = requests.get(url, headers=_NASDAQ_HEADERS, timeout=6)
            if r.status_code == 200:
                d = r.json()
                data = d.get("data", {}) or {}
                summary = data.get("summaryData", {}) or {}
                self._info = {
                    "symbol": symbol, "name": data.get("companyName", symbol) or symbol,
                    "sector": data.get("sector", ""), "industry": data.get("industry", ""),
                    "market_cap": (summary.get("MarketCap", {}) or {}).get("value"),
                    "pe_ratio": (summary.get("P/E", {}) or {}).get("value"),
                    "dividend_yield": (summary.get("Yield", {}) or {}).get("value"),
                    "52w_high": (summary.get("AnnualHigh", {}) or {}).get("value"),
                    "52w_low": (summary.get("AnnualLow", {}) or {}).get("value"),
                    "avg_volume": (summary.get("AverageVolume", {}) or {}).get("value"),
                    "eps": (summary.get("EPS", {}) or {}).get("value"), "currency": "USD",
                }
                return
        except Exception:
            pass
        self._info = {"symbol": symbol, "name": symbol, "error": True}
        self._info_ready = True

    def _do_fetch_chart(self, symbol: str) -> None:
        url = f"https://api.nasdaq.com/api/quote/{symbol}/chart?assetclass=stocks&fromdate=2026-05-01&todate=2026-05-31"
        try:
            r = requests.get(url, headers=_NASDAQ_HEADERS, timeout=8)
            if r.status_code == 200:
                d = r.json()
                chart = (d.get("data", {}) or {}).get("chart", []) or []
                prices = []
                for c in chart:
                    try:
                        prices.append(float(c.get("z", {}).get("close", 0) or 0))
                    except (ValueError, TypeError):
                        pass
                self._chart_prices = prices
        except Exception:
            self._chart_prices = []
        self._chart_ready = True

    @staticmethod
    def sparkline(prices: list[float], width: int = 20) -> str:
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
