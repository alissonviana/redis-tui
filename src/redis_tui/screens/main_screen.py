from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.events import MouseDown, MouseMove, MouseUp
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Footer, Header, TabbedContent, TabPane
from redis_tui.models.connection import ConnectionConfig
from redis_tui.models.key_info import KeyInfo, KeyType
from redis_tui.models.settings import AppSettings
from redis_tui.services.connection_manager import ConnectionManager
from redis_tui.services.redis_client import RedisClient
from redis_tui.services.key_scanner import KeyScanner
from redis_tui.services.settings_store import SettingsStore
from redis_tui.widgets.sidebar import Sidebar
from redis_tui.widgets.key_tree import RedisKeyTree
from redis_tui.widgets.value_viewer import ValueViewer
from redis_tui.widgets.key_header import KeyHeader
from redis_tui.widgets.console_widget import ConsoleWidget
from redis_tui.widgets.server_info_widget import ServerInfoWidget
from redis_tui.widgets.hash_viewer import HashViewer
from redis_tui.widgets.list_viewer import ListViewer
from redis_tui.widgets.set_viewer import SetViewer
from redis_tui.widgets.zset_viewer import ZSetViewer
from redis_tui.screens.confirm_dialog import ConfirmDialog
from redis_tui.screens.new_key_dialog import NewKeyDialog, NewKeyData
from redis_tui.screens.ttl_dialog import TTLDialog
from redis_tui.screens.rename_dialog import RenameDialog
from redis_tui.screens.settings_screen import SettingsScreen
from redis_tui.widgets.pubsub_widget import PubSubWidget
from redis_tui.widgets.memory_widget import MemoryWidget


class SidebarDivider(Widget):
    """Draggable vertical divider to resize the sidebar."""

    _SIDEBAR_MIN = 15
    _SIDEBAR_MAX = 80

    def __init__(self) -> None:
        super().__init__(id="sidebar-divider")
        self._dragging = False
        self._drag_start_x = 0
        self._sidebar_start_width = 0

    def on_mouse_down(self, event: MouseDown) -> None:
        event.stop()
        self._dragging = True
        self._drag_start_x = event.screen_x
        self._sidebar_start_width = self.screen.query_one(Sidebar).size.width
        self.capture_mouse()

    def on_mouse_move(self, event: MouseMove) -> None:
        if not self._dragging:
            return
        event.stop()
        delta = event.screen_x - self._drag_start_x
        new_width = max(self._SIDEBAR_MIN, min(self._SIDEBAR_MAX, self._sidebar_start_width + delta))
        self.screen.query_one(Sidebar).styles.width = new_width

    def on_mouse_up(self, event: MouseUp) -> None:
        if self._dragging:
            event.stop()
            self._dragging = False
            self.release_mouse()

    def render(self) -> str:
        return ""


