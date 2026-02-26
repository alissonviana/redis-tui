from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input
from textual.message import Message


class ListViewer(Vertical):
    """Viewer/editor for Redis List values."""

    class PushRequested(Message):
        def __init__(self, key_name: str, value: str, head: bool) -> None:
            super().__init__()
            self.key_name = key_name
            self.value = value
            self.head = head  # True = LPUSH, False = RPUSH

    class RemoveRequested(Message):
        def __init__(self, key_name: str, index: int, value: str) -> None:
            super().__init__()
            self.key_name = key_name
            self.index = index
            self.value = value

    def __init__(self, key_name: str, data: list, *args, **kwargs):
        super().__init__(*args, id="list-viewer", **kwargs)
        self._key_name = key_name
        self._data = data

    def compose(self) -> ComposeResult:
        table = DataTable(id="list-table", cursor_type="row", zebra_stripes=True)
        table.add_columns("Index", "Value")
        yield table
        with Horizontal(id="list-add-row"):
            yield Input(placeholder="New value...", id="inp-list-value")
            yield Button("LPUSH", id="btn-lpush", variant="primary")
            yield Button("RPUSH", id="btn-rpush", variant="default")
        with Horizontal(id="list-actions"):
            yield Button("Remove Selected", id="btn-list-remove", variant="error")

    def on_mount(self) -> None:
        table = self.query_one("#list-table", DataTable)
        for i, value in enumerate(self._data):
            table.add_row(str(i), str(value), key=str(i))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id in ("btn-lpush", "btn-rpush"):
            inp = self.query_one("#inp-list-value", Input)
            value = inp.value.strip()
            if value:
                head = event.button.id == "btn-lpush"
                inp.clear()
                self.post_message(self.PushRequested(self._key_name, value, head))
        elif event.button.id == "btn-list-remove":
            table = self.query_one("#list-table", DataTable)
            cursor = table.cursor_row
            rows = table.ordered_rows
            if rows and cursor < len(rows):
                try:
                    row_data = table.get_row_at(cursor)
                    index = int(str(row_data[0]))
                    value = str(row_data[1])
                    row_key = rows[cursor].key
                    table.remove_row(row_key)
                    self.post_message(self.RemoveRequested(self._key_name, index, value))
                except Exception:
                    pass
