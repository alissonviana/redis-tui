from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static
from textual.widgets.select import NoSelection
from redis_tui.models.settings import AppSettings


class SettingsScreen(ModalScreen):
    """Settings configuration modal."""

    DEFAULT_CSS = ""

    def __init__(self, current: AppSettings, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current = current

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-panel"):
            yield Static("Settings", id="settings-title", markup=False)

            yield Label("Key Separator", markup=False)
            yield Input(
                value=self._current.key_separator,
                id="inp-separator",
                placeholder=":",
            )

            yield Label("SCAN Count (keys per batch)", markup=False)
            yield Input(
                value=str(self._current.scan_count),
                id="inp-scan-count",
                placeholder="100",
            )

            yield Label("Auto-refresh Interval (seconds, 0=off)", markup=False)
            yield Input(
                value=str(self._current.auto_refresh_interval),
                id="inp-refresh",
                placeholder="0",
            )

            yield Label("Max Keys to Display", markup=False)
            yield Input(
                value=str(self._current.max_keys_display),
                id="inp-max-keys",
                placeholder="10000",
            )

            yield Label("Theme", markup=False)
            yield Select(
                [
                    ("Textual Dark", "textual-dark"),
                    ("Textual Light", "textual-light"),
                    ("Nord", "nord"),
                    ("Gruvbox", "gruvbox"),
                    ("Dracula", "dracula"),
                    ("Tokyo Night", "tokyo-night"),
                    ("Monokai", "monokai"),
                    ("Flexoki", "flexoki"),
                    ("Catppuccin Mocha", "catppuccin-mocha"),
                    ("Catppuccin Latte", "catppuccin-latte"),
                    ("Catppuccin Frappe", "catppuccin-frappe"),
                    ("Catppuccin Macchiato", "catppuccin-macchiato"),
                    ("Solarized Dark", "solarized-dark"),
                    ("Solarized Light", "solarized-light"),
                    ("Rose Pine", "rose-pine"),
                    ("Rose Pine Moon", "rose-pine-moon"),
                    ("Rose Pine Dawn", "rose-pine-dawn"),
                    ("Atom One Dark", "atom-one-dark"),
                    ("Atom One Light", "atom-one-light"),
                ],
                value=self._current.theme,
                id="sel-theme",
                allow_blank=False,
            )

            yield Static("", id="settings-error", markup=False)

            with Horizontal(id="settings-actions"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-save":
            self._save()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)

    def _save(self) -> None:
        error = self.query_one("#settings-error", Static)
        try:
            separator = self.query_one("#inp-separator", Input).value.strip() or ":"
            scan_count = int(self.query_one("#inp-scan-count", Input).value.strip() or "100")
            refresh = int(self.query_one("#inp-refresh", Input).value.strip() or "0")
            max_keys = int(self.query_one("#inp-max-keys", Input).value.strip() or "10000")
            theme_select = self.query_one("#sel-theme", Select)
            theme = str(theme_select.value) if not isinstance(theme_select.value, NoSelection) else "dark"

            if scan_count < 1:
                raise ValueError("SCAN count must be >= 1")
            if max_keys < 1:
                raise ValueError("Max keys must be >= 1")

            settings = AppSettings(
                key_separator=separator,
                scan_count=scan_count,
                auto_refresh_interval=refresh,
                theme=theme,
                max_keys_display=max_keys,
            )
            self.dismiss(settings)
        except ValueError as e:
            error.update(f"Error: {e}")
