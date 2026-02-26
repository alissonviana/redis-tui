from __future__ import annotations
from pathlib import Path
from textual.app import App, ComposeResult
from redis_tui.models.connection import ConnectionConfig
from redis_tui.models.settings import AppSettings
from redis_tui.services.connection_manager import ConnectionManager
from redis_tui.services.settings_store import SettingsStore
from redis_tui.screens.connection_screen import ConnectionScreen
from redis_tui.screens.main_screen import MainScreen


class RedisTuiApp(App):
    """Main Redis TUI Application."""

    CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"

    TITLE = "Redis TUI"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("f1", "help", "Help"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._manager = ConnectionManager()
        settings_store = SettingsStore()
        self._settings = settings_store.load()

    def on_mount(self) -> None:
        # Apply theme from settings
        self.theme = self._settings.theme
        self.push_screen(ConnectionScreen())

    def connect_to(self, config: ConnectionConfig) -> None:
        """Connect to a Redis instance and open the main screen."""
        self.run_worker(self._do_connect(config), exclusive=True)

    async def _do_connect(self, config: ConnectionConfig) -> None:
        try:
            await self._manager.connect(config)
            await self.push_screen(MainScreen(self._manager, config))
        except Exception as e:
            self.notify(f"Connection failed: {e}", severity="error", timeout=5)

    def action_help(self) -> None:
        self.notify(
            "Redis TUI  |  q Quit  F5 Refresh  Esc Back  n New Key  Ctrl+T Console  Ctrl+I Info  Ctrl+S Settings",
            timeout=6,
        )

    async def on_unmount(self) -> None:
        await self._manager.disconnect()
