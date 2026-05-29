from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import (
    DataTable,
    Input,
    Label,
    ListItem,
    ListView,
    RichLog,
    Static,
)

from rich.text import Text

from config import REPORT_TYPES, load_app_config
from i18n import t


class MainScreen(Screen[None]):
    BINDINGS = [
        Binding("left", "focus_prev_panel", "Prev Panel", show=False),
        Binding("right", "focus_next_panel", "Next Panel", show=False),
    ]
    CSS = """
    MainScreen {
        layout: grid;
        grid-size: 3 1;
        grid-columns: 1.5fr 2.5fr 2fr;
        grid-gutter: 1 2;
        padding: 0 1 1 1;
        background: #0f0f1a;
    }

    /* ---- LEFT PANEL ---- */
    #left-panel {
        height: 100%;
        border: thick #2a2a5a;
        background: #16162a;
    }
    #left-top {
        height: auto;
        padding: 1;
        background: #1a1a3a;
    }
    #report-label {
        color: #7aafff;
        text-style: bold;
        height: 1;
    }
    #date-label {
        color: #606080;
        height: 1;
    }
    #search-input {
        margin: 1 0;
        width: 100%;
    }
    #search-input > .input--placeholder {
        color: #404070;
    }
    #market-list {
        height: 1fr;
    }
    #market-list > ListItem {
        color: #c0c0e0;
        padding: 0 1;
    }
    #market-list > ListItem.-highlight {
        background: #2a2a4a;
        color: #ffffff;
    }
    #market-count {
        color: #606080;
        height: 1;
        padding: 0 1;
        background: #1a1a3a;
    }

    /* ---- CENTER PANEL ---- */
    #center-panel {
        height: 100%;
        border: thick #2a2a5a;
        background: #16162a;
    }
    #center-title {
        color: #7aafff;
        text-style: bold;
        padding: 1;
        height: 1;
        background: #1a1a3a;
    }
    #data-table {
        height: 1fr;
    }

    /* ---- RIGHT PANEL ---- */
    #right-panel {
        height: 100%;
        border: thick #2a2a5a;
        background: #16162a;
    }
    #detail-header {
        padding: 1;
        height: auto;
        background: #1a1a3a;
    }
    #detail-title {
        color: #7aafff;
        text-style: bold;
    }
    #detail-log {
        height: 1fr;
        min-height: 10;
        padding: 0 1;
    }
    #detail-hint {
        height: 2;
        padding: 0 1;
        background: #1a1a3a;
        color: #c0c0e0;
    }
    """

    def __init__(self, model, report_type: str) -> None:
        super().__init__()
        self.model = model
        self.report_type = report_type
        self.title = f"COT Dashboard \u2014 {REPORT_TYPES.get(report_type, report_type)}"
        self._all_markets: list[str] = model.markets
        self._selected_market: str | None = None
        self._selected_date: str = ""
        self._search_timer: object = None

    def compose(self) -> ComposeResult:
        # --- LEFT ---
        with Container(id="left-panel"):
            with Vertical(id="left-top"):
                yield Label(
                    f"[{t('report_type_' + self.report_type)}]",
                    id="report-label",
                )
                yield Label(
                    f"Latest: {self.model.latest_date}  |  Markets: {self.model.market_count}",
                    id="date-label",
                )
                yield Input(placeholder=t("search_placeholder"), id="search-input")
            yield ListView(*self._build_items(), id="market-list")
            yield Static(
                f"Showing {len(self._all_markets)} markets", id="market-count"
            )

        # --- CENTER ---
        with Container(id="center-panel"):
            yield Label(t("data_table_hint"), id="center-title")
            yield DataTable(id="data-table")

        # --- RIGHT ---
        with Container(id="right-panel"):
            yield Label(t("market_detail"), id="detail-title")
            yield RichLog(id="detail-log", highlight=True, markup=True)
            cfg = load_app_config()
            model_raw = cfg.get("model", "pro")
            model = model_raw.upper() if isinstance(model_raw, str) else "PRO"
            thinking = cfg.get("thinking", "medium")
            yield Static(
                t("shortcut_hint") + f"  |  {model} \u00b7 {thinking}",
                id="detail-hint",
            )

    def _build_items(self, query: str = "") -> list[ListItem]:
        markets = self._all_markets
        if query:
            q = query.lower()
            markets = [m for m in markets if q in m.lower()]
        return [ListItem(Label(m), name=m) for m in markets]

    def _refresh_list(self, query: str = "") -> None:
        items = self._build_items(query)
        lv = self.query_one("#market-list", ListView)
        lv.clear()
        lv.extend(items)
        self.query_one("#market-count", Static).update(
            f"Showing {len(items)} markets"
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self._debounce_search(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            self._debounce_search(event.value)

    def _debounce_search(self, value: str) -> None:
        if self._search_timer is not None:
            self._search_timer.stop()
        self._search_timer = self.set_timer(0.15, lambda: self._refresh_list(value))

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        market = event.item.name or str(event.item.render().plain)
        self._selected_market = market
        self._update_center(market)
        self._update_detail(market)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        market = event.item.name or str(event.item.render().plain)
        self._selected_market = market
        self._update_center(market)
        self._update_detail(market)

    def _update_center(self, market: str) -> None:
        dt = self.query_one("#data-table", DataTable)
        dt.clear(columns=True)

        rows = self.model.get_market_summary(market)
        if not rows:
            self.query_one("#center-title", Label).update("No data")
            return

        cat_keys = self.model.cat_keys

        cols = ["Date", "OI"]
        for ck in cat_keys:
            cols.append(f"{ck[:5]}_L")
            cols.append(f"{ck[:5]}_S")
            cols.append(f"{ck[:5]}_N")

        dt.add_columns(*cols)
        for r in rows:
            vals: list = [r["date"], f'{r["oi"]:,.0f}']
            for ck in cat_keys:
                long_val = r[f"{ck}_long"]
                short_val = r[f"{ck}_short"]
                net_val = r[f"{ck}_net"]
                if long_val > 0:
                    vals.append(Text(f"{long_val:,.0f}", style="green"))
                elif long_val < 0:
                    vals.append(Text(f"{long_val:,.0f}", style="red"))
                else:
                    vals.append(Text("0", style="dim"))
                if short_val > 0:
                    vals.append(Text(f"{short_val:,.0f}", style="green"))
                elif short_val < 0:
                    vals.append(Text(f"{short_val:,.0f}", style="red"))
                else:
                    vals.append(Text("0", style="dim"))
                if net_val > 0:
                    vals.append(Text(f"+{net_val:,.0f}", style="bold green"))
                elif net_val < 0:
                    vals.append(Text(f"{net_val:,.0f}", style="bold red"))
                else:
                    vals.append(Text("0", style="dim"))
            dt.add_row(*vals)

        self.query_one("#center-title", Label).update(
            f"[{market}]  ({len(rows)} {t('records')})"
        )

    def _update_detail(self, market: str) -> None:
        log = self.query_one("#detail-log", RichLog)
        log.clear()
        detail = self.model.get_market_detail(market)
        if not detail:
            log.write(f"[dim]{t('no_detail')}[/]")
            return

        oi = detail.get("oi", 0)
        oi_change = detail.get("oi_change", 0)
        log.write(f"[bold]{detail['market']}[/]")
        log.write(f"[dim]{t('date')}: {detail['date']}[/]")
        log.write("")

        cot_idx = self.model.get_cot_index(market)
        spark = self.model.get_sparkline(market)
        if spark:
            log.write(f"[dim]{spark}[/]")
        if cot_idx is not None:
            if cot_idx >= 80:
                idx_color = "bold red"
                idx_label = t("cot_index_extreme_long")
            elif cot_idx <= 20:
                idx_color = "bold green"
                idx_label = t("cot_index_extreme_short")
            else:
                idx_color = "yellow"
                idx_label = t("cot_index_neutral")
            log.write(f"{t('cot_index')}: [{idx_color}]{cot_idx:.0f}[/]  [{idx_color}]{idx_label}[/]")
        log.write(f"{t('open_interest')}: [bold]{oi:,.0f}[/]")
        oi_sign = "+" if oi_change >= 0 else ""
        log.write(f"{t('oi_change')}:     [{'green' if oi_change >= 0 else 'red'}]{oi_sign}{oi_change:,.0f}[/]")
        log.write("")

        for cat_label, cat_data in detail.get("categories", {}).items():
            net = cat_data["net"]
            log.write(f"[bold underline]{cat_label}[/]")
            log.write(f"  {t('long')}:   {cat_data['long']:>10,.0f}")
            log.write(f"  {t('short')}:  {cat_data['short']:>10,.0f}")
            sign = "+" if net >= 0 else ""
            color = "green" if net >= 0 else "red"
            log.write(f"  {t('net')}:    [{color}]{sign}{net:>9,.0f}[/]")
            spread = cat_data.get("spread", 0)
            if spread:
                log.write(f"  {t('spread')}: {spread:>10,.0f}")
            chg_l = cat_data.get("change_long", 0)
            chg_s = cat_data.get("change_short", 0)
            if chg_l or chg_s:
                log.write(f"  [Δ] {t('long')}: {chg_l:+,.0f}   {t('short')}: {chg_s:+,.0f}")
            log.write("")

    def refresh_data(self) -> None:
        self._all_markets = self.model.markets
        self.title = f"COT Dashboard \u2014 {REPORT_TYPES.get(self.report_type, self.report_type)}"
        self._refresh_list()
        self.query_one("#date-label", Label).update(
            f"Latest: {self.model.latest_date}  |  Markets: {self.model.market_count}"
        )
        self.query_one("#report-label", Label).update(
            f"[{t('report_type_' + self.report_type)}]"
        )
        self.query_one("#detail-title", Label).update(t("market_detail"))
        cfg = load_app_config()
        model_raw = cfg.get("model", "pro")
        model = model_raw.upper() if isinstance(model_raw, str) else "PRO"
        thinking = cfg.get("thinking", "medium")
        self.query_one("#detail-hint", Static).update(
            t("shortcut_hint") + f"  |  {model} \u00b7 {thinking}",
        )
        if self._selected_market:
            self._update_center(self._selected_market)
            self._update_detail(self._selected_market)

    def get_selected_market(self) -> str | None:
        return self._selected_market

    def _focus_panel(self, selector: str) -> None:
        try:
            self.query_one(selector).focus()
        except Exception:
            pass

    def action_focus_prev_panel(self) -> None:
        order = ["#market-list", "#data-table", "#detail-log"]
        current = None
        try:
            for i, sel in enumerate(order):
                if self.query_one(sel).has_focus_within:
                    current = i
                    break
        except Exception:
            pass
        nxt = ((current or len(order)) - 1) % len(order) if current is not None else 0
        self._focus_panel(order[nxt])

    def action_focus_next_panel(self) -> None:
        order = ["#market-list", "#data-table", "#detail-log"]
        current = None
        try:
            for i, sel in enumerate(order):
                if self.query_one(sel).has_focus_within:
                    current = i
                    break
        except Exception:
            pass
        nxt = ((current or 0) + 1) % len(order) if current is not None else 0
        self._focus_panel(order[nxt])
