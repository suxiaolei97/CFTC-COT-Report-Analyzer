from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Input, Label, RichLog, Static

from rich.text import Text

from i18n import t
from models.stock_model import StockModel, MAJOR_STOCKS


class StockScreen(Screen[None]):
    CSS = """
    StockScreen {
        layout: vertical;
        background: #0f0f1a;
        padding: 1 2;
    }
    #stock-search {
        width: 100%;
        margin-bottom: 1;
    }
    #stock-table-container {
        height: 3fr;
        border: thick #2a2a5a;
        background: #16162a;
    }
    #stock-table {
        height: 100%;
    }
    #stock-detail-section {
        height: 2fr;
        border: thick #2a2a5a;
        background: #16162a;
        margin-top: 1;
    }
    #stock-detail-title {
        color: #7aafff;
        text-style: bold;
        padding: 0 1;
        height: 1;
        background: #1a1a3a;
    }
    #stock-detail-log {
        height: 1fr;
    }
    #stock-hint {
        height: 1;
        padding: 0 1;
        margin-top: 1;
        background: #1a1a3a;
        color: #c0c0e0;
    }
    #stock-count {
        color: #606080;
        text-align: right;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.title = "Stock Market"
        self.model = StockModel()
        self._selected: str = ""

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Input(placeholder=f"{t('search')} (Symbol / Name)", id="stock-search")
            yield Static("Loading...", id="stock-count")
        with Container(id="stock-table-container"):
            yield DataTable(id="stock-table", cursor_type="row")
        with Container(id="stock-detail-section"):
            yield Label(t("stock_detail"), id="stock-detail-title")
            yield RichLog(id="stock-detail-log", highlight=True, markup=True, wrap=True)
        yield Static(f"F3: COT  |  F4: {t('deepseek_analysis')}  |  Enter: select stock", id="stock-hint")

    def on_mount(self) -> None:
        self.model.fetch_all()
        self.set_interval(0.1, self._poll)

    def _poll(self) -> None:
        if self.model._quotes_updated:
            self.model._quotes_updated = False
            self._update_table()
            try:
                n = len(self.model._quotes)
                self.query_one("#stock-count", Static).update(f"{n} / {len(MAJOR_STOCKS)}")
            except Exception:
                pass
        if self.model._chart_ready:
            self._show_detail()
            self.model._chart_ready = False

    def _row_data(self, sym: str, q: dict) -> tuple:
        price = q.get("price", 0)
        chg_pct = q.get("change_pct", 0)
        name = q.get("name", sym)
        pe = q.get("pe", "")
        if not price:
            return (sym, Text(name[:20], style="dim"), Text("--", style="dim"),
                    Text("--", style="dim"), Text(pe or "", style="dim"), "")
        cs = "bold green" if chg_pct >= 0 else "bold red"
        return (Text(sym, style=cs), Text(name[:20], style=""),
                Text(f"{price:.2f}", style=cs),
                Text(f"{chg_pct:+.2f}%", style="bold green" if chg_pct >= 0 else "bold red"),
                Text(pe or "", style="dim"), "")

    def _update_table(self) -> None:
        try:
            dt = self.query_one("#stock-table", DataTable)
            quotes = self.model._quotes
            if not quotes:
                return
            dt.clear(columns=True)
            dt.add_columns(t("symbol"), t("stock_name"), t("stock_price"), t("stock_change"), "PE", "Spark")
            for sym in sorted(quotes.keys()):
                dt.add_row(*self._row_data(sym, quotes[sym]))
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "stock-search":
            return
        query = event.value.strip().upper()
        try:
            dt = self.query_one("#stock-table", DataTable)
            quotes = self.model._quotes
            dt.clear(columns=True)
            dt.add_columns(t("symbol"), t("stock_name"), t("stock_price"), t("stock_change"), "PE", "Spark")
            for sym in sorted(quotes.keys()):
                q = quotes[sym]
                name = str(q.get("name", sym))
                if query and query not in sym.upper() and query.upper() not in name.upper():
                    continue
                dt.add_row(*self._row_data(sym, q))
            if query and query not in quotes:
                self.model.dynamic_fetch(query)
        except Exception:
            pass

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        try:
            dt = self.query_one("#stock-table", DataTable)
            row = dt.get_row(event.row_key)
            sym = str(row[0])
            if sym == self._selected:
                return
            self._selected = sym
            self._show_detail()
            self.model.fetch_chart(sym)
        except Exception:
            pass

    def _show_detail(self) -> None:
        try:
            log = self.query_one("#stock-detail-log", RichLog)
            log.clear()
            q = self.model._quotes.get(self._selected, {})
            if not q:
                return
            price = q.get("price", 0)
            chg_pct = q.get("change_pct", 0)
            name = q.get("name", self._selected)
            color = "green" if chg_pct >= 0 else "red"
            log.write(f"[bold]{name} ({self._selected})[/]")
            log.write(f"[{color}]${price:.2f}  {chg_pct:+.2f}%[/]")

            prices = self.model._chart_prices
            if prices and len(prices) >= 2:
                spark = StockModel.sparkline(prices, 50)
                if spark:
                    log.write(f"[dim]{spark}[/]")
            log.write("")

            pe = q.get("pe", "")
            cap = q.get("market_cap", "")
            h52 = q.get("high_52w", "")
            l52 = q.get("low_52w", "")
            high = q.get("high", "")
            low = q.get("low", "")
            if pe:  log.write(f"PE: {pe}")
            if cap: log.write(f"Market Cap: {cap}")
            if h52 and l52: log.write(f"52W Range: {l52} - {h52}")
            if high and low: log.write(f"Today: {low} - {high}")
        except Exception:
            pass
