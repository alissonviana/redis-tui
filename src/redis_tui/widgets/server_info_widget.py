from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, TabbedContent, TabPane


class ServerInfoWidget(Vertical):
    """Dashboard showing Redis server information."""

    def __init__(self, info: dict, *args, **kwargs):
        super().__init__(*args, id="server-info-widget", **kwargs)
        self._info = info

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Overview", id="sinfo-tab-overview"):
                yield DataTable(id="overview-table", cursor_type="none", zebra_stripes=True)
            with TabPane("Memory", id="sinfo-tab-memory"):
                yield DataTable(id="memory-table", cursor_type="none", zebra_stripes=True)
            with TabPane("Stats", id="sinfo-tab-stats"):
                yield DataTable(id="stats-table", cursor_type="none", zebra_stripes=True)
            with TabPane("Clients", id="sinfo-tab-clients"):
                yield DataTable(id="clients-table", cursor_type="none", zebra_stripes=True)
            with TabPane("Keyspace", id="sinfo-tab-keyspace"):
                yield DataTable(id="keyspace-table", cursor_type="none", zebra_stripes=True)
            with TabPane("Slow Log", id="sinfo-tab-slowlog"):
                yield DataTable(id="slowlog-table", cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        self._setup_columns()
        self._populate_all()

    def _setup_columns(self) -> None:
        self.query_one("#overview-table", DataTable).add_columns("Property", "Value")
        self.query_one("#memory-table", DataTable).add_columns("Property", "Value")
        self.query_one("#stats-table", DataTable).add_columns("Property", "Value")
        self.query_one("#clients-table", DataTable).add_columns("Property", "Value")
        self.query_one("#keyspace-table", DataTable).add_columns("Database", "Keys", "Expires", "Avg TTL")
        self.query_one("#slowlog-table", DataTable).add_columns("ID", "Time (ms)", "Command")

    def _fmt(self, key: str, default: str = "N/A") -> str:
        return str(self._info.get(key, default))

    def _populate_all(self) -> None:
        self._populate_overview()
        self._populate_memory()
        self._populate_stats()
        self._populate_clients()
        self._populate_keyspace()
        self._populate_slowlog_placeholder()

    def _populate_overview(self) -> None:
        table = self.query_one("#overview-table", DataTable)
        table.clear()
        rows = [
            ("Redis Version", self._fmt("redis_version")),
            ("Mode", self._fmt("redis_mode")),
            ("OS", self._fmt("os")),
            ("Arch", self._fmt("arch_bits") + "-bit"),
            ("Uptime (days)", self._fmt("uptime_in_days")),
            ("TCP Port", self._fmt("tcp_port")),
            ("Executable", self._fmt("executable")),
            ("Config File", self._fmt("config_file")),
        ]
        for row in rows:
            table.add_row(*row)

    def _populate_memory(self) -> None:
        table = self.query_one("#memory-table", DataTable)
        table.clear()

        def fmt_bytes(key: str) -> str:
            val = self._info.get(key, 0)
            if isinstance(val, int):
                mb = val / 1024 / 1024
                return f"{mb:.2f} MB ({val:,} bytes)"
            return str(val)

        rows = [
            ("Used Memory", fmt_bytes("used_memory")),
            ("Used Memory RSS", fmt_bytes("used_memory_rss")),
            ("Used Memory Peak", fmt_bytes("used_memory_peak")),
            ("Used Memory Lua", fmt_bytes("used_memory_lua")),
            ("Mem Fragmentation Ratio", self._fmt("mem_fragmentation_ratio")),
            ("Mem Allocator", self._fmt("mem_allocator")),
        ]
        for row in rows:
            table.add_row(*row)

    def _populate_stats(self) -> None:
        table = self.query_one("#stats-table", DataTable)
        table.clear()
        rows = [
            ("Total Commands Processed", self._fmt("total_commands_processed")),
            ("Instantaneous Ops/sec", self._fmt("instantaneous_ops_per_sec")),
            ("Total Connections Received", self._fmt("total_connections_received")),
            ("Rejected Connections", self._fmt("rejected_connections")),
            ("Expired Keys", self._fmt("expired_keys")),
            ("Evicted Keys", self._fmt("evicted_keys")),
            ("Keyspace Hits", self._fmt("keyspace_hits")),
            ("Keyspace Misses", self._fmt("keyspace_misses")),
        ]
        for row in rows:
            table.add_row(*row)

    def _populate_clients(self) -> None:
        table = self.query_one("#clients-table", DataTable)
        table.clear()
        rows = [
            ("Connected Clients", self._fmt("connected_clients")),
            ("Blocked Clients", self._fmt("blocked_clients")),
            ("Tracking Clients", self._fmt("tracking_clients")),
            ("Max Clients", self._fmt("maxclients")),
            ("Client Recent Max Input Buffer", self._fmt("client_recent_max_input_buffer")),
        ]
        for row in rows:
            table.add_row(*row)

    def _populate_keyspace(self) -> None:
        table = self.query_one("#keyspace-table", DataTable)
        table.clear()
        for key, val in self._info.items():
            if key.startswith("db") and isinstance(val, dict):
                table.add_row(
                    key,
                    str(val.get("keys", 0)),
                    str(val.get("expires", 0)),
                    str(val.get("avg_ttl", 0)),
                )
        if table.row_count == 0:
            table.add_row("(no databases)", "", "", "")

    def _populate_slowlog_placeholder(self) -> None:
        table = self.query_one("#slowlog-table", DataTable)
        table.clear()
        table.add_row("--", "--", "Loading...")

    def update_info(self, info: dict) -> None:
        """Update all tables with new server info data."""
        self._info = info
        self._populate_all()

    def update_slowlog(self, entries: list) -> None:
        """Populate the slow log table with entries from SLOWLOG GET."""
        table = self.query_one("#slowlog-table", DataTable)
        table.clear()
        for entry in entries:
            if isinstance(entry, (list, tuple)):
                entry_id = str(entry[0]) if len(entry) > 0 else ""
                duration = str(entry[1]) if len(entry) > 1 else ""
                cmd_parts = entry[2] if len(entry) > 2 else []
                cmd = " ".join(
                    p.decode("utf-8", errors="replace") if isinstance(p, bytes) else str(p)
                    for p in cmd_parts
                )
            else:
                entry_id = str(entry.get("id", ""))
                duration = str(entry.get("duration", ""))
                cmd_parts = entry.get("command", [])
                cmd = " ".join(
                    p.decode("utf-8", errors="replace") if isinstance(p, bytes) else str(p)
                    for p in cmd_parts
                )
            table.add_row(entry_id, duration, cmd)
        if not entries:
            table.add_row("--", "--", "(no slow log entries)")
