import time
from concurrent.futures import ThreadPoolExecutor

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Label, ListItem, ListView, RichLog, Static

from rich.text import Text

from config import load_app_config
from i18n import t
from models.stock_model import StockModel, _COMMODITY_STOCKS


class StockScreen(Screen[None]):
    CSS = """
    StockScreen {
        layout: grid;
        grid-size: 3 1;
        grid-columns: 1.5fr 2.5fr 2fr;
        grid-gutter: 1 2;
        padding: 0 1 1 1;
        background: #0f0f1a;
    }

    #stock-left {
        height: 100%;
        border: thick #2a2a5a;
        background: #16162a;
    }
    #stock-left-top {
        height: auto;
        padding: 1;
        background: #1a1a3a;
    }
    #stock-title {
        color: #7aafff;
        text-style: bold;
        height: 1;
    }
    #stock-search {
        margin: 1 0;
        width: 100%;
    }
    #stock-list {
        height: 1fr;
    }
    #stock-list > ListItem {
        color: #c0c0e0;
        padding: 0 1;
    }
    #stock-list > ListItem.-highlight {
        background: #2a2a4a;
        color: #ffffff;
    }
    #stock-list-count {
        color: #606080;
        height: 1;
        padding: 0 1;
        background: #1a1a3a;
    }

    #stock-center {
        height: 100%;
        border: thick #2a2a5a;
        background: #16162a;
    }
    #stock-center-title {
        color: #7aafff;
        text-style: bold;
        padding: 1;
        height: 1;
        background: #1a1a3a;
    }
    #stock-table {
        height: 1fr;
    }

    #stock-right {
        height: 100%;
        border: thick #2a2a5a;
        background: #16162a;
    }
    #stock-detail-title {
        color: #7aafff;
        text-style: bold;
        padding: 1;
        height: 1;
        background: #1a1a3a;
    }
    #stock-detail {
        height: 1fr;
        padding: 0 1;
    }
    #stock-detail RichLog {
        height: 100%;
        min-height: 10;
    }
    #stock-hint {
        color: #c0c0e0;
        height: 2;
        padding: 0 1;
        background: #1a1a3a;
    }
    """

    BINDINGS = [
        Binding("left", "focus_prev_panel", "", show=False),
        Binding("right", "focus_next_panel", "", show=False),
    ]

    def __init__(self, initial_watchlist: list[str] | None = None) -> None:
        super().__init__()
        self.title = "Stock Market"
        self.model = StockModel()
        cfg = load_app_config()
        wl = cfg.get("watchlist", "")
        self._watchlist = [s.strip().upper() for s in wl.split(",") if s.strip()] if wl else (initial_watchlist or ["AAPL", "TSLA", "NVDA", "^GSPC"])
        self._search_timer: object = None
        self._selected_symbol: str = ""
        self._loading: bool = True
        self._panel_index: int = 0

    def compose(self) -> ComposeResult:
        with Container(id="stock-left"):
            with Vertical(id="stock-left-top"):
                yield Label(t("stock_watchlist"), id="stock-title")
                yield Input(placeholder=t("type_to_search"), id="stock-search")
            yield ListView(*self._build_items(), id="stock-list")
            yield Static(f"{len(self._watchlist)} symbols", id="stock-list-count")

        with Container(id="stock-center"):
            yield Label(t("stock_quotes"), id="stock-center-title")
            yield DataTable(id="stock-table")

        with Container(id="stock-right"):
            yield Label(t("stock_detail"), id="stock-detail-title")
            with Container(id="stock-detail"):
                yield RichLog(id="stock-detail-log", highlight=True, markup=True, wrap=True)
            yield Static("", id="stock-hint")

    def on_mount(self) -> None:
        self.model.fetch_quotes(self._watchlist)
        self.set_interval(0.15, self._poll)
        cfg = load_app_config()
        interval = cfg.get("stock_refresh", 30)
        if interval > 0:
            self.set_interval(interval, self._auto_refresh)

    def _build_items(self, query: str = "") -> list[ListItem]:
        symbols = self._watchlist
        if query:
            q = query.upper()
            symbols = [s for s in symbols if q in s]
        return [ListItem(Label(s), name=s) for s in symbols]

    def _refresh_list(self, query: str = "") -> None:
        items = self._build_items(query)
        try:
            lv = self.query_one("#stock-list", ListView)
            lv.clear()
            lv.extend(items)
            shown = len(items)
        except Exception:
            shown = len(self._watchlist)
        try:
            self.query_one("#stock-list-count", Static).update(f"{shown} symbols")
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "stock-search":
            self._refresh_list(event.value)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        symbol = event.item.name
        if not symbol:
            return
        self._selected_symbol = symbol
        self.model.fetch_info(symbol)
        self.model.fetch_intraday(symbol)

    def _poll(self) -> None:
        if self.model._quotes_ready:
            self._loading = False
            self._update_table()
            self.model._quotes_ready = False
        if self.model._info_ready and self._selected_symbol:
            self._update_detail()
            self.model._info_ready = False

    def _update_table(self) -> None:
        try:
            dt = self.query_one("#stock-table", DataTable)
            dt.clear(columns=True)
            quotes = self.model._quotes
            if not quotes:
                if self.model._error:
                    dt.add_columns("Status")
                    dt.add_row(Text(self.model._error, style="red"))
                return
            cols = [t("symbol"), t("stock_name"), t("stock_price"), t("stock_change"), "Currency"]
            dt.add_columns(*cols)
            for sym, q in quotes.items():
                price = q.get("price", 0)
                chg_pct = q.get("change_pct", 0)
                name = q.get("name", sym)
                currency = q.get("currency", "")
                has_error = q.get("error")
                has_nodata = q.get("nodata")
                has_limit = q.get("rate_limited")

                if has_limit:
                    dt.add_row(sym, Text(name[:25], style="dim"), Text("N/A", style="dim"),
                              Text("Limit", style="red"), "")
                elif has_error:
                    dt.add_row(sym, Text(name[:25], style="dim"), Text("N/A", style="dim"),
                              Text("Error", style="red"), "")
                elif has_nodata:
                    dt.add_row(sym, Text(name[:25], style=""), Text("--", style="dim"),
                              Text("--", style="dim"), "")
                elif price:
                    p_text = Text(f"{price:,.2f}", style="bold")
                    if chg_pct > 0:
                        c_text = Text(f"+{chg_pct:+.2f}%", style="bold green")
                    elif chg_pct < 0:
                        c_text = Text(f"{chg_pct:+.2f}%", style="bold red")
                    else:
                        c_text = Text("0.00%", style="dim")
                    dt.add_row(sym, Text(name[:25], style=""), p_text, c_text, currency or "USD")
                else:
                    dt.add_row(sym, Text(name[:25], style=""), Text("--", style="dim"),
                              Text("--", style="dim"), currency or "USD")
        except Exception:
            pass

    def _update_detail(self) -> None:
        try:
            log = self.query_one("#stock-detail-log", RichLog)
            log.clear()
            info = self.model._info
            if not info:
                log.write(f"[dim]{t('stock_no_data')}[/]")
                return
            if info.get("error"):
                log.write(f"[dim]{t('stock_no_data')}[/]")
                return

            sym = info.get("symbol", "")
            name = info.get("name", sym)
            log.write(f"[bold]{name} ({sym})[/]")

            spark = self.model.get_sparkline(width=40)
            if spark:
                log.write(f"[dim]{spark}[/]")
            log.write("")

            fmt_big = lambda v: f"{v:,.0f}" if v else "--"
            fmt_val = lambda v, p=2: f"{v:,.{p}f}" if v else "--"
            fmt_pct = lambda v: f"{v*100:.2f}%" if v else "--"

            mc = info.get("market_cap")
            pe = info.get("pe_ratio")
            fpe = info.get("forward_pe")
            div = info.get("dividend_yield")
            h52 = info.get("52w_high")
            l52 = info.get("52w_low")
            vol = info.get("avg_volume")
            beta = info.get("beta")
            eps = info.get("trailingEps")
            sector = info.get("sector", "")
            industry = info.get("industry", "")

            if sector:
                log.write(f"{t('stock_sector')}: {sector}")
            if industry:
                log.write(f"{t('stock_industry')}: {industry}")
            log.write("")
            log.write(f"{t('stock_market_cap')}: {fmt_big(mc)}")
            log.write(f"PE: {fmt_val(pe)}  |  Forward PE: {fmt_val(fpe)}")
            log.write(f"EPS: {fmt_val(eps)}  |  Beta: {fmt_val(beta, 1)}")
            log.write(f"{t('stock_dividend')}: {fmt_pct(div)}")
            log.write(f"52W: {fmt_val(l52)} - {fmt_val(h52)}")
            log.write(f"{t('stock_volume')}: {fmt_big(vol)}")

            q = self.model._quotes.get(sym, {})
            if q and q.get("price"):
                log.write("")
                log.write(f"[bold]{t('stock_price')}: {q['price']:,.2f} {info.get('currency', 'USD')}[/]")
        except Exception:
            pass

    def _auto_refresh(self) -> None:
        if not self._loading:
            self.model.fetch_quotes(self._watchlist)

    def action_focus_prev_panel(self) -> None:
        order = ["#stock-list", "#stock-table", "#stock-detail-log"]
        self._panel_index = (self._panel_index - 1) % len(order)
        try:
            self.query_one(order[self._panel_index]).focus()
        except Exception:
            pass

    def action_focus_next_panel(self) -> None:
        order = ["#stock-list", "#stock-table", "#stock-detail-log"]
        self._panel_index = (self._panel_index + 1) % len(order)
        try:
            self.query_one(order[self._panel_index]).focus()
        except Exception:
            pass

    def update_hint(self) -> None:
        cfg = load_app_config()
        wl = cfg.get("watchlist", "")
        symbols = [s.strip().upper() for s in wl.split(",") if s.strip()] if wl else self._watchlist
        self._watchlist = symbols
        self._refresh_list()
        self.model.fetch_quotes(self._watchlist)
        try:
            self.query_one("#stock-hint", Static).update(
                f"F3: COT  |  {len(self._watchlist)} symbols  |  " + t("stock_auto_refresh")
            )
        except Exception:
            pass

    def on_screen_resume(self) -> None:
        self.model.fetch_quotes(self._watchlist)

    def on_screen_pause(self) -> None:
        pass
