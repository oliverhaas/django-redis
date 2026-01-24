"""Unified cache client for Redis-compatible backends.

This module provides a single class hierarchy that extends Django's BaseCache
and implements all Redis operations directly - no delegation layer.
"""

from __future__ import annotations

import logging
import random
import re
import socket
from collections import OrderedDict
from collections.abc import Iterable, Iterator, Mapping
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, cast
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from redis import Redis
from redis.connection import ConnectionPool, DefaultParser
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError
from redis.exceptions import TimeoutError as RedisTimeoutError
from redis.sentinel import Sentinel, SentinelConnectionPool
from redis.typing import AbsExpiryT, EncodableT, ExpiryT, KeyT

from django_redis.client.mixins import HashMixin, ListMixin, SetMixin, SortedSetMixin
from django_redis.compat import create_compressor, create_serializer
from django_redis.exceptions import CompressorError, ConnectionInterrupted, SerializerError
from django_redis.omit_exception import omit_exception
from django_redis.util import CacheKey

if TYPE_CHECKING:
    from redis.cluster import RedisCluster

# Type alias matching Django's cache interface
_DEFAULT_TIMEOUT: Any = DEFAULT_TIMEOUT  # Sentinel type

# Main exceptions to catch for connection issues
_main_exceptions = (
    RedisConnectionError,
    RedisTimeoutError,
    ResponseError,
    socket.timeout,
)

# Regex for escaping glob special characters
special_re = re.compile("([*?[])")


def glob_escape(s: str) -> str:
    return special_re.sub(r"[\1]", s)


# Known options that we handle explicitly (not passed to pool)
_KNOWN_OPTIONS = frozenset({
    "serializer",
    "compressor",
    "connection_factory",
    "sentinels",
    "sentinel_kwargs",
    "ignore_exceptions",
    "close_connection",
    "reverse_key_function",
    "pool_class",
    "parser_class",
    "redis_client_class",
    "db",
    # Legacy option - ignored in new architecture, use separate BACKEND classes instead
    "client_class",
})

# Type variable for Redis client types
ClientT = TypeVar("ClientT", bound=Redis)


