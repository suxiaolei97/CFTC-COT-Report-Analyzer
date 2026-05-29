from __future__ import annotations

import json
import time as time_mod
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pandas as pd
import requests

_NASDAQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

_COMMODITY_STOCKS = {
    "GOLD":     ["GLD", "GDX", "NEM"],
    "SILVER":   ["SLV", "SIL"],
    "OIL":      ["USO", "XLE", "CVX"],
    "CORN":     ["CORN", "ADM"],
    "NAT_GAS":  ["UNG", "BOIL"],
    "COPPER":   ["COPX", "FCX"],
    "SOYBEAN":  ["SOYB", "ADM"],
    "WHEAT":    ["WEAT"],
    "SUGAR":   ["CANE"],
}


class StockModel:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=3)
        self._quotes_ready: bool = False
        self._info_ready: bool = False
        self._intraday_ready: bool = False
        self._quotes: dict[str, dict] = {}
        self._info: dict[str, Any] = {}
        self._intraday_data: list[float] = []
        self._intraday_symbol: str = ""
        self._error: str = ""

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)

    def fetch_quotes(self, symbols: list[str]) -> None:
        self._quotes_ready = False
        self._error = ""
        self._executor.submit(self._do_fetch_quotes, list(symbols))

    def fetch_info(self, symbol: str) -> None:
        self._info_ready = False
        self._info = {}
        self._executor.submit(self._do_fetch_info, symbol)

    def fetch_intraday(self, symbol: str) -> None:
        self._intraday_ready = False
        self._intraday_symbol = symbol
        self._executor.submit(self._do_fetch_intraday, symbol)

    def _fetch_quote(self, symbol: str) -> dict:
        url = f"https://api.nasdaq.com/api/quote/{symbol}/info?assetclass=stocks"
        try:
            r = requests.get(url, headers=_NASDAQ_HEADERS, timeout=8)
            if r.status_code == 200:
                d = r.json()
                data = d.get("data", {}) or {}
                primary = data.get("primaryData", {}) or {}
                price_str = primary.get("lastSalePrice", "").replace("$", "").replace(",", "")
                chg_str = primary.get("netChange", "").replace("$", "").replace(",", "")
                pct_str = primary.get("percentageChange", "").replace("%", "")
                price = float(price_str) if price_str and price_str != "N/A" else 0
                chg = float(chg_str) if chg_str and chg_str != "N/A" else 0
                chg_pct = float(pct_str) if pct_str and pct_str != "N/A" else 0
                return {
                    "symbol": symbol,
                    "price": price,
                    "change": chg,
                    "change_pct": chg_pct,
                    "name": data.get("companyName", symbol) or symbol,
                    "currency": "USD",
                }
        except Exception:
            pass
        return {"symbol": symbol, "price": 0, "change": 0, "change_pct": 0, "name": symbol, "nodata": True}

    def _do_fetch_quotes(self, symbols: list[str]) -> None:
        result = {}
        for i, sym in enumerate(symbols):
            if i > 0:
                time_mod.sleep(0.3)
            result[sym] = self._fetch_quote(sym)
        self._quotes = result
        self._quotes_ready = True

    def _do_fetch_info(self, symbol: str) -> None:
        url = f"https://api.nasdaq.com/api/quote/{symbol}/info?assetclass=stocks"
        try:
            r = requests.get(url, headers=_NASDAQ_HEADERS, timeout=8)
            if r.status_code == 200:
                d = r.json()
                data = d.get("data", {}) or {}
                primary = data.get("primaryData", {}) or {}
                summary = d.get("summaryData", data.get("summaryData", {})) or {}
                self._info = {
                    "symbol": symbol,
                    "name": data.get("companyName", symbol) or symbol,
                    "sector": data.get("sector", ""),
                    "industry": data.get("industry", ""),
                    "market_cap": summary.get("MarketCap", {}).get("value"),
                    "pe_ratio": summary.get("P/E", {}).get("value") or summary.get("PriceEarnings", {}).get("value"),
                    "dividend_yield": summary.get("Yield", {}).get("value"),
                    "52w_high": summary.get("AnnualHigh", {}).get("value"),
                    "52w_low": summary.get("AnnualLow", {}).get("value"),
                    "avg_volume": summary.get("AverageVolume", {}).get("value"),
                    "eps": summary.get("EPS", {}).get("value"),
                    "currency": "USD",
                }
                return
        except Exception:
            pass
        self._info = {"symbol": symbol, "name": symbol, "error": True}
        self._info_ready = True

    def _do_fetch_intraday(self, symbol: str) -> None:
        self._intraday_data = []
        self._intraday_ready = True

    def get_sparkline(self, width: int = 40) -> str:
        prices = self._intraday_data
        if len(prices) < 2:
            return ""
        lo, hi = min(prices), max(prices)
        if hi == lo:
            return "\u2500" * width
        chars = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
        n = len(chars) - 1
        step = max(width // len(prices), 1)
        result = ""
        for v in prices:
            idx = max(0, min(n, int((v - lo) / (hi - lo) * n)))
            result += chars[idx] * step
        return result
