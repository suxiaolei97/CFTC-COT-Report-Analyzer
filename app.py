import os

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header

from config import DEFAULT_REPORT_TYPE, DEFAULT_YEAR, DEFAULT_START_YEAR, DEFAULT_LANG, DEFAULT_TOP_N, REPORT_TYPES, load_app_config, data_path
from i18n import t, set_lang
from models.cot_model import CotData
from screens.analysis_screen import AnalysisScreen
from screens.dataset_screen import DatasetScreen
from screens.loading_screen import LoadingScreen
from screens.main_screen import MainScreen
from screens.settings_screen import SettingsScreen


class CotTui(App[None]):
    BINDINGS = [
        Binding("f2", "switch_dataset", t("dataset")),
        Binding("f4", "analysis", t("deepseek_analysis")),
        Binding("f5", "refresh", t("refresh")),
        Binding("f12", "settings", t("settings")),
        Binding("q", "quit", t("quit")),
        Binding("escape", "focus_market_list", t("focus_list")),
        Binding("slash", "focus_search", t("search")),
        Binding("tab", "cycle_panels", t("cycle_panels")),
    ]

    CSS = """
    FooterKey {
        background: #0f0f1a;
    }
    FooterKey > .footer-key--key {
        color: #7aafff;
        background: #2a2a5a;
    }
    FooterKey > .footer-key--description {
        color: #c0c0e0;
        background: #16162a;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        cfg = load_app_config()
        set_lang(cfg.get("lang", DEFAULT_LANG))
        self.report_type = cfg.get("report_type", DEFAULT_REPORT_TYPE)
        if self.report_type not in REPORT_TYPES:
            self.report_type = DEFAULT_REPORT_TYPE
        self.year = cfg.get("year", DEFAULT_YEAR)
        if not isinstance(self.year, int) or self.year < 2000:
            self.year = DEFAULT_YEAR
        self.start_year = cfg.get("start_year", DEFAULT_START_YEAR)
        if not isinstance(self.start_year, int) or self.start_year < 2000:
            self.start_year = DEFAULT_START_YEAR
        self.model: CotData | None = None
        self._panel_index: int = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, icon="\u25CF")

    def on_mount(self) -> None:
        self.push_screen(
            LoadingScreen(report_type=self.report_type, year=self.year, start_year=self.start_year),
            callback=self._on_data_loaded,
        )

    def _on_data_loaded(self, result: CotData | None) -> None:
        if result is not None:
            self.model = result
            self.push_screen(MainScreen(self.model, self.report_type))
        else:
            self.exit(message="Failed to load data.")

    def action_switch_dataset(self) -> None:
        def _cb(result: str | None) -> None:
            if result is not None and result != self.report_type:
                self.report_type = result
                self.model = CotData(report_type=self.report_type, year=self.year, start_year=self.start_year)
                self.push_screen(
                    LoadingScreen(report_type=self.report_type, year=self.year, start_year=self.start_year),
                    callback=self._on_reload_done,
                )

        self.push_screen(DatasetScreen(current=self.report_type), callback=_cb)

    def _on_reload_done(self, result: CotData | None) -> None:
        if result is not None:
            self.model = result
            main_screen = self.get_current_main()
            if main_screen:
                main_screen.model = result
                main_screen.report_type = self.report_type
                main_screen.refresh_data()
            else:
                self.push_screen(MainScreen(self.model, self.report_type))

    def action_analysis(self) -> None:
        if self.model is None:
            return
        main = self.get_current_main()
        market = main.get_selected_market() if main else None
        self.push_screen(AnalysisScreen(model=self.model, selected_market=market))

    def action_refresh(self) -> None:
        from models.cot_model import CotData
        base = CotData.TXT_MAP.get(self.report_type, "annualof.txt")
        parts = base.rsplit(".", 1)
        cache_file = f"{parts[0]}_{self.start_year}_{self.year}.{parts[1]}"
        for f in [data_path(base), data_path(cache_file)]:
            if os.path.exists(f):
                os.remove(f)
        self.model = CotData(report_type=self.report_type, year=self.year, start_year=self.start_year)
        self.push_screen(
            LoadingScreen(report_type=self.report_type, year=self.year, start_year=self.start_year),
            callback=self._on_reload_done,
        )

    def action_settings(self) -> None:
        def _cb(data: dict) -> None:
            if data:
                cfg = load_app_config()
                set_lang(cfg.get("lang", DEFAULT_LANG))
                new_type = cfg.get("report_type", self.report_type)
                new_year = cfg.get("year", self.year)
                new_start = cfg.get("start_year", self.start_year)
                if new_type != self.report_type or new_year != self.year or new_start != self.start_year:
                    self.report_type = new_type
                    self.year = new_year
                    self.start_year = new_start
                    self.action_refresh()
                else:
                    main = self.get_current_main()
                    if main:
                        main.refresh_data()

        self.push_screen(SettingsScreen(), callback=_cb)

    def action_quit(self) -> None:
        self.exit()

    def action_focus_market_list(self) -> None:
        main = self.get_current_main()
        if main:
            try:
                main.query_one("#market-list").focus()
            except Exception:
                pass

    def action_focus_search(self) -> None:
        main = self.get_current_main()
        if main:
            try:
                inp = main.query_one("#search-input")
                inp.focus()
            except Exception:
                pass

    def action_cycle_panels(self) -> None:
        main = self.get_current_main()
        if main is None:
            return
        order = ["#market-list", "#data-table", "#detail-log"]
        self._panel_index = (self._panel_index + 1) % len(order)
        try:
            main.query_one(order[self._panel_index]).focus()
        except Exception:
            pass

    def get_current_main(self) -> MainScreen | None:
        for screen in self.screen_stack:
            if isinstance(screen, MainScreen):
                return screen
        return None
