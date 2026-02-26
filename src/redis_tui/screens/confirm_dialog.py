from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmDialog(ModalScreen[bool]):
    """Generic confirmation dialog."""

    def __init__(self, message: str, title: str = "Confirm", *args, **kwargs):
        super().__init__(*args, id="confirm-dialog", **kwargs)
        self._message = message
        self._title = title

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-panel"):
            yield Label(self._title, id="confirm-title")
            yield Label(self._message, id="confirm-message")
            with Horizontal(id="confirm-actions"):
                yield Button("Cancel", id="btn-cancel", variant="default")
                yield Button("Confirm", id="btn-confirm", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)
