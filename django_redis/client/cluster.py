"""Redis Cluster client for django-redis."""

from collections import OrderedDict, defaultdict
from collections.abc import Iterable, Iterator
from typing import Any, cast

from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from redis.cluster import RedisCluster, key_slot
from redis.typing import EncodableT, KeyT

from django_redis.client.default import DefaultClient
from django_redis.exceptions import ConnectionInterrupted


class ClusterClient(DefaultClient):
    """
    Client for Redis Cluster.

    Redis Cluster uses server-side sharding across multiple nodes.
    This client handles the connection to a Redis Cluster and delegates
    operations to the appropriate node automatically.

    This client overrides multi-key operations to handle keys across
    different slots by grouping them appropriately.
    """

    _clients: list[RedisCluster | None]

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

    def _group_keys_by_slot(
        self,
        keys: Iterable[KeyT],
    ) -> dict[int, list[KeyT]]:
        """Group keys by their cluster slot."""
        slots: dict[int, list[KeyT]] = defaultdict(list)
        for key in keys:
            # Encode key to bytes for slot calculation
            key_bytes = key.encode() if isinstance(key, str) else key
            slot = key_slot(key_bytes)
            slots[slot].append(key)
        return dict(slots)

    def get_many(
        self,
        keys: Iterable[KeyT],
        version: int | None = None,
        client: RedisCluster | None = None,  # type: ignore[override]
    ) -> OrderedDict:
        """
        Retrieve many keys, handling cross-slot keys by grouping.

        Unlike standalone Redis, cluster mode requires keys to be on the
        same slot for MGET. This method groups keys by slot and performs
        multiple MGET operations as needed.
        """
        if client is None:
            client = self.get_client(write=False)

        keys_list = list(keys)
        if not keys_list:
            return OrderedDict()

        recovered_data = OrderedDict()

        # Create mapping of made_key -> original_key
        map_keys = OrderedDict((self.make_key(k, version=version), k) for k in keys_list)

        # Group keys by slot
        slots = self._group_keys_by_slot(map_keys.keys())

        try:
            # Execute MGET for each slot group
            all_results: dict[KeyT, Any] = {}
            for slot_keys in slots.values():
                if len(slot_keys) == 1:
                    # Single key - use GET
                    value = cast("bytes | None", client.get(slot_keys[0]))
                    all_results[slot_keys[0]] = value
                else:
                    # Multiple keys in same slot - use MGET
                    results = cast("list[bytes | None]", client.mget(*slot_keys))
                    for key, value in zip(slot_keys, results, strict=False):
                        all_results[key] = value

            # Build result in original order
            for made_key, original_key in map_keys.items():
                value = all_results.get(made_key)
                if value is not None:
                    recovered_data[original_key] = self.decode(value)

        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

        return recovered_data

    def delete_many(
        self,
        keys: Iterable[KeyT],
        version: int | None = None,
        client: RedisCluster | None = None,  # type: ignore[override]
    ) -> int:
        """
        Remove multiple keys, handling cross-slot keys by grouping.

        Unlike standalone Redis, cluster mode requires keys to be on the
        same slot for multi-key DEL. This method groups keys by slot and
        performs multiple DEL operations as needed.
        """
        if client is None:
            client = self.get_client(write=True)

        made_keys = [self.make_key(k, version=version) for k in keys]

        if not made_keys:
            return 0

        # Group keys by slot
        slots = self._group_keys_by_slot(made_keys)

        try:
            total_deleted = 0
            for slot_keys in slots.values():
                total_deleted += cast("int", client.delete(*slot_keys))
            return total_deleted
        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

    def set_many(
        self,
        data: dict[KeyT, EncodableT],
        timeout: float | None = DEFAULT_TIMEOUT,
        version: int | None = None,
        client: RedisCluster | None = None,  # type: ignore[override]
    ) -> None:
        """
        Set multiple values, handling cross-slot keys.

        Uses individual SET commands since MSET requires same-slot keys.
        """
        if client is None:
            client = self.get_client(write=True)

        try:
            # Use individual set operations - cluster handles routing
            for key, value in data.items():
                self.set(key, value, timeout, version=version, client=client)
        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

    def clear(self, client: RedisCluster | None = None) -> None:  # type: ignore[override]
        """
        Flush cache keys on all cluster nodes.

        In cluster mode, FLUSHDB only affects the connected node.
        This method flushes all primary nodes in the cluster.
        """
        if client is None:
            client = self.get_client(write=True)

        try:
            # RedisCluster.flushdb() with target_nodes=ALL_PRIMARIES
            # flushes all primary nodes
            client.flushdb(target_nodes=RedisCluster.PRIMARIES)
        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

    def keys(
        self,
        search: str,
        version: int | None = None,
        client: RedisCluster | None = None,  # type: ignore[override]
    ) -> list[Any]:
        """
        Execute KEYS command across all primary nodes.

        In cluster mode, KEYS only operates on the connected node.
        This method queries all primary nodes in the cluster.
        """
        if client is None:
            client = self.get_client(write=False)

        pattern = self.make_pattern(search, version=version)
        try:
            keys_result = cast("list[bytes]", client.keys(pattern, target_nodes=RedisCluster.PRIMARIES))
            return [self.reverse_key(k.decode()) for k in keys_result]
        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

    def iter_keys(
        self,
        search: str,
        itersize: int | None = None,
        client: RedisCluster | None = None,  # type: ignore[override]
        version: int | None = None,
    ) -> Iterator[str]:
        """
        Iterate keys matching pattern across all primary nodes.

        In cluster mode, SCAN only operates on the connected node.
        This method scans all primary nodes in the cluster.
        """
        if client is None:
            client = self.get_client(write=False)

        pattern = self.make_pattern(search, version=version)
        for item in client.scan_iter(
            match=pattern,
            count=itersize,
            target_nodes=RedisCluster.PRIMARIES,
        ):
            yield self.reverse_key(item.decode())

    def delete_pattern(
        self,
        pattern: str,
        version: int | None = None,
        prefix: str | None = None,
        client: RedisCluster | None = None,  # type: ignore[override]
        itersize: int | None = None,
    ) -> int:
        """
        Remove all keys matching pattern across all primary nodes.

        In cluster mode, SCAN only operates on the connected node.
        This method scans all primary nodes and groups deletions by slot.
        """
        if client is None:
            client = self.get_client(write=True)

        pattern = self.make_pattern(pattern, version=version, prefix=prefix)

        try:
            # Collect all matching keys from all primaries
            keys = list(
                client.scan_iter(
                    match=pattern,
                    count=itersize,
                    target_nodes=RedisCluster.PRIMARIES,
                ),
            )

            if not keys:
                return 0

            # Group keys by slot for efficient deletion
            slots = self._group_keys_by_slot(keys)

            total_deleted = 0
            for slot_keys in slots.values():
                total_deleted += cast("int", client.delete(*slot_keys))

            return total_deleted
        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e
