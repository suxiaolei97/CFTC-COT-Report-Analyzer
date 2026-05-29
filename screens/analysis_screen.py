import json
import re
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, Input, Label, ListItem, ListView, RichLog, TextArea

from config import load_app_config, save_app_config, DEFAULT_TOP_N
from i18n import t
from models.cot_model import CotData

_RE_MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
_RE_MD_ITALIC = re.compile(r"\*(.+?)\*")
_RE_MD_HEADER = re.compile(r"^#{1,6}\s*")
_RE_MD_HR = re.compile(r"^[-*_]{3,}\s*$")


def _strip_markdown(text: str) -> str:
    lines = text.split("\n")
    result = []
    for line in lines:
        line = _RE_MD_BOLD.sub(r"\1", line)
        line = _RE_MD_ITALIC.sub(r"\1", line)
        line = _RE_MD_HEADER.sub("", line)
        if _RE_MD_HR.match(line):
            line = ""
        line = line.replace("```", "")
        line = line.replace("`", "")
        result.append(line)
    return "\n".join(result)


class AnalysisScreen(Screen[None]):
    CSS = """
    AnalysisScreen {
        layout: vertical;
        background: #0f0f1a;
        padding: 1 2;
    }
    #analysis-title {
        color: #7aafff;
        text-style: bold;
        height: 1;
    }
    #analysis-top {
        height: auto;
        margin-bottom: 1;
    }
    #analysis-market {
        width: 60;
    }
    #analysis-market-search {
        width: 100%;
        margin-bottom: 1;
    }
    #analysis-market-list {
        height: 15;
        border: solid #2a2a5a;
        margin-bottom: 1;
    }
    #analysis-market-list > ListItem {
        color: #c0c0e0;
        padding: 0 1;
    }
    #analysis-market-list > ListItem.-highlight {
        background: #2a2a4a;
        color: #ffffff;
    }
    #analysis-context-label {
        color: #606080;
        margin-top: 1;
    }
    #analysis-context {
        height: 1fr;
        border: solid #2a2a5a;
    }
    #analysis-result-label {
        color: #606080;
        margin-top: 1;
    }
    #analysis-result {
        height: 2fr;
        border: solid #2a2a5a;
    }
    #analysis-bar {
        height: 3;
        align: right middle;
    }
    #analysis-bar Label {
        margin-right: 1;
        color: #606080;
    }
    Button {
        margin-left: 1;
    }
    .section-label {
        color: #606080;
        height: 1;
        margin-top: 1;
    }
    """

    def __init__(self, model: CotData, selected_market: str | None = None) -> None:
        super().__init__()
        self.title = t("deepseek_analysis")
        self.model = model
        self._selected_market = selected_market
        self._busy: bool = False
        self._done: bool = False
        self._error: str | None = None
        self._chunks: list[str] = []
        self._timer: object = None
        self._executor: object = None

    def compose(self) -> ComposeResult:
        cfg = load_app_config()

        yield Label(t("deepseek_analysis"), id="analysis-title")

        yield Input(placeholder=t("type_to_filter"), id="analysis-market-search")
        yield ListView(*self._build_market_items(), id="analysis-market-list")

        yield Label("System Prompt (editable):", classes="section-label")
        saved_sys = cfg.get("system_prompt", t("system_prompt"))
        yield TextArea(saved_sys, id="analysis-sysprompt", soft_wrap=True)

        yield Label(t("analysis_context"), id="analysis-context-label")
        top_n = cfg.get("top_n", DEFAULT_TOP_N)
        ctx = self.model.to_analysis_context(market_filter=self._selected_market, top_n=top_n)
        yield TextArea(ctx, id="analysis-context", read_only=False, soft_wrap=True)

        yield Label(t("analysis_result"), id="analysis-result-label")
        yield TextArea("", id="analysis-result", read_only=True, soft_wrap=True)

        with Horizontal(id="analysis-bar"):
            yield Label(t("settings_hint"))
            yield Button(t("run_analysis"), variant="primary", id="btn-run")
            yield Button(t("back"), variant="default", id="btn-back")

    def _build_market_items(self, query: str = "") -> list[ListItem]:
        markets = self.model.markets
        if query:
            q = query.lower()
            markets = [m for m in markets if q in m.lower()]
        items = [ListItem(Label(t("all_markets_top_n")), name="")] if not query else []
        items += [ListItem(Label(m), name=m) for m in markets]
        return items

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "analysis-market-search":
            query = event.value.strip().lower()
            items = self._build_market_items(query)
            try:
                lv = self.query_one("#analysis-market-list", ListView)
                lv.clear()
                lv.extend(items)
            except Exception:
                pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        market = event.item.name if event.item.name else None
        self._selected_market = market
        cfg = load_app_config()
        top_n = cfg.get("top_n", DEFAULT_TOP_N)
        ctx = self.model.to_analysis_context(market_filter=market, top_n=top_n)
        try:
            ta = self.query_one("#analysis-context", TextArea)
            ta.text = ctx
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.dismiss()
        elif event.button.id == "btn-run":
            self._run_analysis()

    def _run_analysis(self) -> None:
        if self._busy:
            return

        cfg = load_app_config()
        key = cfg.get("api_key", "").strip()
        model_key = cfg.get("model", "pro")
        if not isinstance(model_key, str):
            model_key = "pro"
        model_map = {"flash": "deepseek-v4-flash", "pro": "deepseek-v4-pro"}
        model = model_map.get(model_key, "deepseek-v4-flash")
        thinking = cfg.get("thinking", "medium")

        sys_prompt = self.query_one("#analysis-sysprompt", TextArea).text.strip()
        prompt = self.query_one("#analysis-context", TextArea).text.strip()

        if not key:
            self._show_error(t("api_key_missing"))
            return
        if not prompt:
            self._show_error(t("no_prompt"))
            return

        if sys_prompt != cfg.get("system_prompt", ""):
            cfg["system_prompt"] = sys_prompt
            save_app_config(cfg)

        self._busy = True
        log = self.query_one("#analysis-result", TextArea)
        log.text = t("call_api", model=model)

        btn = self.query_one("#btn-run", Button)
        btn.disabled = True
        btn.label = t("running")

        self._done = False
        self._error = None
        self._chunks = []

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": sys_prompt if sys_prompt else t("system_prompt")},
                {"role": "user", "content": prompt},
            ],
            "stream": True,
        }
        if thinking != "disabled":
            body["thinking"] = {"type": "enabled", "effort": thinking}

        self._executor = ThreadPoolExecutor(max_workers=1)
        self._executor.submit(self._stream_worker, key, model, body)
        self._timer = self.set_interval(0.15, self._poll)

    def _stream_worker(self, key: str, model: str, body: dict) -> None:
        try:
            with httpx.Client(timeout=300) as client:
                with client.stream(
                    "POST",
                    "https://api.deepseek.com/chat/completions",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                    },
                    json=body,
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                self._chunks.append(token)
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass
        except Exception as e:
            self._error = str(e)
        self._done = True

    def _poll(self) -> None:
        try:
            log = self.query_one("#analysis-result", TextArea)
            if self._chunks:
                clean = _strip_markdown("".join(self._chunks))
                log.text = clean
        except Exception:
            pass

        if not self._done:
            return

        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        if self._executor is not None:
            self._executor.shutdown(wait=False)
            self._executor = None
        self._busy = False

        try:
            btn = self.query_one("#btn-run", Button)
            btn.disabled = False
            btn.label = t("run_analysis")
        except Exception:
            pass

        try:
            log = self.query_one("#analysis-result", TextArea)
            if self._error:
                log.text += f"\n\nError: {self._error}"
            elif not self._chunks:
                log.text = t("no_response")
        except Exception:
            pass

        self._done = False

    def _show_error(self, msg: str) -> None:
        try:
            log = self.query_one("#analysis-result", TextArea)
            log.text = msg
        except Exception:
            pass
