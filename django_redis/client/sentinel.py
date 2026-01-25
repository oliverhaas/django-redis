"""Sentinel cache client for Redis-compatible backends.

This module provides cache clients that use Redis Sentinel for automatic
primary/replica discovery and failover.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from django.core.exceptions import ImproperlyConfigured
from redis import Redis
from redis.connection import ConnectionPool
from redis.sentinel import Sentinel, SentinelConnectionPool

from django_redis.client.default import ClientT, KeyValueCacheClient


class KeyValueSentinelCacheClient(KeyValueCacheClient[ClientT]):
    """Generic Sentinel cache backend base class.

    Automatically discovers primary and replica nodes via Sentinel.
    Subclass this for Redis or Valkey Sentinel support.
    """

    # Subclasses must set these to the appropriate sentinel classes
    _sentinel_class: type[Sentinel]
    _sentinel_pool_class: type[ConnectionPool]

    def __init__(self, server: str, params: dict[str, Any]) -> None:
        # Transform URL to add is_master query param for primary/replica
        if isinstance(server, str):
            server = self._transform_sentinel_urls(server)

        super().__init__(server, params)

        # Create sentinel instance
        sentinels = self._options.get("sentinels")
        if not sentinels:
            raise ImproperlyConfigured(
                "sentinels must be provided as a list of (host, port) tuples"
            )

        sentinel_kwargs = self._options.get("sentinel_kwargs", {})
        pool_options = self._get_pool_options()

        self._sentinel = self._sentinel_class(
            sentinels,
            sentinel_kwargs=sentinel_kwargs,
            **pool_options,
        )

    def _transform_sentinel_urls(self, server: str) -> list[str]:
        """Transform a single URL into primary and replica URLs."""
        url = urlparse(server)
        primary_query = parse_qs(url.query, keep_blank_values=True)
        replica_query = dict(primary_query)
        primary_query["is_master"] = ["1"]
        replica_query["is_master"] = ["0"]

        def replace_query(parsed_url, query):
            return urlunparse((*parsed_url[:4], urlencode(query, doseq=True), parsed_url[5]))

        return [replace_query(url, q) for q in (primary_query, replica_query)]

    def _get_connection_pool(self, write: bool) -> ConnectionPool:
        """Get a sentinel-managed connection pool."""
        index = self._get_connection_pool_index(write)
        url = self._servers[index]
        parsed = urlparse(url)

        if url in self._pools:
            return self._pools[url]

        # Parse service name and is_master from URL
        service_name = parsed.hostname
        query_params = parse_qs(parsed.query)
        is_master = True
        if "is_master" in query_params:
            is_master = query_params["is_master"][0] in ("1", "true", "True")

        pool_options = self._get_pool_options()
        pool_options.update(
            service_name=service_name,
            sentinel_manager=self._sentinel,
            is_master=is_master,
        )

        # Create pool (strip is_master from URL for from_url)
        new_query = {k: v for k, v in query_params.items() if k != "is_master"}
        clean_url = urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.params,
             urlencode(new_query, doseq=True), parsed.fragment)
        )

        pool = self._sentinel_pool_class.from_url(clean_url, **pool_options)
        self._pools[url] = pool

        return pool


class RedisSentinelCacheClient(KeyValueSentinelCacheClient[Redis]):
    """Redis Sentinel cache backend.

    Automatically discovers primary and replica nodes via Redis Sentinel.

    Use as: BACKEND = "django_redis.client.RedisSentinelCacheClient"
    """

    _client_class = Redis
    _pool_class = SentinelConnectionPool  # type: ignore[assignment]
    _sentinel_class = Sentinel
    _sentinel_pool_class = SentinelConnectionPool


# Backwards compatibility alias
SentinelCacheClient = RedisSentinelCacheClient


# NOTE: ValkeySentinelCacheClient is not currently provided due to a bug in valkey-py.
# The valkey-py library's SentinelManagedConnection is missing the `_get_from_local_cache`
# method which causes AttributeError when using Sentinel connections.
# See: https://github.com/valkey-io/valkey-py/issues
# Once the upstream bug is fixed, we can re-enable this by uncommenting the code below:
#
# try:
#     from valkey import Valkey
#     from valkey.sentinel import Sentinel as ValkeySentinel
#     from valkey.sentinel import SentinelConnectionPool as ValkeySentinelConnectionPool
#
#     class ValkeySentinelCacheClient(KeyValueSentinelCacheClient[Valkey]):
#         """Valkey Sentinel cache backend."""
#         _client_class = Valkey
#         _pool_class = ValkeySentinelConnectionPool
#         _sentinel_class = ValkeySentinel
#         _sentinel_pool_class = ValkeySentinelConnectionPool
#
# except ImportError:
#     pass

class ValkeySentinelCacheClient(KeyValueCacheClient):  # type: ignore[type-arg]
    """Valkey Sentinel cache backend (currently unavailable due to valkey-py bug)."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "ValkeySentinelCacheClient is currently unavailable due to a bug in valkey-py. "
            "The SentinelManagedConnection class is missing the '_get_from_local_cache' method. "
            "Use RedisSentinelCacheClient with a Valkey server instead (protocol compatible), "
            "or wait for an upstream fix in valkey-py."
        )
