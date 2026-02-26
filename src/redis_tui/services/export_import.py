from __future__ import annotations
import json
from pathlib import Path
import redis.asyncio as aioredis


class ExportImport:
    """Service for exporting and importing Redis keys to/from JSON."""

    def __init__(self, client: aioredis.Redis):
        self._client = client

    async def export_keys(self, keys: list[str], filepath: Path) -> int:
        """Export keys to JSON using DUMP/RESTORE serialization.

        Args:
            keys: List of key names to export.
            filepath: Destination JSON file path.

        Returns:
            Number of keys successfully exported.
        """
        data: dict[str, dict] = {}
        for key in keys:
            try:
                dump = await self._client.dump(key)
                ttl = await self._client.ttl(key)
                key_type = await self._client.type(key)
                if dump:
                    data[key] = {
                        "dump": dump.hex(),  # bytes -> hex string for JSON serialisation
                        "ttl": ttl if ttl > 0 else -1,
                        "type": key_type,
                    }
            except Exception:
                continue
        filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return len(data)

    async def import_keys(
        self, filepath: Path, overwrite: bool = False
    ) -> tuple[int, int]:
        """Import keys from a previously exported JSON file.

        Args:
            filepath: Source JSON file path.
            overwrite: When True, existing keys are replaced.

        Returns:
            Tuple of (imported_count, skipped_count).
        """
        data: dict[str, dict] = json.loads(filepath.read_text(encoding="utf-8"))
        imported = 0
        skipped = 0
        for key, meta in data.items():
            try:
                if not overwrite and await self._client.exists(key):
                    skipped += 1
                    continue
                dump_bytes = bytes.fromhex(meta["dump"])
                ttl = meta.get("ttl", -1)
                replace = 1 if overwrite else 0
                # TTL of 0 in RESTORE means no expiry; positive values set expiry in ms
                await self._client.restore(key, 0, dump_bytes, replace=replace)
                if ttl > 0:
                    await self._client.expire(key, ttl)
                imported += 1
            except Exception:
                skipped += 1
        return imported, skipped
