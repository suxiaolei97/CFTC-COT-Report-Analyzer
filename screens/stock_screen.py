from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Input, Label, RichLog, Static

from rich.text import Text

from i18n import t
from models.stock_model import StockModel


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
        self._total_loaded: int = 0

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Input(placeholder=f"{t('search')} (Symbol / Name)", id="stock-search")
            yield Static("Loading...", id="stock-count")

        with Container(id="stock-table-container"):
            yield Label(t("stock_quotes"), id="stock-center-title")
            yield DataTable(id="stock-table")

        with Container(id="stock-detail-section"):
            yield Label(t("stock_detail"), id="stock-detail-title")
            yield RichLog(id="stock-detail-log", highlight=True, markup=True, wrap=True)

        yield Static(f"F3: COT  |  F4: {t('deepseek_analysis')}  |  {t('stock_auto_refresh')}", id="stock-hint")

    def on_mount(self) -> None:
        self.model.fetch_all()
        self.set_interval(0.15, self._poll)

    def _poll(self) -> None:
        if self.model._quotes_updated:
            self.model._quotes_updated = False
            self._total_loaded = len(self.model._quotes)
            self._update_table()
            try:
                self.query_one("#stock-count", Static).update(f"{self._total_loaded} / {len(self.model._quotes)}")
            except Exception:
                pass
        if self.model._info_ready or self.model._chart_ready:
            self._update_detail()
            self.model._info_ready = False
            self.model._chart_ready = False

    def _update_table(self) -> None:
        try:
            dt = self.query_one("#stock-table", DataTable)
            quotes = self.model._quotes
            if not quotes:
                return
            syms = sorted(quotes.keys())
            dt.clear(columns=True)
            dt.add_columns(t("symbol"), t("stock_name"), t("stock_price"), t("stock_change"))
            for sym in syms:
                q = quotes[sym]
                price = q.get("price", 0)
                chg_pct = q.get("change_pct", 0)
                name = q.get("name", sym)
                if q.get("nodata"):
                    dt.add_row(sym, Text(name[:25], style="dim"), Text("--", style="dim"), Text("--", style="dim"))
                elif price:
                    p_text = Text(f"{price:.2f}", style="bold")
                    if chg_pct > 0:
                        c_text = Text(f"+{chg_pct:.2f}%", style="bold green")
                    elif chg_pct < 0:
                        c_text = Text(f"{chg_pct:.2f}%", style="bold red")
                    else:
                        c_text = Text("0.00%", style="dim")
                    dt.add_row(sym, Text(name[:25], style=""), p_text, c_text)
                else:
                    dt.add_row(sym, Text(name[:25], style=""), Text("--", style="dim"), Text("--", style="dim"))
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "stock-search":
            try:
                dt = self.query_one("#stock-table", DataTable)
                query = event.value.strip().upper()
                quotes = self.model._quotes
                syms = sorted(quotes.keys())
                dt.clear(columns=True)
                dt.add_columns(t("symbol"), t("stock_name"), t("stock_price"), t("stock_change"))
                for sym in syms:
                    q = quotes[sym]
                    name = q.get("name", sym)
                    if query and query not in sym.upper() and query.upper() not in name.upper():
                        continue
                    price = q.get("price", 0)
                    chg_pct = q.get("change_pct", 0)
                    if q.get("nodata"):
                        dt.add_row(sym, Text(name[:25], style="dim"), Text("--", style="dim"), Text("--", style="dim"))
                    elif price:
                        p_text = Text(f"{price:.2f}", style="bold")
                        c_text = Text(f"{chg_pct:+.2f}%", style="bold green" if chg_pct >= 0 else "bold red") if price else Text("--", style="dim")
                        dt.add_row(sym, Text(name[:25], style=""), p_text, c_text)
                    else:
                        dt.add_row(sym, Text(name[:25], style=""), Text("--", style="dim"), Text("--", style="dim"))
            except Exception:
                pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key.value is not None:
            try:
                dt = self.query_one("#stock-table", DataTable)
                row = dt.get_row(event.row_key)
                self._selected = str(row[0])
                self.model.fetch_info(self._selected)
            except Exception:
                pass

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
                spark = StockModel.sparkline(self.model._chart_prices, 50)
                if spark:
                    log.write(f"[dim]{spark}[/]")
            log.write("")
            for key, label in [("sector", t("stock_sector")), ("industry", t("stock_industry")),
                               ("market_cap", t("stock_market_cap")), ("pe_ratio", "PE"),
                               ("dividend_yield", t("stock_dividend")), ("eps", "EPS"),
                               ("52w_high", "52W"), ("avg_volume", t("stock_volume"))]:
                val = info.get(key)
                if val:
                    log.write(f"{label}: {val}")
        except Exception:
            pass
