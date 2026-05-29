from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, RadioButton, RadioSet

from config import REPORT_TYPES
from i18n import t


class DatasetScreen(ModalScreen[str | None]):
    CSS = """
    DatasetScreen {
        align: center middle;
    }
    #dataset-dialog {
        width: 50;
        height: auto;
        border: thick #2a2a5a;
        background: #16162a;
        padding: 1 2;
    }
    #dataset-title {
        color: #7aafff;
        text-style: bold;
        height: 2;
        content-align: center middle;
    }
    #dataset-radio {
        height: auto;
        margin: 1 0;
    }
    #dataset-buttons {
        height: 3;
        align: center middle;
    }
    RadioButton {
        color: #c0c0e0;
    }
    RadioSet:focus RadioButton.-selected {
        color: #7aafff;
        text-style: bold;
    }
    """

    def __init__(self, current: str = "legacy_futopt") -> None:
        super().__init__()
        self.title = "Select Report Type"
        self.current = current

    def compose(self) -> ComposeResult:
        buttons = []
        for key, label in REPORT_TYPES.items():
            rb = RadioButton(label, id=f"ds-{key}")
            if key == self.current:
                rb.value = True
            buttons.append(rb)

        with Vertical(id="dataset-dialog"):
            yield Label(t("select_dataset"), id="dataset-title")
            yield RadioSet(*buttons, id="dataset-radio")
            with Horizontal(id="dataset-buttons"):
                yield Button("OK", variant="primary", id="ds-ok")
                yield Button(t("cancel"), variant="default", id="ds-cancel")

    def on_radio_set_changed(self, _: RadioSet.Changed) -> None:
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ds-ok":
            rs = self.query_one(RadioSet)
            btn = rs.pressed_button
            if btn is not None and btn.id and btn.id.startswith("ds-"):
                self.dismiss(btn.id[3:])
            else:
                self.dismiss(None)
        else:
            self.dismiss(None)