class MainScreen(Screen):
    """Main application screen with sidebar and content area."""

    BINDINGS = [
        ("f5", "refresh_keys", "Refresh"),
        ("escape", "back_to_connections", "Connections"),
        ("ctrl+d", "toggle_dark", "Dark"),
        ("n", "new_key", "New Key"),
        ("ctrl+t", "toggle_console", "Console"),
        ("ctrl+i", "show_server_info", "Info"),
        ("ctrl+p", "show_pubsub", "Pub/Sub"),
        ("ctrl+m", "show_memory", "Memory"),
        ("ctrl+s", "open_settings", "Settings"),
    ]

    def __init__(
        self,
        manager: ConnectionManager,
        config: ConnectionConfig,
        *args,
        **kwargs,
    ):
        super().__init__(*args, id="main-screen", **kwargs)
        self._manager = manager
        self._config = config
        self._client = RedisClient(manager)
        self._all_keys: list[str] = []
        self._current_key: str | None = None
        self._search_pattern: str = "*"
        self._console_visible: bool = False
        self._settings_store = SettingsStore()
        self._settings = self._settings_store.load()
        self._user_interacted: bool = False  # True após primeiro expand/select

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            yield Sidebar()
            yield SidebarDivider()
            with TabbedContent(id="content-tabs"):
                with TabPane("Browser", id="tab-browser"):
                    yield ValueViewer()
                with TabPane("Console", id="tab-console"):
                    yield ConsoleWidget()
                with TabPane("Server Info", id="tab-info"):
                    yield ServerInfoWidget({})
                with TabPane("Pub/Sub", id="tab-pubsub"):
                    yield PubSubWidget()
                with TabPane("Memory", id="tab-memory"):
                    yield MemoryWidget()
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"Redis TUI - {self._config.name}"
        self.sub_title = f"db{self._config.db}"
        self.run_worker(self._load_all_keys(), exclusive=True, name="load-keys")
        self.run_worker(self._load_db_counts(), name="load-db-counts")

    async def _load_all_keys(self) -> None:
        sidebar = self.query_one(Sidebar)
        tree = self.query_one(RedisKeyTree)
        sidebar.scanning = True
        self._user_interacted = False
        try:
            scanner = KeyScanner(self._manager.get_client())
            keys: list[str] = []
            BATCH_SIZE = 500

            async for key in scanner.scan_all(
                pattern=self._search_pattern,
                count=500,
            ):
                keys.append(key)
                if len(keys) % BATCH_SIZE == 0:
                    self._all_keys = sorted(keys)
                    sidebar.key_count = len(self._all_keys)
                    # Só atualiza a tree se o usuário ainda não interagiu:
                    # evita resetar folders abertos e seleções ativas
                    if not self._user_interacted:
                        tree.populate(self._all_keys)

            # Populate final — só reseta a tree se o usuário não estiver navegando
            self._all_keys = sorted(keys)
            sidebar.key_count = len(self._all_keys)
            if not self._user_interacted:
                tree.populate(self._all_keys)
            else:
                # Usuário já interagiu: notifica que o scan terminou sem resetar
                self.notify(
                    f"Scan completo: {len(self._all_keys)} keys. F5 para atualizar a tree.",
                    severity="information",
                    timeout=4,
                )
        except Exception as e:
            self.notify(f"Error loading keys: {e}", severity="error")
        finally:
            sidebar.scanning = False

    async def _load_server_info(self) -> None:
        try:
            info = await self._client.get_server_info()
            widget = self.query_one(ServerInfoWidget)
            widget.update_info(info)
            try:
                slowlog = await self._manager.get_client().slowlog_get(128)
                widget.update_slowlog(slowlog)
            except Exception:
                pass
        except Exception as e:
            self.notify(f"Error loading server info: {e}", severity="warning")

    async def _load_db_counts(self) -> None:
        try:
            counts = await self._client.get_keyspace_info()
            sidebar = self.query_one(Sidebar)
            sidebar.update_db_counts(counts)
        except Exception:
            pass

    # --- Actions ---

    def action_refresh_keys(self) -> None:
        self.run_worker(self._load_all_keys(), exclusive=True, name="load-keys")

    def action_back_to_connections(self) -> None:
        self.app.pop_screen()

    def action_toggle_dark(self) -> None:
        self.app.action_change_theme()

    def action_new_key(self) -> None:
        self.app.push_screen(NewKeyDialog(), self._on_new_key)

    def _on_new_key(self, data: NewKeyData | None) -> None:
        if data:
            self.run_worker(self._create_key(data))

    async def _create_key(self, data: NewKeyData) -> None:
        try:
            client = self._manager.get_client()
            ttl = data.ttl if data.ttl > 0 else None
            if data.type == "string":
                if ttl:
                    await client.setex(data.name, ttl, data.value or "")
                else:
                    await client.set(data.name, data.value or "")
            elif data.type == "hash":
                await client.hset(data.name, mapping={"field": data.value or ""})
                if ttl:
                    await client.expire(data.name, ttl)
            elif data.type == "list":
                await client.rpush(data.name, data.value or "")
                if ttl:
                    await client.expire(data.name, ttl)
            elif data.type == "set":
                await client.sadd(data.name, data.value or "")
                if ttl:
                    await client.expire(data.name, ttl)
            elif data.type == "zset":
                await client.zadd(data.name, {data.value or "member": 0.0})
                if ttl:
                    await client.expire(data.name, ttl)
            self.notify(f"Created key '{data.name}'", severity="information")
            await self._load_all_keys()
        except Exception as e:
            self.notify(f"Error creating key: {e}", severity="error")

    def action_toggle_console(self) -> None:
        tabs = self.query_one("#content-tabs", TabbedContent)
        if tabs.active == "tab-console":
            tabs.active = "tab-browser"
        else:
            tabs.active = "tab-console"

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if event.tabbed_content.id == "content-tabs" and event.pane and event.pane.id == "tab-info":
            self.run_worker(self._load_server_info(), name="load-info")

    def action_show_server_info(self) -> None:
        tabs = self.query_one("#content-tabs", TabbedContent)
        tabs.active = "tab-info"

    def action_show_pubsub(self) -> None:
        tabs = self.query_one("#content-tabs", TabbedContent)
        tabs.active = "tab-pubsub"

    def action_show_memory(self) -> None:
        tabs = self.query_one("#content-tabs", TabbedContent)
        tabs.active = "tab-memory"

    def action_open_settings(self) -> None:
        def handle_settings(result: AppSettings | None) -> None:
            if result is not None:
                self._settings = result
                self._settings_store.save(result)
                self.app.theme = result.theme
                self.notify("Settings saved", severity="information")

        self.app.push_screen(SettingsScreen(self._settings), handle_settings)

    # --- Sidebar events ---

    def on_sidebar_db_changed(self, event: Sidebar.DbChanged) -> None:
        event.stop()
        self.run_worker(self._switch_db(event.db), exclusive=True)

    async def _switch_db(self, db: int) -> None:
        try:
            await self._manager.switch_db(db)
            self._client = RedisClient(self._manager)
            self._config = self._manager.config
            self.sub_title = f"db{db}"
            await self._load_all_keys()
        except Exception as e:
            self.notify(f"Error switching db: {e}", severity="error")

    def on_sidebar_search_changed(self, event: Sidebar.SearchChanged) -> None:
        event.stop()
        pattern = event.pattern
        self._search_pattern = (
            f"*{pattern}*" if pattern and "*" not in pattern else (pattern or "*")
        )
        self._user_interacted = False  # nova busca: libera updates progressivos
        self._current_key = None
        self.run_worker(self._load_all_keys(), exclusive=True, name="search-keys")

    def on_sidebar_batch_delete_requested(
        self, event: Sidebar.BatchDeleteRequested
    ) -> None:
        event.stop()
        keys = event.keys

        def handle_confirm(confirmed: bool) -> None:
            if confirmed:
                self.run_worker(self._batch_delete(keys))

        self.app.push_screen(
            ConfirmDialog(f"Delete {len(keys)} keys?", "Batch Delete"),
            handle_confirm,
        )

    async def _batch_delete(self, keys: set[str]) -> None:
        try:
            deleted = await self._client.delete_keys(list(keys))
            self._all_keys = [k for k in self._all_keys if k not in keys]
            tree = self.query_one(RedisKeyTree)
            tree.populate(self._all_keys)
            sidebar = self.query_one(Sidebar)
            sidebar.key_count = len(self._all_keys)
            if self._current_key in keys:
                self._current_key = None
                viewer = self.query_one(ValueViewer)
                await viewer.show_message("Keys deleted. Select another key.")
            self.notify(f"Deleted {deleted} keys", severity="information")
        except Exception as e:
            self.notify(f"Error deleting keys: {e}", severity="error")

    # --- Tree events ---

    def on_redis_key_tree_key_selected(self, event: RedisKeyTree.KeySelected) -> None:
        event.stop()
        self._user_interacted = True
        self._current_key = event.key_name
        # Switch to browser tab
        try:
            tabs = self.query_one("#content-tabs", TabbedContent)
            tabs.active = "tab-browser"
        except Exception:
            pass
        self.run_worker(
            self._load_key_value(event.key_name), exclusive=True, name="load-value"
        )

    def on_redis_key_tree_folder_expanded(self, event: RedisKeyTree.FolderExpanded) -> None:
        event.stop()
        self._user_interacted = True
        prefix = event.prefix
        tree = self.query_one(RedisKeyTree)
        matching_keys = [k for k in self._all_keys if k.startswith(f"{prefix}:")]
        tree.populate_folder(event.node, matching_keys, prefix)

    async def _load_key_value(self, key_name: str) -> None:
        try:
            key_info = await self._client.get_key_info(key_name)
            value = await self._client.get_value(key_name, key_info.type)
            viewer = self.query_one(ValueViewer)
            await viewer.show_key(key_info, value)
        except Exception as e:
            self.notify(f"Error loading key: {e}", severity="error")

    # --- Key Header events ---

    def on_key_header_delete_requested(self, event: KeyHeader.DeleteRequested) -> None:
        key_name = event.key_name

        def handle_confirm(confirmed: bool) -> None:
            if confirmed:
                self.run_worker(self._delete_key(key_name))

        self.app.push_screen(
            ConfirmDialog(f"Delete '{key_name}'?", "Delete Key"),
            handle_confirm,
        )

    async def _delete_key(self, key_name: str) -> None:
        try:
            await self._client.delete_keys([key_name])
            self._all_keys = [k for k in self._all_keys if k != key_name]
            tree = self.query_one(RedisKeyTree)
            tree.populate(self._all_keys)
            sidebar = self.query_one(Sidebar)
            sidebar.key_count = len(self._all_keys)
            self._current_key = None
            viewer = self.query_one(ValueViewer)
            await viewer.show_message("Key deleted. Select another key.")
            self.notify(f"Deleted '{key_name}'", severity="information")
        except Exception as e:
            self.notify(f"Error deleting key: {e}", severity="error")

    def on_key_header_refresh_requested(self, event: KeyHeader.RefreshRequested) -> None:
        if event.key_name:
            self.run_worker(
                self._load_key_value(event.key_name), exclusive=True, name="load-value"
            )

    def on_key_header_ttl_requested(self, event: KeyHeader.TTLRequested) -> None:
        key_name = event.key_name
        current_ttl = event.current_ttl

        def handle_ttl(result: int | None) -> None:
            if result is not None:
                self.run_worker(self._apply_ttl(key_name, result))

        self.app.push_screen(TTLDialog(current_ttl, key_name), handle_ttl)

    async def _apply_ttl(self, key_name: str, ttl: int) -> None:
        try:
            if ttl <= 0:
                await self._client.remove_ttl(key_name)
                self.notify(f"TTL removed from '{key_name}'", severity="information")
            else:
                await self._client.set_ttl(key_name, ttl)
                self.notify(f"TTL set to {ttl}s on '{key_name}'", severity="information")
            # Refresh to show updated TTL
            await self._load_key_value(key_name)
        except Exception as e:
            self.notify(f"Error setting TTL: {e}", severity="error")

    def on_key_header_rename_requested(self, event: KeyHeader.RenameRequested) -> None:
        key_name = event.key_name

        def handle_rename(new_name: str | None) -> None:
            if new_name and new_name != key_name:
                self.run_worker(self._rename_key(key_name, new_name))

        self.app.push_screen(RenameDialog(key_name), handle_rename)

    async def _rename_key(self, old_name: str, new_name: str) -> None:
        try:
            await self._client.rename_key(old_name, new_name)
            self._all_keys = [new_name if k == old_name else k for k in self._all_keys]
            tree = self.query_one(RedisKeyTree)
            tree.populate(self._all_keys)
            self._current_key = new_name
            await self._load_key_value(new_name)
            self.notify(f"Renamed to '{new_name}'", severity="information")
        except Exception as e:
            self.notify(f"Error renaming: {e}", severity="error")

    # --- Value save ---

    def on_value_viewer_save_requested(self, event: ValueViewer.SaveRequested) -> None:
        event.stop()
        self.run_worker(self._save_value(event.key_name, event.new_value))

    async def _save_value(self, key_name: str, value: str) -> None:
        try:
            await self._client.set_string(key_name, value)
            await self._load_key_value(key_name)
            self.notify("Saved!", severity="information")
        except Exception as e:
            self.notify(f"Error saving: {e}", severity="error")

    # --- Hash events ---

    def on_hash_viewer_field_added(self, event: HashViewer.FieldAdded) -> None:
        self.run_worker(self._hash_field_add(event.key_name, event.field, event.value))

    async def _hash_field_add(self, key_name: str, field: str, value: str) -> None:
        try:
            await self._manager.get_client().hset(key_name, field, value)
        except Exception as e:
            self.notify(f"Error adding field: {e}", severity="error")

    def on_hash_viewer_field_deleted(self, event: HashViewer.FieldDeleted) -> None:
        self.run_worker(self._hash_field_del(event.key_name, event.field))

    async def _hash_field_del(self, key_name: str, field: str) -> None:
        try:
            await self._manager.get_client().hdel(key_name, field)
        except Exception as e:
            self.notify(f"Error deleting field: {e}", severity="error")

    # --- List events ---

    def on_list_viewer_push_requested(self, event: ListViewer.PushRequested) -> None:
        self.run_worker(self._list_push(event.key_name, event.value, event.head))

    async def _list_push(self, key_name: str, value: str, head: bool) -> None:
        try:
            client = self._manager.get_client()
            if head:
                await client.lpush(key_name, value)
            else:
                await client.rpush(key_name, value)
            await self._load_key_value(key_name)
        except Exception as e:
            self.notify(f"Error pushing to list: {e}", severity="error")

    def on_list_viewer_remove_requested(self, event: ListViewer.RemoveRequested) -> None:
        self.run_worker(self._list_remove(event.key_name, event.value))

    async def _list_remove(self, key_name: str, value: str) -> None:
        try:
            await self._manager.get_client().lrem(key_name, 1, value)
            await self._load_key_value(key_name)
        except Exception as e:
            self.notify(f"Error removing from list: {e}", severity="error")

    # --- Set events ---

    def on_set_viewer_member_added(self, event: SetViewer.MemberAdded) -> None:
        self.run_worker(self._set_add(event.key_name, event.member))

    async def _set_add(self, key_name: str, member: str) -> None:
        try:
            await self._manager.get_client().sadd(key_name, member)
        except Exception as e:
            self.notify(f"Error adding member: {e}", severity="error")

    def on_set_viewer_member_removed(self, event: SetViewer.MemberRemoved) -> None:
        self.run_worker(self._set_rem(event.key_name, event.member))

    async def _set_rem(self, key_name: str, member: str) -> None:
        try:
            await self._manager.get_client().srem(key_name, member)
        except Exception as e:
            self.notify(f"Error removing member: {e}", severity="error")

    # --- ZSet events ---

    def on_zset_viewer_member_added(self, event: ZSetViewer.MemberAdded) -> None:
        self.run_worker(self._zset_add(event.key_name, event.member, event.score))

    async def _zset_add(self, key_name: str, member: str, score: float) -> None:
        try:
            await self._manager.get_client().zadd(key_name, {member: score})
        except Exception as e:
            self.notify(f"Error adding to sorted set: {e}", severity="error")

    def on_zset_viewer_member_removed(self, event: ZSetViewer.MemberRemoved) -> None:
        self.run_worker(self._zset_rem(event.key_name, event.member))

    async def _zset_rem(self, key_name: str, member: str) -> None:
        try:
            await self._manager.get_client().zrem(key_name, member)
        except Exception as e:
            self.notify(f"Error removing from sorted set: {e}", severity="error")

    # --- Console events ---

    def on_console_widget_command_executed(self, event: ConsoleWidget.CommandExecuted) -> None:
        event.stop()
        self.run_worker(self._exec_console_command(event.command))

    async def _exec_console_command(self, command: str) -> None:
        console = self.query_one(ConsoleWidget)
        try:
            result = await self._client.execute_raw(command)
            output = str(result) if result is not None else "(nil)"
            console.write_output(command, output)
        except Exception as e:
            console.write_output(command, str(e), is_error=True)
