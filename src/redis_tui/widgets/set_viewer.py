from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input
from textual.message import Message


class SetViewer(Vertical):
    """Viewer/editor for Redis Set values."""

    class MemberAdded(Message):
        def __init__(self, key_name: str, member: str) -> None:
            super().__init__()
            self.key_name = key_name
            self.member = member

    class MemberRemoved(Message):
        def __init__(self, key_name: str, member: str) -> None:
            super().__init__()
            self.key_name = key_name
            self.member = member

    def __init__(self, key_name: str, data: set, *args, **kwargs):
        super().__init__(*args, id="set-viewer", **kwargs)
        self._key_name = key_name
        self._data = data

    def compose(self) -> ComposeResult:
        table = DataTable(id="set-table", cursor_type="row", zebra_stripes=True)
        table.add_columns("Member")
        yield table
        with Horizontal(id="set-add-row"):
            yield Input(placeholder="New member...", id="inp-set-member")
            yield Button("Add", id="btn-set-add", variant="primary")
        with Horizontal(id="set-actions"):
            yield Button("Remove Selected", id="btn-set-remove", variant="error")

    def on_mount(self) -> None:
        table = self.query_one("#set-table", DataTable)
        for member in sorted(self._data):
            table.add_row(str(member), key=str(member))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "btn-set-add":
            inp = self.query_one("#inp-set-member", Input)
            member = inp.value.strip()
            if member:
                table = self.query_one("#set-table", DataTable)
                table.add_row(member, key=member)
                inp.clear()
                self.post_message(self.MemberAdded(self._key_name, member))
        elif event.button.id == "btn-set-remove":
            table = self.query_one("#set-table", DataTable)
            cursor = table.cursor_row
            rows = table.ordered_rows
            if rows and cursor < len(rows):
                try:
                    row_data = table.get_row_at(cursor)
                    member = str(row_data[0])
                    row_key = rows[cursor].key
                    table.remove_row(row_key)
                    self.post_message(self.MemberRemoved(self._key_name, member))
                except Exception:
                    pass
