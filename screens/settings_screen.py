from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Select

from config import REPORT_TYPES, DEFAULT_REPORT_TYPE, DEFAULT_YEAR, DEFAULT_START_YEAR, load_app_config, save_app_config


class SettingsScreen(Screen[dict]):
    TITLE = "Settings"
    CSS = """
    SettingsScreen {
        layout: vertical;
        background: #0f0f1a;
        padding: 1 2;
    }
    #settings-dialog {
        width: 52;
        height: auto;
        margin: 1 0;
        border: thick #2a2a5a;
        background: #16162a;
        padding: 1 2;
    }
    #settings-title {
        color: #7aafff;
        text-style: bold;
        height: 2;
        content-align: center middle;
    }
    .settings-section {
        margin-top: 1;
        color: #606080;
        height: 1;
    }
    #settings-buttons {
        height: 3;
        align: right middle;
        margin-top: 1;
    }
    #settings-api-key {
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        cfg = load_app_config()

        with Vertical(id="settings-dialog"):
            yield Label("Settings", id="settings-title")

            yield Label("API Key", classes="settings-section")
            yield Input(
                value=cfg.get("api_key", ""),
                placeholder="sk-... DeepSeek API Key",
                password=True,
                id="settings-api-key",
            )

            yield Label("Model", classes="settings-section")
            saved_model = cfg.get("model", "pro")
            if not isinstance(saved_model, str):
                saved_model = "pro"
            with RadioSet(id="settings-model"):
                yield RadioButton("DeepSeek V4 Flash", id="model-flash")
                yield RadioButton("DeepSeek V4 Pro", id="model-pro")

            yield Label("Thinking Intensity", classes="settings-section")
            thinking_options = [
                ("Disabled",    "disabled"),
                ("Low",         "low"),
                ("Medium",      "medium"),
                ("High",        "high"),
            ]
            saved_thinking = cfg.get("thinking", "medium")
            yield Select(
                thinking_options,
                value=saved_thinking,
                id="settings-thinking",
            )

            yield Label("Default Report Type", classes="settings-section")
            options = [(label, key) for key, label in REPORT_TYPES.items()]
            saved_type = cfg.get("report_type", DEFAULT_REPORT_TYPE)
            yield Select(
                options,
                value=saved_type,
                id="settings-report-type",
            )

            yield Label("Default Year", classes="settings-section")
            yield Input(
                value=str(cfg.get("year", DEFAULT_YEAR)),
                placeholder=str(DEFAULT_YEAR),
                id="settings-year",
            )

            yield Label("Start Year", classes="settings-section")
            yield Input(
                value=str(cfg.get("start_year", DEFAULT_START_YEAR)),
                placeholder=str(DEFAULT_START_YEAR),
                id="settings-start-year",
            )

            with Horizontal(id="settings-buttons"):
                yield Button("Save", variant="primary", id="btn-save")
                yield Button("Cancel", variant="default", id="btn-cancel")

    def on_mount(self) -> None:
        cfg = load_app_config()
        saved_model = cfg.get("model", "pro")
        if not isinstance(saved_model, str):
            saved_model = "pro"
        target_id = f"model-{saved_model}"
        rs = self.query_one("#settings-model", RadioSet)
        for btn in rs.query(RadioButton):
            if btn.id == target_id:
                btn.value = True
                break

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss({})
        elif event.button.id == "btn-save":
            self._save()

    def _save(self) -> None:
        key = self.query_one("#settings-api-key", Input).value.strip()
        rs = self.query_one("#settings-model", RadioSet)
        btn = rs.pressed_button
        model = "pro"
        if btn is not None and btn.id and btn.id.startswith("model-"):
            model = btn.id[6:]

        sel_think = self.query_one("#settings-thinking", Select)
        thinking = str(sel_think.value) if sel_think.value else "medium"

        sel = self.query_one("#settings-report-type", Select)
        report_type = str(sel.value) if sel.value and str(sel.value) not in ("Select.NULL", "") else DEFAULT_REPORT_TYPE
        if report_type not in REPORT_TYPES:
            report_type = DEFAULT_REPORT_TYPE
        year_str = self.query_one("#settings-year", Input).value.strip()
        start_year_str = self.query_one("#settings-start-year", Input).value.strip()

        try:
            year = int(year_str)
        except ValueError:
            year = DEFAULT_YEAR
        try:
            start_year = int(start_year_str)
        except ValueError:
            start_year = DEFAULT_START_YEAR
        if start_year > year:
            start_year = year - 3
        if start_year < 2000:
            start_year = 2000

        data = {
            "api_key": key,
            "model": model,
            "thinking": thinking,
            "report_type": report_type,
            "year": year,
            "start_year": start_year,
        }
        save_app_config(data)
        self.dismiss(data)
