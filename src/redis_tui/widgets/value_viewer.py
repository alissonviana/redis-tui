from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static
from textual.message import Message
from redis_tui.models.key_info import KeyInfo, KeyType
from redis_tui.widgets.key_header import KeyHeader
from redis_tui.widgets.string_viewer import StringViewer
from redis_tui.widgets.hash_viewer import HashViewer
from redis_tui.widgets.list_viewer import ListViewer
from redis_tui.widgets.set_viewer import SetViewer
from redis_tui.widgets.zset_viewer import ZSetViewer
from redis_tui.widgets.stream_viewer import StreamViewer


class ValueViewer(Vertical):
    """Content area showing key header + type-specific viewer."""

    class SaveRequested(Message):
        def __init__(self, key_name: str, new_value: str, key_type: KeyType) -> None:
            super().__init__()
            self.key_name = key_name
            self.new_value = new_value
            self.key_type = key_type

    def __init__(self, *args, **kwargs):
        super().__init__(*args, id="content-area", **kwargs)
        self._current_key: KeyInfo | None = None

    def compose(self) -> ComposeResult:
        yield Static(
            "Select a key from the tree to view its value",
            id="empty-state",
            markup=False,
        )

    async def show_key(self, key_info: KeyInfo, value) -> None:
        self._current_key = key_info
        await self._rebuild(key_info, value)

    async def show_message(self, message: str) -> None:
        """Show a plain message (e.g. after deleting a key)."""
        await self.query("#key-header").remove()
        for widget_id in ("string-viewer", "hash-viewer", "list-viewer",
                          "set-viewer", "zset-viewer", "stream-viewer", "empty-state"):
            await self.query(f"#{widget_id}").remove()
        await self.mount(Static(message, id="empty-state", markup=False))

    async def _rebuild(self, key_info: KeyInfo, value) -> None:
        # Remove all existing content
        await self.query("#key-header").remove()
        for widget_id in ("string-viewer", "hash-viewer", "list-viewer",
                          "set-viewer", "zset-viewer", "stream-viewer", "empty-state"):
            await self.query(f"#{widget_id}").remove()

        await self.mount(KeyHeader(key_info))

        if key_info.type == KeyType.STRING:
            str_val = value if isinstance(value, str) else str(value or "")
            await self.mount(StringViewer(str_val))

        elif key_info.type == KeyType.HASH:
            data = value if isinstance(value, dict) else {}
            await self.mount(HashViewer(key_info.name, data))

        elif key_info.type == KeyType.LIST:
            data = list(value) if value else []
            await self.mount(ListViewer(key_info.name, data))

        elif key_info.type == KeyType.SET:
            data = set(value) if value else set()
            await self.mount(SetViewer(key_info.name, data))

        elif key_info.type == KeyType.ZSET:
            # value is list of (member, score) tuples
            data = list(value) if value else []
            await self.mount(ZSetViewer(key_info.name, data))

        elif key_info.type == KeyType.STREAM:
            data = list(value) if value else []
            await self.mount(StreamViewer(key_info.name, data))

        else:
            preview = str(value)[:500] if value is not None else "(empty)"
            await self.mount(
                Static(
                    f"Unknown type '{key_info.type.value}'\n\n{preview}",
                    id="empty-state",
                    markup=False,
                )
            )

    # --- Event forwarding to Screen ---

    def on_key_header_delete_requested(self, event: KeyHeader.DeleteRequested) -> None:
        event.stop()
        self.screen.on_key_header_delete_requested(event)

    def on_key_header_refresh_requested(self, event: KeyHeader.RefreshRequested) -> None:
        event.stop()
        self.screen.on_key_header_refresh_requested(event)

    def on_key_header_ttl_requested(self, event: KeyHeader.TTLRequested) -> None:
        event.stop()
        self.screen.on_key_header_ttl_requested(event)

    def on_key_header_rename_requested(self, event: KeyHeader.RenameRequested) -> None:
        event.stop()
        self.screen.on_key_header_rename_requested(event)

    def on_string_viewer_save_requested(self, event: StringViewer.SaveRequested) -> None:
        event.stop()
        if self._current_key:
            self.post_message(
                self.SaveRequested(
                    self._current_key.name,
                    event.new_value,
                    self._current_key.type,
                )
            )

    # Forward hash/list/set/zset events to screen
    def on_hash_viewer_field_added(self, event: HashViewer.FieldAdded) -> None:
        event.stop()
        self.screen.on_hash_viewer_field_added(event)

    def on_hash_viewer_field_deleted(self, event: HashViewer.FieldDeleted) -> None:
        event.stop()
        self.screen.on_hash_viewer_field_deleted(event)

    def on_list_viewer_push_requested(self, event: ListViewer.PushRequested) -> None:
        event.stop()
        self.screen.on_list_viewer_push_requested(event)

    def on_list_viewer_remove_requested(self, event: ListViewer.RemoveRequested) -> None:
        event.stop()
        self.screen.on_list_viewer_remove_requested(event)

    def on_set_viewer_member_added(self, event: SetViewer.MemberAdded) -> None:
        event.stop()
        self.screen.on_set_viewer_member_added(event)

    def on_set_viewer_member_removed(self, event: SetViewer.MemberRemoved) -> None:
        event.stop()
        self.screen.on_set_viewer_member_removed(event)

    def on_zset_viewer_member_added(self, event: ZSetViewer.MemberAdded) -> None:
        event.stop()
        self.screen.on_zset_viewer_member_added(event)

    def on_zset_viewer_member_removed(self, event: ZSetViewer.MemberRemoved) -> None:
        event.stop()
        self.screen.on_zset_viewer_member_removed(event)
