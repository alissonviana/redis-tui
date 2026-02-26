from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Input, Select, Label, Static, Button
from textual.message import Message
from textual.reactive import reactive
from redis_tui.widgets.key_tree import RedisKeyTree


class Sidebar(Vertical):
    """Left sidebar with database selector, search, and key tree."""

    DEFAULT_CSS = ""

    class DbChanged(Message):
        def __init__(self, db: int) -> None:
            super().__init__()
            self.db = db

    class SearchChanged(Message):
        def __init__(self, pattern: str) -> None:
            super().__init__()
            self.pattern = pattern

    class BatchDeleteRequested(Message):
        def __init__(self, keys: set[str]) -> None:
            super().__init__()
            self.keys = keys

    key_count: reactive[int] = reactive(0)
    scanning: reactive[bool] = reactive(False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, id="sidebar", **kwargs)
        self._db_options: list[tuple[str, int]] = [(f"db{i}", i) for i in range(16)]

    def compose(self) -> ComposeResult:
        yield Select(
            [(f"db{i}", i) for i in range(16)],
            value=0,
            id="db-selector",
            prompt="Select database",
        )
        yield Input(
            placeholder="Search keys...",
            id="search-input",
        )
        yield RedisKeyTree(id="key-tree")
        yield Label("", id="key-count")
        with Horizontal(id="batch-bar", classes="hidden"):
            yield Label("", id="batch-count", markup=False)
            yield Button("Delete", id="btn-batch-delete", classes="-danger")
            yield Button("Clear", id="btn-batch-clear")

    def watch_key_count(self, count: int) -> None:
        label = self.query_one("#key-count", Label)
        suffix = " (scanning...)" if self.scanning else ""
        label.update(f" {count} keys{suffix}")

    def watch_scanning(self, scanning: bool) -> None:
        label = self.query_one("#key-count", Label)
        suffix = " (scanning...)" if scanning else ""
        label.update(f" {self.key_count} keys{suffix}")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "db-selector" and event.value is not None:
            self.post_message(self.DbChanged(int(event.value)))

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.post_message(self.SearchChanged(event.value or "*"))

    def on_redis_key_tree_selection_changed(
        self, event: RedisKeyTree.SelectionChanged
    ) -> None:
        event.stop()
        count = len(event.selected_keys)
        bar = self.query_one("#batch-bar")
        if count > 0:
            bar.remove_class("hidden")
            self.query_one("#batch-count", Label).update(f"{count} selected")
        else:
            bar.add_class("hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-batch-delete":
            event.stop()
            tree = self.query_one(RedisKeyTree)
            selected = tree.get_selected_keys()
            if selected:
                self.post_message(self.BatchDeleteRequested(selected))
        elif event.button.id == "btn-batch-clear":
            event.stop()
            tree = self.query_one(RedisKeyTree)
            tree.clear_selection()

    def get_tree(self) -> RedisKeyTree:
        return self.query_one(RedisKeyTree)

    def update_db_counts(self, counts: dict[int, int]) -> None:
        """Update the database selector options to show key counts.

        Args:
            counts: Mapping of {db_index: key_count} for databases that
                    contain at least one key.  Databases absent from the
                    mapping are shown without a count suffix.
        """
        options: list[tuple[str, int]] = []
        for i in range(16):
            count = counts.get(i)
            if count:
                label = f"db{i} ({count})"
            else:
                label = f"db{i}"
            options.append((label, i))
        selector = self.query_one("#db-selector", Select)
        # Preserve the currently selected value across the options refresh
        current_value = selector.value
        selector.set_options(options)
        # Restore selection (set_options resets to the first item)
        try:
            selector.value = current_value
        except Exception:
            pass
