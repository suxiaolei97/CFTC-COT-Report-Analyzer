from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pandas as pd


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
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._quotes_ready: bool = False
        self._info_ready: bool = False
        self._intraday_ready: bool = False
        self._quotes: dict[str, dict] = {}
        self._info: dict[str, Any] = {}
        self._intraday_df: pd.DataFrame | None = None
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

    def _do_fetch_quotes(self, symbols: list[str]) -> None:
        try:
            import yfinance as yf
        except ImportError:
            self._error = "yfinance not installed"
            self._quotes = {}
            self._quotes_ready = True
            return
        import time
        result = {}
        rate_limited = False
        for sym in symbols:
            if rate_limited:
                result[sym] = {"symbol": sym, "price": 0, "change": 0, "change_pct": 0, "name": sym, "rate_limited": True}
                continue
            try:
                t = yf.Ticker(sym)
                time.sleep(1.5)
                info = t.info
                price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
                prev = info.get("regularMarketPreviousClose") or info.get("previousClose")
                chg = info.get("regularMarketChange") or 0
                chg_pct_val = info.get("regularMarketChangePercent") or 0
                if isinstance(chg_pct_val, float):
                    chg_pct = chg_pct_val
                elif price and prev:
                    chg = (price - prev) if price and prev else 0
                    chg_pct = (chg / prev) * 100 if prev else 0
                else:
                    chg_pct = 0
                result[sym] = {
                    "symbol": sym,
                    "price": float(price) if price else 0,
                    "change": float(chg) if chg else 0,
                    "change_pct": float(chg_pct) if chg_pct else 0,
                    "name": info.get("longName") or info.get("shortName") or sym,
                    "currency": info.get("currency", "USD") or "USD",
                }
            except Exception as e:
                msg = str(e).lower()
                if "rate limit" in msg or "too many" in msg:
                    rate_limited = True
                    self._error = "Yahoo Finance rate limited. Try again later."
                result[sym] = {"symbol": sym, "price": 0, "change": 0, "change_pct": 0, "name": sym, "error": "rate_limited" if rate_limited else True}
        self._quotes = result
        self._quotes_ready = True

    def _do_fetch_info(self, symbol: str) -> None:
        try:
            import yfinance as yf
            t = yf.Ticker(symbol)
            info = t.info
            self._info = {
                "symbol": symbol,
                "name": info.get("longName", symbol),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "dividend_yield": info.get("dividendYield"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "avg_volume": info.get("averageVolume"),
                "beta": info.get("beta"),
                "eps": info.get("trailingEps"),
                "currency": info.get("currency", "USD"),
            }
        except Exception:
            self._info = {"symbol": symbol, "name": symbol, "error": True}
        self._info_ready = True

    def _do_fetch_intraday(self, symbol: str) -> None:
        try:
            import yfinance as yf
            t = yf.Ticker(symbol)
            df = t.history(period="1d", interval="5m")
            self._intraday_df = df
        except Exception:
            self._intraday_df = None
        self._intraday_ready = True

    def _do_fetch_com_stocks(self, commodity_name: str) -> None:
        keywords = commodity_name.upper().split()
        symbols = []
        for kw, syms in _COMMODITY_STOCKS.items():
            if kw in keywords or any(kw in w for w in keywords):
                symbols.extend(syms)
        if symbols:
            self._do_fetch_quotes(symbols)
            self._quotes = self._quotes
        else:
            self._quotes = {}
        self._quotes_ready = True

    @staticmethod
    def get_sparkline(df: pd.DataFrame | None, width: int = 40, currency: str = "USD") -> str:
        if df is None or df.empty or "Close" not in df.columns:
            return ""
        closes = df["Close"].values
        if len(closes) < 2:
            return ""
        lo, hi = closes.min(), closes.max()
        if hi == lo:
            return "\u2500" * width
        chars = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
        n = len(chars) - 1
        step = max(width // len(closes), 1)
        result = ""
        for v in closes:
            idx = max(0, min(n, int((v - lo) / (hi - lo) * n)))
            result += chars[idx] * step
        return result