class KeyValueCacheClient(
    BaseCache,
    HashMixin[ClientT],
    ListMixin[ClientT],
    SetMixin[ClientT],
    SortedSetMixin[ClientT],
    Generic[ClientT],
):
    """Unified cache backend and client.

    Extends Django's BaseCache and implements all Redis operations directly.
    No delegation layer - this class IS both the backend and the client.
    """

    # Class-level attributes that subclasses can override
    _client_class: type[ClientT] = Redis  # type: ignore[assignment]
    _pool_class: type[ConnectionPool] = ConnectionPool

    # Process-global pool cache (Django creates new cache instances per request)
    _pools: ClassVar[dict[str, ConnectionPool]] = {}

    def __init__(self, server: str, params: dict[str, Any]) -> None:
        super().__init__(params)

        # Parse server(s)
        if isinstance(server, str):
            self._servers = re.split("[;,]", server)
        else:
            self._servers = list(server)

        if not self._servers:
            raise ImproperlyConfigured("Missing cache server connection string")

        self._params = params
        self._options = params.get("OPTIONS", {})

        # Exception handling
        self._ignore_exceptions = self._options.get(
            "ignore_exceptions",
            getattr(settings, "DJANGO_REDIS_IGNORE_EXCEPTIONS", False),
        )
        self._log_ignored_exceptions = getattr(
            settings,
            "DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS",
            False,
        )
        self.logger = (
            logging.getLogger(getattr(settings, "DJANGO_REDIS_LOGGER", __name__))
            if self._log_ignored_exceptions
            else None
        )

        # Pool class - accept class or string path
        pool_class = self._options.get("pool_class")
        if pool_class is not None:
            if isinstance(pool_class, str):
                pool_class = import_string(pool_class)
            self._pool_class = pool_class

        # Parser class - accept class or string path
        parser_class = self._options.get("parser_class", DefaultParser)
        if isinstance(parser_class, str):
            parser_class = import_string(parser_class)
        self._parser_class = parser_class

        # Redis client class - can be overridden
        redis_client_class = self._options.get("redis_client_class")
        if redis_client_class is not None:
            if isinstance(redis_client_class, str):
                redis_client_class = import_string(redis_client_class)
            self._client_class = redis_client_class

        # Reverse key function
        reverse_key_func = self._options.get("reverse_key_function") or "django_redis.util.default_reverse_key"
        if isinstance(reverse_key_func, str):
            reverse_key_func = import_string(reverse_key_func)
        self._reverse_key = reverse_key_func

        # Setup serializers
        serializer_config = self._options.get(
            "serializer",
            "django_redis.serializers.pickle.PickleSerializer",
        )
        self._serializers = self._create_serializers(serializer_config)

        # Setup compressors
        compressor_config = self._options.get("compressor")
        self._compressors = self._create_compressors(compressor_config)

        # Default scan itersize
        self._default_scan_itersize = getattr(
            settings,
            "DJANGO_REDIS_SCAN_ITERSIZE",
            10,
        )

    def _create_serializers(self, config: str | list | type | Any) -> list:
        """Create serializer instance(s) from config."""
        if isinstance(config, list):
            return [create_serializer(item, self._options) for item in config]
        return [create_serializer(config, self._options)]

    def _create_compressors(self, config: str | list | type | Any | None) -> list:
        """Create compressor instance(s) from config."""
        if config is None:
            return [create_compressor("django_redis.compressors.identity.IdentityCompressor")]
        if isinstance(config, list):
            return [create_compressor(item, self._options) for item in config]
        return [create_compressor(config, self._options)]

    def _has_compression_enabled(self) -> bool:
        """Check if compression is enabled (first compressor is not identity)."""
        if not self._compressors:
            return False
        first_compressor = self._compressors[0]
        return first_compressor.__class__.__name__ != "IdentityCompressor"

    # =========================================================================
    # Connection Management
    # =========================================================================

    def _get_pool_options(self) -> dict:
        """Get options to pass directly to ConnectionPool.from_url()."""
        pool_options = {"parser_class": self._parser_class}

        # Pass through any option that's not in our known set
        for key, value in self._options.items():
            if key not in _KNOWN_OPTIONS:
                pool_options[key] = value

        return pool_options

    def _get_connection_pool_index(self, write: bool) -> int:
        """Return index for read/write operations.

        Write to first server, read from replicas if available.
        """
        if write or len(self._servers) == 1:
            return 0
        return random.randint(1, len(self._servers) - 1)

    def _get_connection_pool(self, write: bool) -> ConnectionPool:
        """Get or create a connection pool for the given operation type."""
        index = self._get_connection_pool_index(write)
        url = self._servers[index]

        # Handle db option by appending to URL if not already specified
        db = self._options.get("db")
        if db is not None:
            parsed = urlparse(url)
            if not parsed.path or parsed.path == "/":
                url = f"{url.rstrip('/')}/{db}"

        if url not in self._pools:
            pool_options = self._get_pool_options()
            self._pools[url] = self._pool_class.from_url(url, **pool_options)

        return self._pools[url]

    def get_client(self, key: KeyT | None = None, *, write: bool = False) -> ClientT:
        """Get raw Redis client.

        Args:
            key: Optional key (for sharding implementations)
            write: If True, get write client; if False, get read client

        Returns:
            Raw Redis client instance
        """
        pool = self._get_connection_pool(write)
        return self._client_class(connection_pool=pool)

    def close(self, **kwargs: Any) -> None:
        """Close connections if configured to do so."""
        close_flag = self._options.get(
            "close_connection",
            getattr(settings, "DJANGO_REDIS_CLOSE_CONNECTION", False),
        )
        if close_flag:
            # Disconnect all pools we've used
            for pool in self._pools.values():
                pool.disconnect()

    # =========================================================================
    # Encoding/Decoding
    # =========================================================================

    def encode(self, value: EncodableT) -> bytes | int:
        """Encode a value for storage."""
        # Store integers raw for atomic incr/decr
        if isinstance(value, bool) or not isinstance(value, int):
            value = self._serializers[0].dumps(value)
            return self._compressors[0].compress(value)
        return value

    def decode(self, value: EncodableT) -> Any:
        """Decode a value from storage."""
        try:
            return int(value)
        except (ValueError, TypeError):
            value = self._decompress(value)
            return self._deserialize(value)

    def _deserialize(self, value: bytes) -> Any:
        """Deserialize with fallback support for multiple serializers."""
        last_error: SerializerError | None = None
        for serializer in self._serializers:
            try:
                return serializer.loads(value)
            except SerializerError as e:
                last_error = e
                continue

        if last_error is not None:
            raise last_error
        msg = "No serializers configured"
        raise SerializerError(msg)

    def _decompress(self, value: bytes) -> bytes:
        """Decompress with fallback support for multiple compressors."""
        for compressor in self._compressors:
            try:
                return compressor.decompress(value)
            except CompressorError:
                continue
        return value

    def _decode_iterable_result(
        self,
        result: Any,
        convert_to_set: bool = True,
    ) -> list[Any] | set[Any] | None | Any:
        """Decode an iterable result from Redis."""
        if result is None:
            return None
        if isinstance(result, list):
            if convert_to_set:
                return {self.decode(value) for value in result}
            return [self.decode(value) for value in result]
        return self.decode(result)

    # =========================================================================
    # Key Management
    # =========================================================================

    def make_key(
        self,
        key: KeyT,
        version: int | None = None,
        prefix: str | None = None,
    ) -> KeyT:
        """Create a cache key with prefix and version."""
        if isinstance(key, CacheKey):
            return key

        if prefix is None:
            prefix = self.key_prefix

        if version is None:
            version = self.version

        return CacheKey(self.key_func(key, prefix, version))

    def make_pattern(
        self,
        pattern: str,
        version: int | None = None,
        prefix: str | None = None,
    ) -> str:
        """Create a key pattern for scanning."""
        if isinstance(pattern, CacheKey):
            return pattern

        if prefix is None:
            prefix = self.key_prefix
        prefix = glob_escape(prefix)

        if version is None:
            version = self.version
        version_str = glob_escape(str(version))

        return CacheKey(self.key_func(pattern, prefix, version_str))

    def reverse_key(self, key: str) -> str:
        """Reverse a cache key to get original key."""
        return self._reverse_key(key)

    # =========================================================================
    # Django BaseCache Interface - Core Methods
    # =========================================================================

    @omit_exception
    def add(
        self,
        key: str,
        value: Any,
        timeout: float | None = _DEFAULT_TIMEOUT,
        version: int | None = None,
    ) -> bool:
        """Add a value only if it doesn't exist."""
        return self.set(key, value, timeout=timeout, version=version, nx=True)

    def get(
        self,
        key: str,
        default: Any | None = None,
        version: int | None = None,
    ) -> Any:
        """Retrieve a value from the cache."""
        value = self._get(key, default, version)
        if value is None:
            return default
        return value

    @omit_exception
    def _get(
        self,
        key: str,
        default: Any | None,
        version: int | None,
    ) -> Any:
        """Internal get implementation."""
        client = self.get_client(key, write=False)
        nkey = self.make_key(key, version=version)

        try:
            value = cast("bytes | None", client.get(nkey))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

        if value is None:
            return default

        return self.decode(value)

    @omit_exception
    def set(
        self,
        key: str,
        value: Any,
        timeout: float | None = _DEFAULT_TIMEOUT,
        version: int | None = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """Set a value in the cache."""
        client = self.get_client(key, write=True)
        nkey = self.make_key(key, version=version)
        nvalue = self.encode(value)

        if timeout is DEFAULT_TIMEOUT:
            timeout = self.default_timeout

        try:
            if timeout is not None:
                # Convert to milliseconds
                timeout_ms = int(timeout * 1000)

                if timeout_ms <= 0:
                    if nx:
                        # Don't expire if nx and value exists
                        return not self.has_key(key, version=version)
                    # Delete key for non-positive timeout
                    return bool(self.delete(key, version=version))

                return bool(cast("bool | None", client.set(nkey, nvalue, nx=nx, px=timeout_ms, xx=xx)))
            else:
                # No timeout - persistent key
                return bool(cast("bool | None", client.set(nkey, nvalue, nx=nx, xx=xx)))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def delete(self, key: str, version: int | None = None) -> bool:
        """Remove a key from the cache."""
        client = self.get_client(key, write=True)
        nkey = self.make_key(key, version=version)

        try:
            return bool(client.delete(nkey))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def touch(
        self,
        key: str,
        timeout: float | None = _DEFAULT_TIMEOUT,
        version: int | None = None,
    ) -> bool:
        """Update the timeout on a key."""
        if timeout is DEFAULT_TIMEOUT:
            timeout = self.default_timeout

        client = self.get_client(key, write=True)
        nkey = self.make_key(key, version=version)

        if timeout is None:
            return cast("bool", client.persist(nkey))

        # Convert to milliseconds
        timeout_ms = int(timeout * 1000)
        return cast("bool", client.pexpire(nkey, timeout_ms))

    @omit_exception
    def has_key(self, key: str, version: int | None = None) -> bool:
        """Test if key exists."""
        client = self.get_client(key, write=False)
        nkey = self.make_key(key, version=version)

        try:
            return cast("int", client.exists(nkey)) == 1
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception(return_value={})
    def get_many(
        self,
        keys: list[str],
        version: int | None = None,
    ) -> dict[str, Any]:
        """Retrieve many keys at once."""
        client = self.get_client(write=False)

        if not keys:
            return {}

        # Build mapping of made_key -> original_key
        map_keys = OrderedDict((self.make_key(k, version=version), k) for k in keys)

        try:
            results = cast("list[bytes | None]", client.mget(*map_keys))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

        recovered_data = {}
        for key, value in zip(map_keys, results, strict=False):
            if value is not None:
                recovered_data[map_keys[key]] = self.decode(value)

        return recovered_data

    @omit_exception
    def set_many(
        self,
        data: Mapping[str, Any],
        timeout: float | None = _DEFAULT_TIMEOUT,
        version: int | None = None,
    ) -> list[str]:
        """Set multiple values at once."""
        client = self.get_client(write=True)

        if not data:
            return []

        try:
            pipeline = client.pipeline()
            for key, value in data.items():
                nkey = self.make_key(key, version=version)
                nvalue = self.encode(value)

                if timeout is DEFAULT_TIMEOUT:
                    timeout = self.default_timeout

                if timeout is not None:
                    timeout_ms = int(timeout * 1000)
                    if timeout_ms > 0:
                        pipeline.set(nkey, nvalue, px=timeout_ms)
                    else:
                        pipeline.delete(nkey)
                else:
                    pipeline.set(nkey, nvalue)

            pipeline.execute()
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

        return []

    @omit_exception
    def delete_many(self, keys: list[str], version: int | None = None) -> int:
        """Remove multiple keys at once."""
        client = self.get_client(write=True)
        nkeys = [self.make_key(k, version=version) for k in keys]

        if not nkeys:
            return 0

        try:
            return cast("int", client.delete(*nkeys))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def clear(self) -> bool:
        """Flush all cache keys."""
        client = self.get_client(write=True)

        try:
            client.flushdb()
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

        return True

    @omit_exception
    def incr(
        self,
        key: str,
        delta: int = 1,
        version: int | None = None,
        ignore_key_check: bool = False,
    ) -> int:
        """Increment a value in the cache."""
        client = self.get_client(key, write=True)
        nkey = self.make_key(key, version=version)

        try:
            if not ignore_key_check:
                lua = """
                local exists = redis.call('EXISTS', KEYS[1])
                if (exists == 1) then
                    return redis.call('INCRBY', KEYS[1], ARGV[1])
                else return false end
                """
            else:
                lua = """
                return redis.call('INCRBY', KEYS[1], ARGV[1])
                """
            value = cast("int | None", client.eval(lua, 1, nkey, delta))
            if value is None:
                raise ValueError(f"Key '{key!r}' not found")
        except ResponseError:
            # Handle encoded integers or overflow
            timeout = self.ttl(key, version=version)
            if timeout == -2:
                raise ValueError(f"Key '{key!r}' not found")
            current = self._get(key, None, version)
            if current is None:
                raise ValueError(f"Key '{key!r}' not found")
            value = current + delta
            self.set(key, value, version=version, timeout=timeout)
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

        return value

    @omit_exception
    def decr(
        self,
        key: str,
        delta: int = 1,
        version: int | None = None,
    ) -> int:
        """Decrement a value in the cache."""
        return self.incr(key, delta=-delta, version=version)

    @omit_exception
    def incr_version(
        self,
        key: str,
        delta: int = 1,
        version: int | None = None,
    ) -> int:
        """Increment the version of a key."""
        if version is None:
            version = self.version

        old_key = self.make_key(key, version)
        value = self._get(key, None, version=version)

        if value is None:
            raise ValueError(f"Key '{key!r}' not found")

        ttl = self.ttl(key, version=version)

        if isinstance(key, CacheKey):
            new_key = self.make_key(key.original_key(), version=version + delta)
        else:
            new_key = self.make_key(key, version=version + delta)

        self.set(new_key, value, timeout=ttl)
        self.delete(old_key)
        return version + delta

    # =========================================================================
    # Extended Methods
    # =========================================================================

    @omit_exception
    def keys(
        self,
        pattern: str = "*",
        version: int | None = None,
    ) -> list[str]:
        """Execute KEYS command and return matched results."""
        client = self.get_client(write=False)
        npattern = self.make_pattern(pattern, version=version)

        try:
            return [self.reverse_key(k.decode()) for k in cast("list[bytes]", client.keys(npattern))]
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def iter_keys(
        self,
        pattern: str = "*",
        version: int | None = None,
        itersize: int | None = None,
    ) -> Iterator[str]:
        """Iterate over keys matching pattern using SCAN."""
        client = self.get_client(write=False)
        npattern = self.make_pattern(pattern, version=version)

        if itersize is None:
            itersize = self._default_scan_itersize

        for item in client.scan_iter(match=npattern, count=itersize):
            yield self.reverse_key(item.decode())

    @omit_exception
    def delete_pattern(
        self,
        pattern: str,
        version: int | None = None,
        itersize: int | None = None,
    ) -> int:
        """Remove all keys matching pattern."""
        client = self.get_client(write=True)
        npattern = self.make_pattern(pattern, version=version)

        if itersize is None:
            itersize = self._default_scan_itersize

        try:
            count = 0
            pipeline = client.pipeline()
            for key in client.scan_iter(match=npattern, count=itersize):
                pipeline.delete(key)
                count += 1
            pipeline.execute()
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

        return count

    @omit_exception
    def ttl(self, key: str, version: int | None = None) -> int | None:
        """Get the time-to-live of a key in seconds."""
        client = self.get_client(key, write=False)
        nkey = self.make_key(key, version=version)

        if not cast("int", client.exists(nkey)):
            return 0

        t = cast("int", client.ttl(nkey))

        if t >= 0:
            return t
        if t == -1:
            return None
        if t == -2:
            return 0

        return None

    @omit_exception
    def pttl(self, key: str, version: int | None = None) -> int | None:
        """Get the time-to-live of a key in milliseconds."""
        client = self.get_client(key, write=False)
        nkey = self.make_key(key, version=version)

        if not cast("int", client.exists(nkey)):
            return 0

        t = cast("int", client.pttl(nkey))

        if t >= 0:
            return t
        if t == -1:
            return None
        if t == -2:
            return 0

        return None

    @omit_exception
    def persist(self, key: str, version: int | None = None) -> bool:
        """Remove the timeout from a key."""
        client = self.get_client(key, write=True)
        nkey = self.make_key(key, version=version)
        return cast("bool", client.persist(nkey))

    @omit_exception
    def expire(
        self,
        key: str,
        timeout: ExpiryT,
        version: int | None = None,
    ) -> bool:
        """Set a timeout on a key."""
        if timeout is DEFAULT_TIMEOUT:
            timeout = self.default_timeout

        client = self.get_client(key, write=True)
        nkey = self.make_key(key, version=version)
        return cast("bool", client.expire(nkey, timeout))

    @omit_exception
    def pexpire(
        self,
        key: str,
        timeout: ExpiryT,
        version: int | None = None,
    ) -> bool:
        """Set a timeout on a key in milliseconds."""
        if timeout is DEFAULT_TIMEOUT:
            timeout = self.default_timeout

        client = self.get_client(key, write=True)
        nkey = self.make_key(key, version=version)
        return cast("bool", client.pexpire(nkey, timeout))

    @omit_exception
    def expire_at(
        self,
        key: str,
        when: AbsExpiryT,
        version: int | None = None,
    ) -> bool:
        """Set an expire time as Unix timestamp."""
        client = self.get_client(key, write=True)
        nkey = self.make_key(key, version=version)
        return cast("bool", client.expireat(nkey, when))

    @omit_exception
    def pexpire_at(
        self,
        key: str,
        when: AbsExpiryT,
        version: int | None = None,
    ) -> bool:
        """Set an expire time as Unix timestamp in milliseconds."""
        client = self.get_client(key, write=True)
        nkey = self.make_key(key, version=version)
        return cast("bool", client.pexpireat(nkey, when))

    @omit_exception
    def lock(
        self,
        key: str,
        version: int | None = None,
        timeout: float | None = None,
        sleep: float = 0.1,
        blocking: bool = True,
        blocking_timeout: float | None = None,
        thread_local: bool = True,
    ) -> Any:
        """Acquire a distributed lock."""
        client = self.get_client(key, write=True)
        nkey = self.make_key(key, version=version)
        return client.lock(
            nkey,
            timeout=timeout,
            sleep=sleep,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
            thread_local=thread_local,
        )

    def pipeline(
        self,
        transaction: bool = True,
        version: int | None = None,
    ):
        """Create a pipeline for batched operations."""
        from django_redis.client.pipeline import Pipeline

        client = self.get_client(write=True)
        raw_pipeline = client.pipeline(transaction=transaction)
        return Pipeline(client=self, pipeline=raw_pipeline, version=version)


# =============================================================================
# Concrete Implementations
# =============================================================================


class RedisCacheClient(KeyValueCacheClient[Redis]):
    """Standard Redis cache backend.

    Use as: BACKEND = "django_redis.client.RedisCacheClient"
    """

    _client_class = Redis
    _pool_class = ConnectionPool


# Type variable for Sentinel class (Redis or Valkey Sentinel)
SentinelT = TypeVar("SentinelT")
SentinelPoolT = TypeVar("SentinelPoolT", bound=ConnectionPool)


class KeyValueSentinelCacheClient(KeyValueCacheClient[ClientT], Generic[ClientT, SentinelT, SentinelPoolT]):
    """Generic Sentinel cache backend base class.

    Automatically discovers primary and replica nodes via Sentinel.
    Subclass this for Redis or Valkey Sentinel support.
    """

    _sentinel_class: type[SentinelT]
    _sentinel_pool_class: type[SentinelPoolT]

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

    def _get_connection_pool(self, write: bool) -> SentinelPoolT:
        """Get a sentinel-managed connection pool."""
        index = self._get_connection_pool_index(write)
        url = self._servers[index]
        parsed = urlparse(url)

        if url in self._pools:
            return self._pools[url]  # type: ignore[return-value]

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


class RedisSentinelCacheClient(KeyValueSentinelCacheClient[Redis, Sentinel, SentinelConnectionPool]):
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

        parsed = urlparse(url)
        cluster_options = {}

        # Pass through options
        for key_opt, value in self._options.items():
            if key_opt not in _KNOWN_OPTIONS:
                cluster_options[key_opt] = value

        if parsed.hostname:
            cluster_options["host"] = parsed.hostname
        if parsed.port:
            cluster_options["port"] = parsed.port

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
    ):
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


