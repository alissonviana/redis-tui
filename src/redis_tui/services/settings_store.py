from __future__ import annotations
import json
import os
from pathlib import Path
from redis_tui.models.settings import AppSettings


SETTINGS_FILE = "settings.json"
CONFIG_DIR = "~/.redis-tui"


class SettingsStore:
    def __init__(self):
        self.config_dir = Path(os.path.expanduser(CONFIG_DIR))
        self.settings_file = self.config_dir / SETTINGS_FILE
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppSettings:
        if not self.settings_file.exists():
            return AppSettings()
        try:
            data = json.loads(self.settings_file.read_text(encoding="utf-8"))
            return AppSettings.from_dict(data)
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self.settings_file.write_text(
            json.dumps(settings.to_dict(), indent=2), encoding="utf-8"
        )
