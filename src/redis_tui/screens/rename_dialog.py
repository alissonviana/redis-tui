from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class RenameDialog(ModalScreen[str | None]):
    """Modal for renaming a Redis key.

    Returns:
        str: New key name if confirmed
        None: If cancelled
    """

    def __init__(self, key_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._key_name = key_name

    def compose(self) -> ComposeResult:
        with Vertical(id="rename-dialog"):
            yield Label("Rename Key", classes="form-title")
            yield Label(f"Current name: {self._key_name}", markup=False)
            yield Label("New key name:")
            yield Input(
                value=self._key_name,
                id="inp-new-name",
                placeholder="Enter new key name",
            )
            yield Label("", id="rename-error")
            with Horizontal(id="dialog-actions"):
                yield Button("Cancel", id="btn-cancel", variant="default")
                yield Button("Save", id="btn-save", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-save":
            new_name = self.query_one("#inp-new-name", Input).value.strip()
            error_label = self.query_one("#rename-error", Label)
            if not new_name:
                error_label.update("[red]Key name cannot be empty[/red]")
                return
            self.dismiss(new_name)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
        elif event.key == "enter":
            new_name = self.query_one("#inp-new-name", Input).value.strip()
            error_label = self.query_one("#rename-error", Label)
            if not new_name:
                error_label.update("[red]Key name cannot be empty[/red]")
                return
            self.dismiss(new_name)
