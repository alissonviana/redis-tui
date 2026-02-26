from __future__ import annotations
import json
import os
from pathlib import Path
from redis_tui.models.connection import ConnectionConfig
from redis_tui.constants import CONFIG_DIR, CONFIG_FILE


class ConfigStore:
    def __init__(self):
        self.config_dir = Path(os.path.expanduser(CONFIG_DIR))
        self.config_file = self.config_dir / CONFIG_FILE
        self._ensure_dir()

    def _ensure_dir(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_connections(self) -> list[ConnectionConfig]:
        if not self.config_file.exists():
            return []
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [ConnectionConfig.from_dict(d) for d in data.get("connections", [])]
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    def save_connections(self, connections: list[ConnectionConfig]) -> None:
        data = {"connections": [c.to_dict() for c in connections]}
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add_connection(self, config: ConnectionConfig) -> None:
        connections = self.load_connections()
        # Remove existing with same id
        connections = [c for c in connections if c.id != config.id]
        connections.append(config)
        self.save_connections(connections)

    def remove_connection(self, connection_id: str) -> None:
        connections = self.load_connections()
        connections = [c for c in connections if c.id != connection_id]
        self.save_connections(connections)

    def update_connection(self, config: ConnectionConfig) -> None:
        connections = self.load_connections()
        connections = [config if c.id == config.id else c for c in connections]
        self.save_connections(connections)
