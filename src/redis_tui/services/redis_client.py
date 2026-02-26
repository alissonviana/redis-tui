from __future__ import annotations
from typing import Any
import redis.asyncio as aioredis
from redis_tui.models.key_info import KeyInfo, KeyType
from redis_tui.services.connection_manager import ConnectionManager


class RedisClient:
    def __init__(self, manager: ConnectionManager):
        self._manager = manager

    def _client(self) -> aioredis.Redis:
        return self._manager.get_client()

    async def ping(self) -> bool:
        try:
            return await self._client().ping()
        except Exception:
            return False

    async def get_key_info(self, key: str) -> KeyInfo:
        client = self._client()
        type_str = await client.type(key)
        ttl = await client.ttl(key)
        try:
            size = await client.memory_usage(key) or 0
        except Exception:
            size = 0
        try:
            encoding = await client.object_encoding(key) or ""
        except Exception:
            encoding = ""
        return KeyInfo(
            name=key,
            type=KeyType.from_redis(type_str),
            ttl=ttl,
            size=size,
            encoding=encoding,
        )

    async def get_value(self, key: str, key_type: KeyType | None = None) -> Any:
        client = self._client()
        if key_type is None:
            type_str = await client.type(key)
            key_type = KeyType.from_redis(type_str)

        if key_type == KeyType.STRING:
            return await client.get(key)
        elif key_type == KeyType.HASH:
            return await client.hgetall(key)
        elif key_type == KeyType.LIST:
            return await client.lrange(key, 0, -1)
        elif key_type == KeyType.SET:
            return await client.smembers(key)
        elif key_type == KeyType.ZSET:
            return await client.zrange(key, 0, -1, withscores=True)
        elif key_type == KeyType.STREAM:
            return await client.xrange(key, count=100)
        return None

    async def set_string(self, key: str, value: str, ttl: int | None = None) -> None:
        client = self._client()
        if ttl and ttl > 0:
            await client.setex(key, ttl, value)
        else:
            await client.set(key, value)

    async def delete_keys(self, keys: list[str]) -> int:
        return await self._client().delete(*keys)

    async def rename_key(self, old: str, new: str) -> None:
        await self._client().rename(old, new)

    async def set_ttl(self, key: str, seconds: int) -> bool:
        return await self._client().expire(key, seconds)

    async def remove_ttl(self, key: str) -> bool:
        return await self._client().persist(key)

    async def get_ttl(self, key: str) -> int:
        return await self._client().ttl(key)

    async def get_db_size(self) -> int:
        return await self._client().dbsize()

    async def get_all_db_sizes(self) -> dict[int, int]:
        """Get key count for all databases (0-15)."""
        client = self._client()
        result = {}
        for db in range(16):
            try:
                info = await client.info("keyspace")
                db_key = f"db{db}"
                if db_key in info:
                    result[db] = info[db_key].get("keys", 0)
                else:
                    result[db] = 0
            except Exception:
                result[db] = 0
        return result

    async def get_keyspace_info(self) -> dict[int, int]:
        """Returns {db_index: key_count} for databases with keys."""
        client = self._client()
        try:
            info = await client.info("keyspace")
            result = {}
            for key, val in info.items():
                if key.startswith("db"):
                    db_num = int(key[2:])
                    result[db_num] = val.get("keys", 0)
            return result
        except Exception:
            return {}

    async def get_server_info(self) -> dict:
        client = self._client()
        try:
            return await client.info()
        except Exception:
            return {}

    async def execute_raw(self, command: str) -> Any:
        """Execute a raw Redis command string."""
        client = self._client()
        parts = command.strip().split()
        if not parts:
            return None
        cmd = parts[0].upper()
        args = parts[1:]
        return await client.execute_command(cmd, *args)
