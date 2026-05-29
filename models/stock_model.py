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

        result = {}
        clean_symbols = [s.strip().upper().replace(" ", "-") for s in symbols]
        sym_str = " ".join(clean_symbols)

        try:
            df = yf.download(sym_str, period="2d", progress=False, timeout=15)
            if df is not None and not df.empty:
                close_col = "Close"
                if close_col in df.columns:
                    closes = df[close_col]
                    if isinstance(closes, pd.Series):
                        closes = pd.DataFrame({sym_str: closes})
                    for sym in clean_symbols:
                        if sym in closes.columns:
                            col = closes[sym].dropna()
                            if len(col) >= 2:
                                price = float(col.iloc[-1])
                                prev = float(col.iloc[-2])
                                chg = price - prev
                                chg_pct = (chg / prev) * 100 if prev else 0
                                result[sym] = {
                                    "symbol": sym, "price": price,
                                    "change": chg, "change_pct": chg_pct,
                                    "name": sym, "currency": "USD",
                                }
                                continue
                        result[sym] = {"symbol": sym, "price": 0, "change": 0, "change_pct": 0, "name": sym, "nodata": True}
                else:
                    for sym in clean_symbols:
                        result[sym] = {"symbol": sym, "price": 0, "change": 0, "change_pct": 0, "name": sym, "nodata": True}
            else:
                for sym in clean_symbols:
                    result[sym] = {"symbol": sym, "price": 0, "change": 0, "change_pct": 0, "name": sym, "nodata": True}
        except Exception as e:
            msg = str(e).lower()
            if "rate limit" in msg or "too many" in msg:
                self._error = "Yahoo rate limited. Wait and retry."
            else:
                self._error = str(e)[:80]
            for sym in clean_symbols:
                result[sym] = {"symbol": sym, "price": 0, "change": 0, "change_pct": 0, "name": sym, "error": True}

        self._quotes = result
        self._quotes_ready = True

    def _do_fetch_info(self, symbol: str) -> None:
        try:
            import yfinance as yf
            t = yf.Ticker(symbol)
            info = t.info
            self._info = {
                "symbol": symbol,
                "name": info.get("longName", info.get("shortName", symbol)),
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
            df = yf.download(symbol, period="1d", interval="5m", progress=False, timeout=10)
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
        else:
            self._quotes = {}
        self._quotes_ready = True

    @staticmethod
    def get_sparkline(df: pd.DataFrame | None, width: int = 40, currency: str = "USD") -> str:
        if df is None or df.empty:
            return ""
        if "Close" not in df.columns:
            return ""
        closes = df["Close"]
        if isinstance(closes, pd.DataFrame):
            closes = closes.iloc[:, 0]
        closes = closes.dropna().values
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
