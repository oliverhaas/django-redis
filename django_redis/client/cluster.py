"""Redis Cluster client for django-redis."""

from typing import Any

from django.core.cache.backends.base import BaseCache
from redis.cluster import RedisCluster

from django_redis.client.default import DefaultClient


class ClusterClient(DefaultClient):
    """
    Client for Redis Cluster.

    Redis Cluster uses server-side sharding across multiple nodes.
    This client handles the connection to a Redis Cluster and delegates
    operations to the appropriate node automatically.

    Important notes:
    - Multi-key operations (mget, delete_many, etc.) require all keys
      to hash to the same slot. Use hash tags like {prefix}key to ensure this.
    - The cluster handles failover automatically.
    """

    _clients: list[RedisCluster | None]  # type: ignore[assignment]

    def __init__(self, server, params: dict[str, Any], backend: BaseCache) -> None:
        super().__init__(server, params, backend)
        # For cluster, we only maintain a single client connection
        self._clients = [None]

    def get_next_client_index(
        self,
        write: bool = True,
        tried: list[int] | None = None,
    ) -> int:
        """
        Always return 0 for cluster client since the cluster
        handles routing internally.
        """
        return 0

    def connect(self, index: int = 0) -> RedisCluster:  # type: ignore[override]
        """
        Connect to the Redis Cluster.
        """
        return self.connection_factory.connect(self._server[0])

    def get_client(  # type: ignore[override]
        self,
        write: bool = True,
        tried: list[int] | None = None,
    ) -> RedisCluster:
        """Get the cluster client."""
        if self._clients[0] is None:
            self._clients[0] = self.connect(0)
        return self._clients[0]  # type: ignore[return-value]

    def get_client_with_index(  # type: ignore[override]
        self,
        write: bool = True,
        tried: list[int] | None = None,
    ) -> tuple[RedisCluster, int]:
        """Get the cluster client with index."""
        if self._clients[0] is None:
            self._clients[0] = self.connect(0)
        return self._clients[0], 0  # type: ignore[return-value]

    def do_close_clients(self) -> None:
        """Close the cluster connection."""
        if self._clients[0] is not None:
            self._clients[0].close()
        self._clients = [None]