# Try to import Valkey and create Valkey clients if available
try:
    from valkey import Valkey
    from valkey.connection import ConnectionPool as ValkeyConnectionPool

    class ValkeyCacheClient(KeyValueCacheClient[Valkey]):
        """Valkey cache backend.

        Use as: BACKEND = "django_redis.client.ValkeyCacheClient"
        """

        _client_class = Valkey
        _pool_class = ValkeyConnectionPool

    # NOTE: ValkeySentinelCacheClient is not currently provided due to a bug in valkey-py.
    # The valkey-py library's SentinelManagedConnection is missing the `_get_from_local_cache`
    # method which causes AttributeError when using Sentinel connections.
    # See: https://github.com/valkey-io/valkey-py/issues
    # Once the upstream bug is fixed, we can re-enable this by uncommenting the code below:
    #
    # from valkey.sentinel import Sentinel as ValkeySentinel
    # from valkey.sentinel import SentinelConnectionPool as ValkeySentinelConnectionPool
    #
    # class ValkeySentinelCacheClient(KeyValueSentinelCacheClient[Valkey, ValkeySentinel, ValkeySentinelConnectionPool]):
    #     """Valkey Sentinel cache backend."""
    #     _client_class = Valkey
    #     _pool_class = ValkeySentinelConnectionPool
    #     _sentinel_class = ValkeySentinel
    #     _sentinel_pool_class = ValkeySentinelConnectionPool

    class ValkeySentinelCacheClient(KeyValueCacheClient):  # type: ignore[no-redef]
        """Valkey Sentinel cache backend (currently unavailable due to valkey-py bug)."""

        def __init__(self, *args, **kwargs):
            raise NotImplementedError(
                "ValkeySentinelCacheClient is currently unavailable due to a bug in valkey-py. "
                "The SentinelManagedConnection class is missing the '_get_from_local_cache' method. "
                "Use RedisSentinelCacheClient with a Valkey server instead (protocol compatible), "
                "or wait for an upstream fix in valkey-py."
            )

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
        class ValkeyClusterCacheClient(KeyValueCacheClient):  # type: ignore[no-redef]
            """Valkey Cluster cache backend (requires valkey-py with cluster support)."""

            def __init__(self, *args, **kwargs):
                raise ImportError(
                    "ValkeyClusterCacheClient requires valkey-py with cluster support. "
                    "Install it with: pip install valkey"
                )

except ImportError:
    # Valkey not installed - create stubs that raise on instantiation
    class ValkeyCacheClient(KeyValueCacheClient):  # type: ignore[no-redef]
        """Valkey cache backend (requires valkey-py to be installed)."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "ValkeyCacheClient requires valkey-py to be installed. "
                "Install it with: pip install valkey"
            )

    class ValkeySentinelCacheClient(KeyValueCacheClient):  # type: ignore[no-redef]
        """Valkey Sentinel cache backend (currently unavailable due to valkey-py bug)."""

        def __init__(self, *args, **kwargs):
            raise NotImplementedError(
                "ValkeySentinelCacheClient is currently unavailable due to a bug in valkey-py. "
                "The SentinelManagedConnection class is missing the '_get_from_local_cache' method. "
                "Use RedisSentinelCacheClient with a Valkey server instead (protocol compatible), "
                "or wait for an upstream fix in valkey-py."
            )

    class ValkeyClusterCacheClient(KeyValueCacheClient):  # type: ignore[no-redef]
        """Valkey Cluster cache backend (requires valkey-py to be installed)."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "ValkeyClusterCacheClient requires valkey-py to be installed. "
                "Install it with: pip install valkey"
            )
