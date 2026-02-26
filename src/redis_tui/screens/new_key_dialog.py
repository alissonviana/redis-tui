from __future__ import annotations
from dataclasses import dataclass
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select


@dataclass
class NewKeyData:
    name: str
    type: str
    value: str
    ttl: int  # -1 = no TTL


class NewKeyDialog(ModalScreen[NewKeyData | None]):
    """Modal for creating a new Redis key."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, id="new-key-dialog", **kwargs)

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="new-key-form"):
            yield Label("New Key", classes="form-title")
            yield Label("Key Name")
            yield Input(placeholder="mykey:name", id="inp-key-name")
            yield Label("Type")
            yield Select(
                [
                    ("String", "string"),
                    ("Hash", "hash"),
                    ("List", "list"),
                    ("Set", "set"),
                    ("Sorted Set", "zset"),
                ],
                value="string",
                id="sel-key-type",
            )
            yield Label("Value (initial)")
            yield Input(placeholder="Initial value or first member...", id="inp-key-value")
            yield Label("TTL (seconds, 0 = no expiry)")
            yield Input(placeholder="0", id="inp-key-ttl", value="0")
            yield Label("", id="new-key-error")
            with Horizontal(id="dialog-actions"):
                yield Button("Cancel", id="btn-cancel")
                yield Button("Create", id="btn-create", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-create":
            name = self.query_one("#inp-key-name", Input).value.strip()
            value = self.query_one("#inp-key-value", Input).value.strip()
            ttl_str = self.query_one("#inp-key-ttl", Input).value.strip()
            error_label = self.query_one("#new-key-error", Label)

            if not name:
                error_label.update("[red]Key name is required[/red]")
                return

            try:
                ttl = int(ttl_str) if ttl_str else 0
                if ttl < 0:
                    ttl = 0
            except ValueError:
                ttl = 0

            type_select = self.query_one("#sel-key-type", Select)
            key_type = str(type_select.value) if type_select.value is not None else "string"

            self.dismiss(NewKeyData(name=name, type=key_type, value=value, ttl=ttl))

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
