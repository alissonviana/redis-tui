from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Label
from textual.worker import Worker


class MemoryWidget(Vertical):
    """Memory usage analysis per key.

    Displays the top keys by memory footprint using the Redis
    MEMORY USAGE command.  Analysis is triggered manually because
    scanning large keyspaces can be slow.
    """

    DEFAULT_CSS = ""

    # Maximum number of keys to show sorted by descending size
    _TOP_N = 100

    def __init__(self, *args, **kwargs):
        super().__init__(*args, id="memory-widget", **kwargs)
        self._sort_asc: bool = False
        self._rows: list[tuple[str, str, int, str]] = []  # key, type, size, encoding

    def compose(self) -> ComposeResult:
        with Horizontal(id="memory-controls"):
            yield Input(
                placeholder="Filter pattern (e.g. user:*)",
                id="memory-pattern-input",
            )
            yield Button("Analyse", id="btn-analyse", variant="primary")
            yield Button("Sort by Size", id="btn-sort", variant="default")
        yield Label("", id="memory-status")
        yield DataTable(
            id="memory-table",
            cursor_type="row",
            zebra_stripes=True,
        )

    def on_mount(self) -> None:
        table = self.query_one("#memory-table", DataTable)
        table.add_columns("Key", "Type", "Size (bytes)", "Encoding")
        table.add_row("--", "--", "--", "Click 'Analyse' to load memory data")

    # ------------------------------------------------------------------
    # Button handling
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "btn-analyse":
            self._start_analysis()
        elif event.button.id == "btn-sort":
            self._toggle_sort()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "memory-pattern-input":
            event.stop()
            self._start_analysis()

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def _start_analysis(self) -> None:
        pattern = self.query_one("#memory-pattern-input", Input).value.strip() or "*"
        status = self.query_one("#memory-status", Label)
        status.update("[yellow]Analysing... this may take a moment.[/yellow]")
        self.run_worker(
            self._analyse(pattern),
            exclusive=True,
            name="memory-analysis",
        )

    async def _analyse(self, pattern: str) -> None:
        try:
            redis_client = self.app._manager.get_client()  # type: ignore[attr-defined]
            rows: list[tuple[str, str, int, str]] = []
            async for key in redis_client.scan_iter(pattern):
                key_str = key.decode("utf-8", errors="replace") if isinstance(key, bytes) else key
                try:
                    size = await redis_client.memory_usage(key_str) or 0
                    key_type = await redis_client.type(key_str)
                    if isinstance(key_type, bytes):
                        key_type = key_type.decode("utf-8", errors="replace")
                    try:
                        encoding = await redis_client.object_encoding(key_str) or ""
                        if isinstance(encoding, bytes):
                            encoding = encoding.decode("utf-8", errors="replace")
                    except Exception:
                        encoding = ""
                    rows.append((key_str, key_type, size, encoding))
                except Exception:
                    continue

            # Sort by size descending and keep top N
            rows.sort(key=lambda r: r[2], reverse=True)
            rows = rows[: self._TOP_N]
            self._rows = rows
            self._sort_asc = False
            self._render_rows(rows)

            status = self.query_one("#memory-status", Label)
            status.update(
                f"[green]Found {len(rows)} keys (showing top {self._TOP_N} by size).[/green]"
            )
        except Exception as exc:
            status = self.query_one("#memory-status", Label)
            status.update(f"[red]Error: {exc}[/red]")

    def _toggle_sort(self) -> None:
        self._sort_asc = not self._sort_asc
        rows = list(self._rows)
        rows.sort(key=lambda r: r[2], reverse=not self._sort_asc)
        self._render_rows(rows)

    def _render_rows(self, rows: list[tuple[str, str, int, str]]) -> None:
        table = self.query_one("#memory-table", DataTable)
        table.clear()
        if not rows:
            table.add_row("--", "--", "--", "No keys found.")
            return
        for key, key_type, size, encoding in rows:
            table.add_row(key, key_type, str(size), encoding)
