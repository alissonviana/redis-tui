from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input
from textual.message import Message


class ZSetViewer(Vertical):
    """Viewer/editor for Redis Sorted Set values."""

    class MemberAdded(Message):
        def __init__(self, key_name: str, member: str, score: float) -> None:
            super().__init__()
            self.key_name = key_name
            self.member = member
            self.score = score

    class MemberRemoved(Message):
        def __init__(self, key_name: str, member: str) -> None:
            super().__init__()
            self.key_name = key_name
            self.member = member

    def __init__(self, key_name: str, data: list[tuple], *args, **kwargs):
        super().__init__(*args, id="zset-viewer", **kwargs)
        self._key_name = key_name
        # data is list of (member, score) tuples
        self._data = data

    def compose(self) -> ComposeResult:
        table = DataTable(id="zset-table", cursor_type="row", zebra_stripes=True)
        table.add_columns("Member", "Score")
        yield table
        with Horizontal(id="zset-add-row"):
            yield Input(placeholder="Member", id="inp-zset-member")
            yield Input(placeholder="Score (e.g. 1.0)", id="inp-zset-score")
            yield Button("Add", id="btn-zset-add", variant="primary")
        with Horizontal(id="zset-actions"):
            yield Button("Remove Selected", id="btn-zset-remove", variant="error")

    def on_mount(self) -> None:
        table = self.query_one("#zset-table", DataTable)
        for member, score in self._data:
            table.add_row(str(member), str(score), key=str(member))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "btn-zset-add":
            member_inp = self.query_one("#inp-zset-member", Input)
            score_inp = self.query_one("#inp-zset-score", Input)
            member = member_inp.value.strip()
            try:
                score = float(score_inp.value.strip() or "0")
            except ValueError:
                score = 0.0
            if member:
                table = self.query_one("#zset-table", DataTable)
                table.add_row(member, str(score), key=member)
                member_inp.clear()
                score_inp.clear()
                self.post_message(self.MemberAdded(self._key_name, member, score))
        elif event.button.id == "btn-zset-remove":
            table = self.query_one("#zset-table", DataTable)
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
