from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class KeyType(str, Enum):
    STRING = "string"
    HASH = "hash"
    LIST = "list"
    SET = "set"
    ZSET = "zset"
    STREAM = "stream"
    UNKNOWN = "unknown"

    @classmethod
    def from_redis(cls, value: str) -> KeyType:
        try:
            return cls(value.lower())
        except ValueError:
            return cls.UNKNOWN

    def icon(self) -> str:
        icons = {
            KeyType.STRING: "S",
            KeyType.HASH: "#",
            KeyType.LIST: "L",
            KeyType.SET: "S",
            KeyType.ZSET: "Z",
            KeyType.STREAM: "~",
            KeyType.UNKNOWN: "?",
        }
        return icons.get(self, "?")

    def color(self) -> str:
        colors = {
            KeyType.STRING: "green",
            KeyType.HASH: "yellow",
            KeyType.LIST: "cyan",
            KeyType.SET: "magenta",
            KeyType.ZSET: "blue",
            KeyType.STREAM: "red",
            KeyType.UNKNOWN: "white",
        }
        return colors.get(self, "white")


@dataclass
class KeyInfo:
    name: str
    type: KeyType = KeyType.UNKNOWN
    ttl: int = -1  # -1 = no TTL, -2 = key doesn't exist
    size: int = 0  # bytes
    encoding: str = ""

    def ttl_display(self) -> str:
        if self.ttl == -1:
            return "No expiry"
        if self.ttl == -2:
            return "Expired"
        if self.ttl < 0:
            return "No expiry"
        hours, remainder = divmod(self.ttl, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


@dataclass
class TreeNodeData:
    """Data associated with a tree node."""
    is_leaf: bool = False
    key_name: str = ""  # Full key name (only for leaf nodes)
    prefix: str = ""    # Namespace prefix (for folder nodes)
    key_info: KeyInfo | None = None
