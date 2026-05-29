from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Input, Label, ListItem, ListView, RichLog, Static

from rich.text import Text

from config import load_app_config
from i18n import t
from models.stock_model import StockModel


class StockScreen(Screen[None]):
    CSS = """
    StockScreen {
        layout: grid;
        grid-size: 3 1;
        grid-columns: 1fr 4fr 2fr;
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

    def __init__(self) -> None:
        super().__init__()
        self.title = "Stock Market"
        self.model = StockModel()
        self._all_symbols: list[str] = []
        self._selected: str = ""
        self._panel_index: int = 0

    def compose(self) -> ComposeResult:
        with Container(id="stock-left"):
            with Vertical(id="stock-left-top"):
                yield Label(t("stock_watchlist"), id="stock-title")
                yield Input(placeholder=t("search"), id="stock-search")
            yield ListView(id="stock-list")
            yield Static("", id="stock-list-count")

        with Container(id="stock-center"):
            yield Label(t("stock_quotes"), id="stock-center-title")
            yield DataTable(id="stock-table")

        with Container(id="stock-right"):
            yield Label(t("stock_detail"), id="stock-detail-title")
            with Container(id="stock-detail"):
                yield RichLog(id="stock-detail-log", highlight=True, markup=True, wrap=True)
            yield Static(t("stock_auto_refresh"), id="stock-hint")

    def on_mount(self) -> None:
        self.model.fetch_all()
        self.set_interval(0.15, self._poll)
        cfg = load_app_config()
        interval = cfg.get("stock_refresh", 60)
        if interval > 0:
            self.set_interval(interval, lambda: self.model.fetch_all())

    def _poll(self) -> None:
        if self.model._quotes_ready:
            self._all_symbols = sorted(self.model._quotes.keys())
            self._update_table()
            self._refresh_list()
            self.model._quotes_ready = False
        if self.model._info_ready or self.model._chart_ready:
            self._update_detail()

    def _update_table(self) -> None:
        try:
            dt = self.query_one("#stock-table", DataTable)
            dt.clear(columns=True)
            quotes = self.model._quotes
            if not quotes:
                return
            dt.add_columns(t("symbol"), t("stock_name"), t("stock_price"), t("stock_change"))
            for sym in sorted(quotes.keys()):
                q = quotes[sym]
                price = q.get("price", 0)
                chg_pct = q.get("change_pct", 0)
                name = q.get("name", sym)

                if q.get("nodata"):
                    dt.add_row(sym, Text(name[:20], style="dim"), Text("N/A", style="dim"),
                              Text("--", style="dim"))
                elif price:
                    p_text = Text(f"{price:.2f}", style="bold")
                    if chg_pct > 0:
                        c_text = Text(f"+{chg_pct:.2f}%", style="bold green")
                    elif chg_pct < 0:
                        c_text = Text(f"{chg_pct:.2f}%", style="bold red")
                    else:
                        c_text = Text("0.00%", style="dim")

                    spark = StockModel.sparkline(q.get("sparkline_prices", []), 18)
                    dt.add_row(sym, Text(name[:20], style=""), p_text, c_text)
                else:
                    dt.add_row(sym, Text(name[:20], style=""), Text("--", style="dim"),
                              Text("--", style="dim"))
        except Exception:
            pass

    def _build_items(self, query: str = "") -> list[ListItem]:
        symbols = self._all_symbols
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
            self.query_one("#stock-list-count", Static).update(f"{len(items)} stocks")
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "stock-search":
            self._refresh_list(event.value)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        symbol = event.item.name
        if not symbol:
            return
        self._selected = symbol
        self.model.fetch_info(symbol)

    def _update_detail(self) -> None:
        try:
            log = self.query_one("#stock-detail-log", RichLog)
            log.clear()
            info = self.model._info
            if not info or info.get("error"):
                log.write(f"[dim]{t('stock_no_data')}[/]")
                return

            sym = info.get("symbol", "")
            name = info.get("name", sym)
            log.write(f"[bold]{name} ({sym})[/]")

            q = self.model._quotes.get(sym, {})
            if q and q.get("price"):
                chg = q.get("change_pct", 0)
                color = "green" if chg >= 0 else "red"
                log.write(f"[{color}]${q['price']:.2f}  {chg:+.2f}%[/]")

            if self.model._chart_prices:
                spark = StockModel.sparkline(self.model._chart_prices, 40)
                if spark:
                    log.write(f"[dim]{spark}[/]")
            log.write("")

            sector = info.get("sector", "")
            industry = info.get("industry", "")
            if sector:
                log.write(f"{t('stock_sector')}: {sector}")
            if industry:
                log.write(f"{t('stock_industry')}: {industry}")
            log.write("")

            mc = info.get("market_cap")
            pe = info.get("pe_ratio")
            div = info.get("dividend_yield")
            h52 = info.get("52w_high")
            l52 = info.get("52w_low")
            eps = info.get("eps")
            vol = info.get("avg_volume")

            if mc:
                log.write(f"{t('stock_market_cap')}: {mc}")
            if pe:
                log.write(f"PE: {pe}")
            if eps:
                log.write(f"EPS: {eps}")
            if div:
                log.write(f"{t('stock_dividend')}: {div}")
            if h52 and l52:
                log.write(f"52W: {l52} - {h52}")
            if vol:
                log.write(f"{t('stock_volume')}: {vol}")
        except Exception:
            pass

    def action_focus_prev_panel(self) -> None:
        self._panel_index = (self._panel_index - 1) % 3
        self._focus_current()

    def action_focus_next_panel(self) -> None:
        self._panel_index = (self._panel_index + 1) % 3
        self._focus_current()

    def _focus_current(self) -> None:
        order = ["#stock-list", "#stock-table", "#stock-detail-log"]
        try:
            self.query_one(order[self._panel_index]).focus()
        except Exception:
            pass
