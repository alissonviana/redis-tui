from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Label
from textual.message import Message


class HashViewer(Vertical):
    """Viewer/editor for Redis Hash values."""

    BORDER_TITLE = "Hash"

    class FieldChanged(Message):
        def __init__(self, key_name: str, field: str, value: str) -> None:
            super().__init__()
            self.key_name = key_name
            self.field = field
            self.value = value

    class FieldDeleted(Message):
        def __init__(self, key_name: str, field: str) -> None:
            super().__init__()
            self.key_name = key_name
            self.field = field

    class FieldAdded(Message):
        def __init__(self, key_name: str, field: str, value: str) -> None:
            super().__init__()
            self.key_name = key_name
            self.field = field
            self.value = value

    def __init__(self, key_name: str, data: dict, *args, **kwargs):
        super().__init__(*args, id="hash-viewer", **kwargs)
        self._key_name = key_name
        self._data = data

    def compose(self) -> ComposeResult:
        table = DataTable(id="hash-table", cursor_type="row", zebra_stripes=True)
        table.add_columns("Field", "Value")
        yield table
        with Horizontal(id="hash-add-row"):
            yield Input(placeholder="Field name", id="inp-new-field")
            yield Input(placeholder="Value", id="inp-new-value")
            yield Button("Add", id="btn-add-field", variant="primary")
        with Horizontal(id="hash-actions"):
            yield Button("Delete Field", id="btn-del-field", variant="error")

    def on_mount(self) -> None:
        table = self.query_one("#hash-table", DataTable)
        for field, value in self._data.items():
            table.add_row(str(field), str(value), key=str(field))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "btn-add-field":
            field_input = self.query_one("#inp-new-field", Input)
            value_input = self.query_one("#inp-new-value", Input)
            field = field_input.value.strip()
            value = value_input.value.strip()
            if field:
                table = self.query_one("#hash-table", DataTable)
                table.add_row(field, value, key=field)
                field_input.clear()
                value_input.clear()
                self.post_message(self.FieldAdded(self._key_name, field, value))
        elif event.button.id == "btn-del-field":
            table = self.query_one("#hash-table", DataTable)
            cursor = table.cursor_row
            rows = table.ordered_rows
            if rows and cursor < len(rows):
                try:
                    row_data = table.get_row_at(cursor)
                    field = str(row_data[0])
                    row_key = rows[cursor].key
                    table.remove_row(row_key)
                    self.post_message(self.FieldDeleted(self._key_name, field))
                except Exception:
                    pass
