import time
from concurrent.futures import ThreadPoolExecutor

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Static

from i18n import t
from models.cot_model import CotData

_SPINNER = ["\u25CB", "\u25D4", "\u25D1", "\u25D5", "\u25CF"]


class LoadingScreen(Screen[CotData | None]):
    TITLE = "Loading"
    CSS = """
    LoadingScreen {
        layout: vertical;
        align: center middle;
        background: #0f0f1a;
    }
    #loading-container {
        width: 62;
        height: auto;
        border: thick #2a2a5a;
        background: #16162a;
        padding: 2 4;
        content-align: center middle;
    }
    #loading-title {
        color: #7aafff;
        text-style: bold;
        content-align: center middle;
        height: 3;
    }
    #loading-status {
        color: #c0c0e0;
        content-align: center middle;
        height: 5;
    }
    #loading-spinner {
        color: #7aafff;
        content-align: center middle;
        height: 1;
    }
    """

    def __init__(self, report_type: str = "legacy_futopt", year: int = 2026, start_year: int = 2020) -> None:
        super().__init__()
        self.report_type = report_type
        self.year = year
        self.start_year = start_year
        self._start_time: float = 0.0
        self._status: str = ""
        self._complete: bool = False
        self._result: CotData | None = None
        self._error: str = ""
        self._dismissed: bool = False
        self._spin_idx: int = 0

    def compose(self) -> ComposeResult:
        yield Container(
            Static("[ CFTC COT TUI ]", id="loading-title"),
            Static(f"{t('loading')} {self.report_type} ...", id="loading-status"),
            Static("", id="loading-spinner"),
            id="loading-container",
        )

    def on_mount(self) -> None:
        self._start_time = time.monotonic()
        self._start_worker()
        self.set_interval(0.15, self._tick)

    def _tick(self) -> None:
        elapsed = time.monotonic() - self._start_time
        if self._complete:
            self._handle_complete(elapsed)
            return
        self._spin_idx = (self._spin_idx + 1) % len(_SPINNER)
        try:
            status = self._status or f"Loading {self.report_type} ({self.start_year}-{self.year}) ..."
            s = self.query_one("#loading-status", Static)
            s.update(f"{status} [{elapsed:.0f}s]")
            sp = self.query_one("#loading-spinner", Static)
            sp.update(_SPINNER[self._spin_idx])
        except Exception:
            pass

    def _handle_complete(self, elapsed: float) -> None:
        if self._dismissed:
            return
        self._dismissed = True
        self._complete = False
        if hasattr(self, '_pool'):
            self._pool.shutdown(wait=False)
        if self._error:
            self._status = f"Error: {self._error}"
            try:
                s = self.query_one("#loading-status", Static)
                s.update(self._status)
                sp = self.query_one("#loading-spinner", Static)
                sp.update("")
            except Exception:
                pass
            return
        if self._result is not None:
            self.dismiss(self._result)
            return
        try:
            s = self.query_one("#loading-status", Static)
            s.update("Failed to load data")
        except Exception:
            pass

    def _start_worker(self) -> None:
        self._pool = ThreadPoolExecutor(max_workers=1)

        def _do() -> CotData | None:
            model = CotData(report_type=self.report_type, year=self.year, start_year=self.start_year)

            def _status(msg: str) -> None:
                self._status = msg

            model.load(status_callback=_status)
            return model

        def _on_done(fut) -> None:
            try:
                model = fut.result()
                self._result = model
            except Exception as e:
                self._error = str(e)
            self._complete = True

        self._pool.submit(_do).add_done_callback(_on_done)
