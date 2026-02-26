from __future__ import annotations
from typing import AsyncGenerator
import redis.asyncio as aioredis
from redis_tui.constants import DEFAULT_SCAN_COUNT


class KeyScanner:
    def __init__(self, client: aioredis.Redis):
        self._client = client

    async def scan_all(
        self,
        pattern: str = "*",
        count: int = DEFAULT_SCAN_COUNT,
        type_filter: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Async generator that yields keys using SCAN cursor."""
        kwargs = {"match": pattern, "count": count}
        if type_filter:
            kwargs["_type"] = type_filter

        async for key in self._client.scan_iter(**kwargs):
            yield key

    async def scan_prefix(
        self,
        prefix: str,
        separator: str = ":",
        count: int = DEFAULT_SCAN_COUNT,
    ) -> AsyncGenerator[str, None]:
        """Scan keys matching a specific prefix."""
        pattern = f"{prefix}{separator}*" if prefix else "*"
        async for key in self.scan_all(pattern=pattern, count=count):
            yield key

    async def count_keys(self, pattern: str = "*") -> int:
        """Count keys matching a pattern (uses SCAN)."""
        count = 0
        async for _ in self.scan_all(pattern=pattern):
            count += 1
        return count
