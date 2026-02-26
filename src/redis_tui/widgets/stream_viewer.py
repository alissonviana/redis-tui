from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Label
from textual.message import Message


class StreamViewer(Vertical):
    """Viewer for Redis Stream values (read-only in Phase 2)."""

    def __init__(self, key_name: str, data: list, *args, **kwargs):
        super().__init__(*args, id="stream-viewer", **kwargs)
        self._key_name = key_name
        # data: list of (id, {field: value}) tuples from xrange
        self._data = data

    def compose(self) -> ComposeResult:
        yield Label(f"Stream entries: {len(self._data)}", markup=False)
        table = DataTable(id="stream-table", cursor_type="row", zebra_stripes=True)
        yield table

    def on_mount(self) -> None:
        table = self.query_one("#stream-table", DataTable)
        # Collect all unique field names
        all_fields: set[str] = set()
        for entry_id, fields in self._data:
            if isinstance(fields, dict):
                all_fields.update(fields.keys())

        columns = ["ID"] + sorted(all_fields)
        table.add_columns(*columns)

        for entry_id, fields in self._data:
            if isinstance(fields, dict):
                row = [str(entry_id)] + [str(fields.get(f, "")) for f in sorted(all_fields)]
            else:
                row = [str(entry_id), str(fields)]
            table.add_row(*row, key=str(entry_id))
