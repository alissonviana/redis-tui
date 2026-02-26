from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import uuid


class ConnectionMode(str, Enum):
    STANDALONE = "standalone"
    CLUSTER = "cluster"
    SENTINEL = "sentinel"


@dataclass
class ConnectionConfig:
    name: str
    host: str = "localhost"
    port: int = 6379
    password: str | None = None
    username: str | None = None  # ACL (Redis 6+)
    db: int = 0
    mode: ConnectionMode = ConnectionMode.STANDALONE
    ssl: bool = False
    ssl_ca_cert: str | None = None
    ssl_certfile: str | None = None
    ssl_keyfile: str | None = None
    readonly: bool = False
    color: str = "#e74c3c"  # Tag visual (hex color)
    # SSH tunnel
    ssh_host: str | None = None
    ssh_port: int = 22
    ssh_username: str | None = None
    ssh_password: str | None = None
    ssh_key_file: str | None = None
    # Sentinel
    sentinel_master: str | None = None
    sentinel_nodes: list[tuple[str, int]] = field(default_factory=list)
    # Cluster
    cluster_nodes: list[tuple[str, int]] = field(default_factory=list)
    # Internal
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "password": self.password,
            "username": self.username,
            "db": self.db,
            "mode": self.mode.value,
            "ssl": self.ssl,
            "ssl_ca_cert": self.ssl_ca_cert,
            "ssl_certfile": self.ssl_certfile,
            "ssl_keyfile": self.ssl_keyfile,
            "readonly": self.readonly,
            "color": self.color,
            "ssh_host": self.ssh_host,
            "ssh_port": self.ssh_port,
            "ssh_username": self.ssh_username,
            "ssh_password": self.ssh_password,
            "ssh_key_file": self.ssh_key_file,
            "sentinel_master": self.sentinel_master,
            "sentinel_nodes": self.sentinel_nodes,
            "cluster_nodes": self.cluster_nodes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ConnectionConfig:
        data = data.copy()
        data["mode"] = ConnectionMode(data.get("mode", "standalone"))
        data["sentinel_nodes"] = [tuple(n) for n in data.get("sentinel_nodes", [])]
        data["cluster_nodes"] = [tuple(n) for n in data.get("cluster_nodes", [])]
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
