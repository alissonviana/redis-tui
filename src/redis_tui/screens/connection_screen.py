from __future__ import annotations
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, ListItem, ListView, Static
from textual.message import Message
from redis_tui.models.connection import ConnectionConfig
from redis_tui.services.config_store import ConfigStore
from redis_tui.screens.connection_dialog import ConnectionDialog


class ConnectionListItem(ListItem):
    def __init__(self, config: ConnectionConfig, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config

    def compose(self) -> ComposeResult:
        cfg = self.config
        mode_label = f" [{cfg.mode.value}]" if cfg.mode.value != "standalone" else ""
        ssh_label = " [SSH]" if cfg.ssh_host else ""
        yield Label(
            f"  * {cfg.name}{mode_label}{ssh_label}\n"
            f"    {cfg.host}:{cfg.port}  db{cfg.db}",
            markup=False,
        )


class ConnectionScreen(Screen):
    """Initial screen for managing Redis connections."""

    BINDINGS = [
        ("n", "new_connection", "New"),
        ("e", "edit_connection", "Edit"),
        ("d", "delete_connection", "Delete"),
        Binding("enter", "connect", "Connect", priority=True),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, id="connection-screen", **kwargs)
        self._store = ConfigStore()
        self._connections: list[ConnectionConfig] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="connection-panel"):
            yield Label("Redis TUI", id="connection-title")
            yield ListView(id="connections-list")
            with Horizontal(id="connection-actions"):
                yield Button("+ New", id="btn-new", variant="primary")
                yield Button("Edit", id="btn-edit")
                yield Button("Delete", id="btn-delete", variant="error")
                yield Button("Connect", id="btn-connect", variant="primary")

    def on_mount(self) -> None:
        self._load_connections()

    def _load_connections(self) -> None:
        self._connections = self._store.load_connections()
        lv = self.query_one("#connections-list", ListView)
        lv.clear()
        for conn in self._connections:
            lv.append(ConnectionListItem(conn))

        # Add default localhost if empty
        if not self._connections:
            default = ConnectionConfig(name="localhost", host="localhost", port=6379)
            self._connections.append(default)
            self._store.save_connections(self._connections)
            lv.append(ConnectionListItem(default))

    def _selected_config(self) -> ConnectionConfig | None:
        lv = self.query_one("#connections-list", ListView)
        if lv.highlighted_child is None:
            return None
        idx = lv.index
        if idx is not None and 0 <= idx < len(self._connections):
            return self._connections[idx]
        return None

    def action_new_connection(self) -> None:
        self.app.push_screen(ConnectionDialog(), self._on_connection_saved)

    def action_edit_connection(self) -> None:
        config = self._selected_config()
        if config:
            self.app.push_screen(ConnectionDialog(config), self._on_connection_saved)

    def action_delete_connection(self) -> None:
        config = self._selected_config()
        if config:
            self._store.remove_connection(config.id)
            self._load_connections()

    def action_connect(self) -> None:
        config = self._selected_config()
        if config:
            self.app.connect_to(config)

    def _on_connection_saved(self, config: ConnectionConfig | None) -> None:
        if config:
            self._store.add_connection(config)
            self._load_connections()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        actions = {
            "btn-new": self.action_new_connection,
            "btn-edit": self.action_edit_connection,
            "btn-delete": self.action_delete_connection,
            "btn-connect": self.action_connect,
        }
        if event.button.id in actions:
            event.stop()
            actions[event.button.id]()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        pass  # single click only highlights; use Enter or Connect button to connect
