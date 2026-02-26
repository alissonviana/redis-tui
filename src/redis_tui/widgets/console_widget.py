from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, RichLog
from textual.message import Message
from rich.text import Text


class ConsoleWidget(Vertical):
    """Built-in Redis CLI console."""

    class CommandExecuted(Message):
        def __init__(self, command: str) -> None:
            super().__init__()
            self.command = command

    def __init__(self, *args, **kwargs):
        super().__init__(*args, id="console-widget", **kwargs)
        self._history: list[str] = []
        self._history_idx: int = -1

    def compose(self) -> ComposeResult:
        yield RichLog(id="console-log", highlight=True, markup=False, wrap=True)
        yield Input(placeholder="redis> ", id="console-input")

    def on_mount(self) -> None:
        log = self.query_one("#console-log", RichLog)
        log.write(Text.from_markup("[dim]Redis Console - type commands and press Enter[/dim]"))

    def write_output(self, command: str, result: str, is_error: bool = False) -> None:
        log = self.query_one("#console-log", RichLog)
        log.write(Text.from_markup(f"[bold cyan]> {command}[/bold cyan]"))
        if is_error:
            log.write(Text.from_markup(f"[red]{result}[/red]"))
        else:
            log.write(result)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        command = event.value.strip()
        if not command:
            return
        self._history.append(command)
        self._history_idx = len(self._history)
        event.input.clear()
        self.post_message(self.CommandExecuted(command))

    def on_key(self, event) -> None:
        inp = self.query_one("#console-input", Input)
        if event.key == "up":
            if self._history and self._history_idx > 0:
                self._history_idx -= 1
                inp.value = self._history[self._history_idx]
                event.prevent_default()
        elif event.key == "down":
            if self._history_idx < len(self._history) - 1:
                self._history_idx += 1
                inp.value = self._history[self._history_idx]
            elif self._history_idx == len(self._history) - 1:
                self._history_idx = len(self._history)
                inp.value = ""
            event.prevent_default()
