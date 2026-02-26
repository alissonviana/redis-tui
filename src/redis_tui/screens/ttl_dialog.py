from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Switch


class TTLDialog(ModalScreen[int | None]):
    """Modal for editing a key's TTL.

    Returns:
        int: New TTL in seconds (0 = remove TTL / persist)
        None: Cancelled
    """

    def __init__(self, current_ttl: int, key_name: str, *args, **kwargs):
        super().__init__(*args, id="ttl-dialog", **kwargs)
        self._current_ttl = current_ttl
        self._key_name = key_name

    def compose(self) -> ComposeResult:
        with Vertical(id="ttl-panel"):
            yield Label(f"TTL for: {self._key_name}", classes="form-title", markup=False)
            current = (
                f"Current TTL: {self._current_ttl}s"
                if self._current_ttl > 0
                else "Current TTL: No expiry"
            )
            yield Label(current, markup=False)
            yield Label("New TTL (seconds, 0 = remove expiry)")
            yield Input(
                placeholder="e.g. 3600",
                id="inp-ttl",
                value="" if self._current_ttl <= 0 else str(self._current_ttl),
            )
            yield Label("", id="ttl-error")
            with Horizontal(id="dialog-actions"):
                yield Button("Cancel", id="btn-cancel")
                yield Button("Persist (no expiry)", id="btn-persist")
                yield Button("Set TTL", id="btn-set", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-persist":
            self.dismiss(0)  # 0 = remove TTL
        elif event.button.id == "btn-set":
            ttl_str = self.query_one("#inp-ttl", Input).value.strip()
            error_label = self.query_one("#ttl-error", Label)
            try:
                ttl = int(ttl_str)
                if ttl <= 0:
                    ttl = 0
                self.dismiss(ttl)
            except ValueError:
                error_label.update("[red]Please enter a valid number[/red]")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
