from __future__ import annotations
from dataclasses import dataclass, field


def _migrate_theme(value: str) -> str:
    """Map legacy 'dark'/'light' values to Textual theme names."""
    if value == "dark":
        return "textual-dark"
    if value == "light":
        return "textual-light"
    return value


@dataclass
class AppSettings:
    key_separator: str = ":"
    scan_count: int = 100
    auto_refresh_interval: int = 0  # 0 = disabled, seconds
    theme: str = "textual-dark"
    max_keys_display: int = 10000

    def to_dict(self) -> dict:
        return {
            "key_separator": self.key_separator,
            "scan_count": self.scan_count,
            "auto_refresh_interval": self.auto_refresh_interval,
            "theme": self.theme,
            "max_keys_display": self.max_keys_display,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AppSettings:
        return cls(
            key_separator=data.get("key_separator", ":"),
            scan_count=int(data.get("scan_count", 100)),
            auto_refresh_interval=int(data.get("auto_refresh_interval", 0)),
            theme=_migrate_theme(data.get("theme", "textual-dark")),
            max_keys_display=int(data.get("max_keys_display", 10000)),
        )
