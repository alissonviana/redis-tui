from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import DataTable, Label, Static, TabbedContent, TabPane
from textual.reactive import reactive


class ServerInfoWidget(Vertical):
    """Dashboard showing Redis server information."""

    def __init__(self, info: dict, *args, **kwargs):
        super().__init__(*args, id="server-info-widget", **kwargs)
        self._info = info

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Overview", id="tab-overview"):
                yield self._make_overview()
            with TabPane("Memory", id="tab-memory"):
                yield self._make_memory()
            with TabPane("Stats", id="tab-stats"):
                yield self._make_stats()
            with TabPane("Clients", id="tab-clients"):
                yield self._make_clients()
            with TabPane("Keyspace", id="tab-keyspace"):
                yield self._make_keyspace()
            with TabPane("Slow Log", id="tab-slowlog"):
                yield self._make_slowlog()

    def _fmt(self, key: str, default: str = "N/A") -> str:
        return str(self._info.get(key, default))

    def _make_overview(self) -> DataTable:
        table = DataTable(id="overview-table", cursor_type="none", zebra_stripes=True)
        table.add_columns("Property", "Value")
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
        return table

    def _make_memory(self) -> DataTable:
        table = DataTable(id="memory-table", cursor_type="none", zebra_stripes=True)
        table.add_columns("Property", "Value")

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
        return table

    def _make_stats(self) -> DataTable:
        table = DataTable(id="stats-table", cursor_type="none", zebra_stripes=True)
        table.add_columns("Property", "Value")
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
        return table

    def _make_clients(self) -> DataTable:
        table = DataTable(id="clients-table", cursor_type="none", zebra_stripes=True)
        table.add_columns("Property", "Value")
        rows = [
            ("Connected Clients", self._fmt("connected_clients")),
            ("Blocked Clients", self._fmt("blocked_clients")),
            ("Tracking Clients", self._fmt("tracking_clients")),
            ("Max Clients", self._fmt("maxclients")),
            ("Client Recent Max Input Buffer", self._fmt("client_recent_max_input_buffer")),
        ]
        for row in rows:
            table.add_row(*row)
        return table

    def _make_keyspace(self) -> DataTable:
        table = DataTable(id="keyspace-table", cursor_type="none", zebra_stripes=True)
        table.add_columns("Database", "Keys", "Expires", "Avg TTL")
        # Keyspace info is nested in the full INFO output
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
        return table

    def _make_slowlog(self) -> DataTable:
        table = DataTable(
            id="slowlog-table", cursor_type="row", zebra_stripes=True
        )
        table.add_columns("ID", "Time (ms)", "Command")
        table.add_row("--", "--", "Click 'Refresh' in Server Info tab to load")
        return table

    def update_slowlog(self, entries: list) -> None:
        """Populate the slow log table with entries from SLOWLOG GET.

        Args:
            entries: List of slow log entries as returned by redis-py
                     (each entry is a list/tuple or a dict depending on
                     the decode_responses setting).
        """
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
