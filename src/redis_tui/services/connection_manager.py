from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from typing import Any
import redis.asyncio as aioredis
from redis.asyncio.cluster import RedisCluster
from redis_tui.models.connection import ConnectionConfig, ConnectionMode


class ConnectionManager:
    def __init__(self):
        self._client: aioredis.Redis | RedisCluster | None = None
        self._config: ConnectionConfig | None = None
        self._ssh_tunnel = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    @property
    def config(self) -> ConnectionConfig | None:
        return self._config

    async def connect(self, config: ConnectionConfig) -> None:
        await self.disconnect()

        self._config = config
        actual_host = config.host
        actual_port = config.port

        # SSH tunnel setup
        if config.ssh_host:
            actual_host, actual_port = await self._setup_ssh_tunnel(config)

        if config.mode == ConnectionMode.CLUSTER:
            self._client = await self._create_cluster_client(config, actual_host, actual_port)
        elif config.mode == ConnectionMode.SENTINEL:
            self._client = await self._create_sentinel_client(config)
        else:
            self._client = await self._create_standalone_client(config, actual_host, actual_port)

    async def _setup_ssh_tunnel(self, config: ConnectionConfig) -> tuple[str, int]:
        try:
            from sshtunnel import SSHTunnelForwarder
            tunnel = SSHTunnelForwarder(
                (config.ssh_host, config.ssh_port),
                ssh_username=config.ssh_username,
                ssh_password=config.ssh_password,
                ssh_pkey=config.ssh_key_file,
                remote_bind_address=(config.host, config.port),
            )
            tunnel.start()
            self._ssh_tunnel = tunnel
            return "127.0.0.1", tunnel.local_bind_port
        except ImportError:
            raise RuntimeError("sshtunnel package is required for SSH connections")

    async def _create_standalone_client(
        self, config: ConnectionConfig, host: str, port: int
    ) -> aioredis.Redis:
        kwargs: dict[str, Any] = {
            "host": host,
            "port": port,
            "db": config.db,
            "decode_responses": True,
            "socket_connect_timeout": 10,
            "socket_timeout": 30,
        }
        if config.password:
            kwargs["password"] = config.password
        if config.username:
            kwargs["username"] = config.username
        if config.ssl:
            kwargs["ssl"] = True
            if config.ssl_ca_cert:
                kwargs["ssl_ca_certs"] = config.ssl_ca_cert
            if config.ssl_certfile:
                kwargs["ssl_certfile"] = config.ssl_certfile
            if config.ssl_keyfile:
                kwargs["ssl_keyfile"] = config.ssl_keyfile

        client = aioredis.Redis(**kwargs)
        await client.ping()
        return client

    async def _create_cluster_client(
        self, config: ConnectionConfig, host: str, port: int
    ) -> RedisCluster:
        kwargs: dict[str, Any] = {
            "host": host,
            "port": port,
            "decode_responses": True,
        }
        if config.password:
            kwargs["password"] = config.password
        if config.username:
            kwargs["username"] = config.username

        client = RedisCluster(**kwargs)
        await client.initialize()
        return client

    async def _create_sentinel_client(self, config: ConnectionConfig) -> aioredis.Redis:
        from redis.asyncio.sentinel import Sentinel
        sentinel_kwargs: dict[str, Any] = {}
        if config.password:
            sentinel_kwargs["password"] = config.password

        nodes = config.sentinel_nodes or [(config.host, config.port)]
        sentinel = Sentinel(nodes, sentinel_kwargs=sentinel_kwargs)
        master = sentinel.master_for(
            config.sentinel_master or "mymaster",
            decode_responses=True,
        )
        await master.ping()
        return master

    async def disconnect(self) -> None:
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None

        if self._ssh_tunnel:
            try:
                self._ssh_tunnel.stop()
            except Exception:
                pass
            self._ssh_tunnel = None

        self._config = None

    async def switch_db(self, db: int) -> None:
        if not self._config:
            return
        new_config = ConnectionConfig(**{**self._config.__dict__, "db": db})
        await self.connect(new_config)

    def get_client(self) -> aioredis.Redis | RedisCluster:
        if not self._client:
            raise RuntimeError("Not connected to Redis")
        return self._client

    @classmethod
    async def test_connection(cls, config: ConnectionConfig) -> tuple[bool, str]:
        """Test a connection config. Returns (success, message)."""
        manager = cls()
        try:
            await manager.connect(config)
            info = await manager.get_client().info("server")
            version = info.get("redis_version", "unknown")
            await manager.disconnect()
            return True, f"Connected! Redis {version}"
        except Exception as e:
            await manager.disconnect()
            return False, str(e)
