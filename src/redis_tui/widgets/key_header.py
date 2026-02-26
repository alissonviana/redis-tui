from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Label, Static
from textual.message import Message
from redis_tui.models.key_info import KeyInfo, KeyType


class KeyHeader(Horizontal):
    """Header bar showing key name, type, TTL and action buttons."""

    class DeleteRequested(Message):
        def __init__(self, key_name: str) -> None:
            super().__init__()
            self.key_name = key_name

    class RefreshRequested(Message):
        def __init__(self, key_name: str) -> None:
            super().__init__()
            self.key_name = key_name

    class RenameRequested(Message):
        def __init__(self, key_name: str) -> None:
            super().__init__()
            self.key_name = key_name

    class TTLRequested(Message):
        def __init__(self, key_name: str, current_ttl: int) -> None:
            super().__init__()
            self.key_name = key_name
            self.current_ttl = current_ttl

    def __init__(self, key_info: KeyInfo, *args, **kwargs):
        super().__init__(*args, id="key-header", **kwargs)
        self._key_info = key_info

    def compose(self) -> ComposeResult:
        info = self._key_info
        yield Label(info.name, id="key-name-label")
        yield Label(f" {info.type.icon()} {info.type.value} ", id="key-type-badge")
        yield Label(f"TTL: {info.ttl_display()}", id="key-ttl-label")
        with Horizontal(id="key-actions"):
            yield Button("Refresh", id="btn-refresh", variant="default")
            yield Button("TTL", id="btn-ttl", variant="default")
            yield Button("Rename", id="btn-rename", variant="default")
            yield Button("Delete", id="btn-delete", classes="-danger")

    def update_info(self, key_info: KeyInfo) -> None:
        self._key_info = key_info
        self.query_one("#key-name-label", Label).update(key_info.name)
        self.query_one("#key-type-badge", Label).update(
            f" {key_info.type.icon()} {key_info.type.value} "
        )
        self.query_one("#key-ttl-label", Label).update(f"TTL: {key_info.ttl_display()}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "btn-delete":
            self.post_message(self.DeleteRequested(self._key_info.name))
        elif event.button.id == "btn-refresh":
            self.post_message(self.RefreshRequested(self._key_info.name))
        elif event.button.id == "btn-ttl":
            self.post_message(self.TTLRequested(self._key_info.name, self._key_info.ttl))
        elif event.button.id == "btn-rename":
            self.post_message(self.RenameRequested(self._key_info.name))
