"""Cluster cache client for Redis-compatible backends.

This module provides cache clients for Redis Cluster mode, handling
server-side sharding and slot-aware operations.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable, Iterator, Mapping
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, cast

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from redis.typing import KeyT

from django_redis.client.default import (
    KeyValueCacheClient,
    _DEFAULT_TIMEOUT,
    _KNOWN_OPTIONS,
)
from django_redis.exceptions import ConnectionInterrupted
from django_redis.omit_exception import omit_exception

if TYPE_CHECKING:
    from redis.cluster import RedisCluster

    from django_redis.client.pipeline import Pipeline

# Type variable for Cluster class (RedisCluster or ValkeyCluster)
ClusterT = TypeVar("ClusterT")


class KeyValueClusterCacheClient(KeyValueCacheClient[ClusterT], Generic[ClusterT]):
    """Generic Cluster cache backend base class.

    Handles server-side sharding and slot-aware operations.
    Subclass this for Redis or Valkey Cluster support.
    """

    # Cluster-level cache (cluster manages its own connection pool)
    _clusters: ClassVar[dict[str, ClusterT]] = {}  # type: ignore[misc]

    # Subclasses must set these
    _cluster_class: type[ClusterT]
    _key_slot_func: Any  # Function to calculate key slot

    def __init__(self, server: str, params: dict[str, Any]) -> None:
        super().__init__(server, params)

    def get_client(self, key: KeyT | None = None, *, write: bool = False) -> ClusterT:
        """Get the Cluster client."""
        url = self._servers[0]
        if url in self._clusters:
            return self._clusters[url]

        parsed_url = __import__("urllib.parse", fromlist=["urlparse"]).urlparse(url)
        cluster_options = {}

        # Pass through options
        for key_opt, value in self._options.items():
            if key_opt not in _KNOWN_OPTIONS:
                cluster_options[key_opt] = value

        if parsed_url.hostname:
            cluster_options["host"] = parsed_url.hostname
        if parsed_url.port:
            cluster_options["port"] = parsed_url.port

        cluster = self._cluster_class(**cluster_options)
        self._clusters[url] = cluster
        return cluster

    def _group_keys_by_slot(self, keys: Iterable[KeyT]) -> dict[int, list[KeyT]]:
        """Group keys by their cluster slot."""
        from collections import defaultdict

        slots: dict[int, list[KeyT]] = defaultdict(list)
        for key in keys:
            key_bytes = key.encode() if isinstance(key, str) else key
            slot = self._key_slot_func(key_bytes)
            slots[slot].append(key)
        return dict(slots)

    @omit_exception(return_value={})
    def get_many(
        self,
        keys: list[str],
        version: int | None = None,
    ) -> dict[str, Any]:
        """Retrieve many keys, handling cross-slot keys."""
        if not keys:
            return {}

        client = self.get_client(write=False)

        # Create mapping of made_key -> original_key
        map_keys = OrderedDict((self.make_key(k, version=version), k) for k in keys)

        try:
            # mget_nonatomic handles slot splitting
            results = cast(
                "list[bytes | None]",
                client.mget_nonatomic(list(map_keys.keys())),
            )

            recovered_data = {}
            for (_, original_key), value in zip(map_keys.items(), results, strict=True):
                if value is not None:
                    recovered_data[original_key] = self.decode(value)

        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

        return recovered_data

    @omit_exception
    def set_many(
        self,
        data: Mapping[str, Any],
        timeout: float | None = _DEFAULT_TIMEOUT,
        version: int | None = None,
    ) -> list[str]:
        """Set multiple values, handling cross-slot keys."""
        client = self.get_client(write=True)

        if not data:
            return []

        if timeout is DEFAULT_TIMEOUT:
            timeout = self.default_timeout

        # Prepare data with made keys and encoded values
        prepared_data = {
            self.make_key(k, version=version): self.encode(v)
            for k, v in data.items()
        }

        try:
            # mset_nonatomic handles slot splitting
            client.mset_nonatomic(prepared_data)

            # Set expiry if needed
            if timeout is not None:
                timeout_ms = int(timeout * 1000)
                if timeout_ms > 0:
                    pipe = client.pipeline()
                    for key in prepared_data:
                        pipe.pexpire(key, timeout_ms)
                    pipe.execute()
        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

        return []

    @omit_exception
    def delete_many(self, keys: list[str], version: int | None = None) -> int:
        """Remove multiple keys, grouping by slot."""
        if not keys:
            return 0

        client = self.get_client(write=True)
        made_keys = [self.make_key(k, version=version) for k in keys]

        # Group keys by slot
        slots = self._group_keys_by_slot(made_keys)

        try:
            total_deleted = 0
            for slot_keys in slots.values():
                total_deleted += cast("int", client.delete(*slot_keys))
            return total_deleted
        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def clear(self) -> bool:
        """Flush all primary nodes in the cluster."""
        client = self.get_client(write=True)

        try:
            # Use PRIMARIES constant from the cluster class
            client.flushdb(target_nodes=self._cluster_class.PRIMARIES)  # type: ignore[attr-defined]
        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

        return True

    @omit_exception
    def keys(
        self,
        pattern: str = "*",
        version: int | None = None,
    ) -> list[str]:
        """Execute KEYS command across all primary nodes."""
        client = self.get_client(write=False)
        npattern = self.make_pattern(pattern, version=version)

        try:
            keys_result = cast(
                "list[bytes]",
                client.keys(npattern, target_nodes=self._cluster_class.PRIMARIES),  # type: ignore[attr-defined]
            )
            return [self.reverse_key(k.decode()) for k in keys_result]
        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def iter_keys(
        self,
        pattern: str = "*",
        version: int | None = None,
        itersize: int | None = None,
    ) -> Iterator[str]:
        """Iterate keys matching pattern across all primary nodes."""
        client = self.get_client(write=False)
        npattern = self.make_pattern(pattern, version=version)

        if itersize is None:
            itersize = self._default_scan_itersize

        for item in client.scan_iter(
            match=npattern,
            count=itersize,
            target_nodes=self._cluster_class.PRIMARIES,  # type: ignore[attr-defined]
        ):
            yield self.reverse_key(item.decode())

    @omit_exception
    def delete_pattern(
        self,
        pattern: str,
        version: int | None = None,
        itersize: int | None = None,
    ) -> int:
        """Remove all keys matching pattern across all primary nodes."""
        client = self.get_client(write=True)
        npattern = self.make_pattern(pattern, version=version)

        if itersize is None:
            itersize = self._default_scan_itersize

        try:
            # Collect all matching keys from all primaries
            keys_list = list(
                client.scan_iter(
                    match=npattern,
                    count=itersize,
                    target_nodes=self._cluster_class.PRIMARIES,  # type: ignore[attr-defined]
                ),
            )

            if not keys_list:
                return 0

            # Group keys by slot for efficient deletion
            slots = self._group_keys_by_slot(keys_list)

            total_deleted = 0
            for slot_keys in slots.values():
                total_deleted += cast("int", client.delete(*slot_keys))
        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

        return total_deleted

    def close(self, **kwargs: Any) -> None:
        """Close the cluster connection if configured to do so."""
        close_flag = self._options.get(
            "close_connection",
            getattr(settings, "DJANGO_REDIS_CLOSE_CONNECTION", False),
        )
        if close_flag:
            url = self._servers[0]
            if url in self._clusters:
                self._clusters[url].close()  # type: ignore[attr-defined]
                del self._clusters[url]

    def pipeline(
        self,
        transaction: bool = True,
        version: int | None = None,
    ) -> "Pipeline":
        """Create a pipeline for batched operations.

        Note: Cluster mode doesn't support transactions, so transaction
        parameter is ignored and always set to False.
        """
        from django_redis.client.pipeline import Pipeline

        client = self.get_client(write=True)
        # Cluster doesn't support transactions
        raw_pipeline = client.pipeline(transaction=False)
        return Pipeline(client=self, pipeline=raw_pipeline, version=version)


class RedisClusterCacheClient(KeyValueClusterCacheClient["RedisCluster"]):
    """Redis Cluster cache backend.

    Handles server-side sharding and slot-aware operations.

    Use as: BACKEND = "django_redis.client.RedisClusterCacheClient"
    """

    # Import at module level for class attribute access
    from redis.cluster import RedisCluster as _cluster_class
    from redis.cluster import key_slot
    _key_slot_func = staticmethod(key_slot)


# Backwards compatibility alias
ClusterCacheClient = RedisClusterCacheClient


# Try to import Valkey Cluster
try:
    from valkey.cluster import ValkeyCluster
    from valkey.cluster import key_slot as valkey_key_slot

    class ValkeyClusterCacheClient(KeyValueClusterCacheClient[ValkeyCluster]):
        """Valkey Cluster cache backend.

        Handles server-side sharding and slot-aware operations.

        Use as: BACKEND = "django_redis.client.ValkeyClusterCacheClient"
        """

        # Import at module level for class attribute access
        _cluster_class = ValkeyCluster
        _key_slot_func = staticmethod(valkey_key_slot)

except ImportError:
    class ValkeyClusterCacheClient(KeyValueCacheClient):  # type: ignore[no-redef,type-arg]
        """Valkey Cluster cache backend (requires valkey-py with cluster support)."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "ValkeyClusterCacheClient requires valkey-py with cluster support. "
                "Install it with: pip install valkey"
            )
