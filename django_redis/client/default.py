"""Default cache client for Redis-compatible backends.

This module provides the base KeyValueCacheClient class and standard Redis/Valkey
implementations that extend Django's BaseCache directly.
"""

from __future__ import annotations

import logging
import random
import re
import socket
from collections import OrderedDict
from collections.abc import Iterable, Iterator, Mapping
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from redis import Redis
from redis.connection import ConnectionPool, DefaultParser
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError
from redis.exceptions import TimeoutError as RedisTimeoutError
from redis.typing import AbsExpiryT, EncodableT, ExpiryT, KeyT

from django_redis.client.mixins import HashMixin, ListMixin, SetMixin, SortedSetMixin
from django_redis.compat import create_compressor, create_serializer
from django_redis.exceptions import CompressorError, ConnectionInterrupted, SerializerError
from django_redis.omit_exception import omit_exception
from django_redis.util import CacheKey

if TYPE_CHECKING:
    from django_redis.client.pipeline import Pipeline

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

logger = logging.getLogger(__name__)


class KeyValueCacheClient(
    BaseCache,
    HashMixin["ClientT"],
    ListMixin["ClientT"],
    SetMixin["ClientT"],
    SortedSetMixin["ClientT"],
    Generic[ClientT],
):
    """Unified cache backend and client.

    Extends Django's BaseCache and implements all Redis operations directly.
    No delegation layer - this class IS both the backend and the client.
    """

    # Subclasses must set these to appropriate client/pool classes
    _client_class: type[ClientT]
    _pool_class: type[ConnectionPool]

    # Default scan iteration batch size
    _default_scan_itersize: int = 10

    def __init__(self, server: str, params: dict[str, Any]) -> None:
        super().__init__(params)

        # Parse servers
        if isinstance(server, str):
            self._servers = re.split("[;,]", server)
        else:
            self._servers = list(server)

        # Connection pools keyed by server URL
        self._pools: dict[str, ConnectionPool] = {}

        # Extract OPTIONS
        self._options = params.get("OPTIONS", {})

        # Override pool/client classes if specified in options
        if "pool_class" in self._options:
            self._pool_class = import_string(self._options["pool_class"])
        if "redis_client_class" in self._options:
            self._client_class = import_string(self._options["redis_client_class"])

        # Setup serializers
        serializer_config = self._options.get(
            "serializer",
            "django_redis.serializers.pickle.PickleSerializer",
        )
        self._serializers = self._create_serializers(serializer_config)

        # Setup compressors
        compressor_config = self._options.get("compressor")
        self._compressors = self._create_compressors(compressor_config)

        # Exception handling configuration
        self._ignore_exceptions = self._options.get(
            "ignore_exceptions",
            getattr(settings, "DJANGO_REDIS_IGNORE_EXCEPTIONS", False),
        )
        self._log_ignored_exceptions = self._options.get(
            "log_ignored_exceptions",
            getattr(settings, "DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS", False),
        )
        self.logger = (
            logger
            if self._log_ignored_exceptions
            else None
        )

        # Key reverse function
        reverse_key_path = self._options.get("reverse_key_function")
        if reverse_key_path:
            self._reverse_key = import_string(reverse_key_path)
        else:
            self._reverse_key = self._default_reverse_key

    def _get_pool_options(self) -> dict[str, Any]:
        """Build options dict for connection pool."""
        pool_options: dict[str, Any] = {}

        # Parser class
        parser_class = self._options.get("parser_class")
        if parser_class:
            pool_options["parser_class"] = import_string(parser_class)
        else:
            pool_options["parser_class"] = DefaultParser

        # Pass through unknown options to pool
        for key, value in self._options.items():
            if key not in _KNOWN_OPTIONS:
                pool_options[key] = value

        return pool_options

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

    def _get_connection_pool_index(self, write: bool) -> int:
        """Determine which server index to use for the operation.

        Args:
            write: True for write operations (use primary), False for reads

        Returns:
            Index into self._servers list

        """
        if write or len(self._servers) == 1:
            return 0
        return random.randint(1, len(self._servers) - 1)

    def _get_connection_pool(self, write: bool) -> ConnectionPool:
        """Get or create a connection pool for the given operation type."""
        index = self._get_connection_pool_index(write)
        url = self._servers[index]

        if url in self._pools:
            return self._pools[url]

        pool_options = self._get_pool_options()
        pool = self._pool_class.from_url(url, **pool_options)
        self._pools[url] = pool

        return pool

    def get_client(self, key: KeyT | None = None, *, write: bool = False) -> ClientT:
        """Get a Redis client for the given operation.

        Args:
            key: Optional key (used by cluster for routing)
            write: True for write operations

        Returns:
            Redis client instance

        """
        pool = self._get_connection_pool(write)
        return self._client_class(connection_pool=pool)

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
        raise SerializerError("No serializers configured")

    # =========================================================================
    # Key Management
    # =========================================================================

    def make_key(self, key: str, version: int | None = None) -> CacheKey:
        """Build a cache key with prefix and version."""
        return CacheKey(self.key_func(key, self.key_prefix, version or self.version))

    def make_pattern(self, pattern: str, version: int | None = None) -> str:
        """Build a pattern for key matching."""
        prefix = glob_escape(self.key_prefix)
        ver = version or self.version
        return self.key_func(pattern, prefix, ver)

    def _default_reverse_key(self, key: str) -> str:
        """Default reverse key function - strips prefix:version: from key."""
        # Keys are typically formatted as prefix:version:key
        parts = key.split(":", 2)
        if len(parts) == 3:
            return parts[2]
        return key

    def reverse_key(self, key: str) -> str:
        """Reverse a made key back to original."""
        return self._reverse_key(key)

    # =========================================================================
    # Django BaseCache Interface Implementation
    # =========================================================================

    @omit_exception
    def add(
        self,
        key: str,
        value: Any,
        timeout: float | None = _DEFAULT_TIMEOUT,
        version: int | None = None,
    ) -> bool:
        """Set a value only if the key doesn't exist."""
        return self._add(key, value, timeout, version)

    def _add(
        self,
        key: str,
        value: Any,
        timeout: float | None = _DEFAULT_TIMEOUT,
        version: int | None = None,
    ) -> bool:
        """Internal add implementation without exception handling."""
        nkey = self.make_key(key, version=version)
        nvalue = self.encode(value)

        if timeout is DEFAULT_TIMEOUT:
            timeout = self.default_timeout

        client = self.get_client(nkey, write=True)

        # nx=True means "set if not exists"
        if timeout is None:
            return bool(client.set(nkey, nvalue, nx=True))
        elif timeout == 0:
            # 0 timeout means delete immediately
            return False
        else:
            timeout_ms = int(timeout * 1000)
            return bool(client.set(nkey, nvalue, nx=True, px=timeout_ms))

    def get(
        self,
        key: str,
        default: Any = None,
        version: int | None = None,
    ) -> Any:
        """Fetch a value from the cache."""
        nkey = self.make_key(key, version=version)
        client = self.get_client(nkey, write=False)

        try:
            val = client.get(nkey)
        except _main_exceptions as e:
            if self._ignore_exceptions:
                if self._log_ignored_exceptions:
                    self.logger.exception("Exception ignored")
                return default
            raise e from None

        if val is None:
            return default

        return self.decode(val)

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
        nkey = self.make_key(key, version=version)
        client = self.get_client(nkey, write=True)

        try:
            result = client.delete(nkey)
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

        return bool(result)

    @omit_exception(return_value={})
    def get_many(
        self,
        keys: Iterable[str],
        version: int | None = None,
    ) -> dict[str, Any]:
        """Retrieve many keys at once."""
        if not keys:
            return {}

        client = self.get_client(write=False)

        # Create mapping of made_key -> original_key
        map_keys = OrderedDict((self.make_key(k, version=version), k) for k in keys)

        try:
            results = cast("list[bytes | None]", client.mget(list(map_keys.keys())))

            recovered_data = {}
            for (_, original_key), value in zip(map_keys.items(), results, strict=True):
                if value is not None:
                    recovered_data[original_key] = self.decode(value)

        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

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

        if timeout is DEFAULT_TIMEOUT:
            timeout = self.default_timeout

        try:
            # Prepare data
            prepared = {
                self.make_key(k, version=version): self.encode(v)
                for k, v in data.items()
            }

            if timeout is None:
                # No expiry
                client.mset(prepared)
            elif timeout == 0:
                # 0 timeout means delete all
                client.delete(*prepared.keys())
            else:
                # Set all, then expire all (no atomic mset+expire in Redis)
                timeout_ms = int(timeout * 1000)
                pipe = client.pipeline()
                for nkey, nvalue in prepared.items():
                    pipe.set(nkey, nvalue, px=timeout_ms)
                pipe.execute()

        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

        return []

    @omit_exception
    def delete_many(self, keys: list[str], version: int | None = None) -> int:
        """Remove multiple keys from the cache."""
        client = self.get_client(write=True)
        made_keys = [self.make_key(k, version=version) for k in keys]

        if not made_keys:
            return 0

        try:
            result = client.delete(*made_keys)
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

        return cast("int", result)

    @omit_exception
    def has_key(self, key: str, version: int | None = None) -> bool:
        """Check if a key exists in the cache."""
        nkey = self.make_key(key, version=version)
        client = self.get_client(nkey, write=False)

        try:
            return bool(client.exists(nkey))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

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
            # TTL of -1 means no expiry - convert to None for set()
            if timeout == -1:
                timeout = None
            current = self.get(key, None, version)
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
        return self.incr(key, -delta, version)

    @omit_exception
    def touch(
        self,
        key: str,
        timeout: float | None = _DEFAULT_TIMEOUT,
        version: int | None = None,
    ) -> bool:
        """Update the expiry time on a key."""
        nkey = self.make_key(key, version=version)
        client = self.get_client(nkey, write=True)

        if timeout is DEFAULT_TIMEOUT:
            timeout = self.default_timeout

        try:
            if timeout is None:
                return bool(client.persist(nkey))
            elif timeout == 0:
                return bool(client.delete(nkey))
            else:
                timeout_ms = int(timeout * 1000)
                return bool(client.pexpire(nkey, timeout_ms))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def clear(self) -> bool:
        """Flush all keys in the current database."""
        client = self.get_client(write=True)

        try:
            client.flushdb()
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

        return True

    # =========================================================================
    # Extended Methods (beyond BaseCache)
    # =========================================================================

    @omit_exception
    def keys(
        self,
        pattern: str = "*",
        version: int | None = None,
    ) -> list[str]:
        """Return all keys matching pattern."""
        client = self.get_client(write=False)
        npattern = self.make_pattern(pattern, version=version)

        try:
            keys_result = cast("list[bytes]", client.keys(npattern))
            return [self.reverse_key(k.decode()) for k in keys_result]
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
        """Delete all keys matching pattern."""
        client = self.get_client(write=True)
        npattern = self.make_pattern(pattern, version=version)

        if itersize is None:
            itersize = self._default_scan_itersize

        try:
            count = 0
            pipe = client.pipeline()
            batch_count = 0

            for key in client.scan_iter(match=npattern, count=itersize):
                pipe.delete(key)
                count += 1
                batch_count += 1

                # Execute in batches to avoid memory issues
                if batch_count >= 1000:
                    pipe.execute()
                    pipe = client.pipeline()
                    batch_count = 0

            if batch_count:
                pipe.execute()

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
        """Remove the expiry from a key."""
        nkey = self.make_key(key, version=version)
        client = self.get_client(nkey, write=True)

        try:
            return bool(client.persist(nkey))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def expire(
        self,
        key: str,
        timeout: ExpiryT,
        version: int | None = None,
    ) -> bool:
        """Set expiry time on a key in seconds."""
        if timeout is DEFAULT_TIMEOUT:
            timeout = self.default_timeout

        nkey = self.make_key(key, version=version)
        client = self.get_client(nkey, write=True)

        try:
            timeout_ms = int(timeout * 1000)
            return bool(client.pexpire(nkey, timeout_ms))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def expire_at(
        self,
        key: str,
        when: AbsExpiryT,
        version: int | None = None,
    ) -> bool:
        """Set expiry to an absolute time (seconds or datetime)."""
        nkey = self.make_key(key, version=version)
        client = self.get_client(nkey, write=True)

        try:
            return bool(client.expireat(nkey, when))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def pexpire(
        self,
        key: str,
        timeout: ExpiryT,
        version: int | None = None,
    ) -> bool:
        """Set expiry time on a key in milliseconds."""
        if timeout is DEFAULT_TIMEOUT:
            timeout = self.default_timeout
            if timeout is not None:
                timeout = int(timeout * 1000)

        nkey = self.make_key(key, version=version)
        client = self.get_client(nkey, write=True)

        try:
            return bool(client.pexpire(nkey, timeout))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def pexpire_at(
        self,
        key: str,
        when: AbsExpiryT,
        version: int | None = None,
    ) -> bool:
        """Set expiry to an absolute time in milliseconds."""
        nkey = self.make_key(key, version=version)
        client = self.get_client(nkey, write=True)

        try:
            return bool(client.pexpireat(nkey, when))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def lock(
        self,
        key: str,
        version: int | None = None,
        timeout: float | None = None,
        sleep: float = 0.1,
        blocking: bool = True,
        blocking_timeout: float | None = None,
        lock_class: type | None = None,
        thread_local: bool = True,
    ):
        """Return a Lock object for distributed locking."""
        nkey = self.make_key(key, version=version)
        client = self.get_client(nkey, write=True)

        if lock_class is None:
            lock_class = client.lock.__self__.__class__.lock  # type: ignore[attr-defined]

        return client.lock(
            nkey,
            timeout=timeout,
            sleep=sleep,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
            thread_local=thread_local,
        )

    @omit_exception
    def scan(
        self,
        cursor: int = 0,
        match: str | None = None,
        count: int | None = None,
        version: int | None = None,
    ) -> tuple[int, list[str]]:
        """Execute SCAN command and return cursor, keys."""
        client = self.get_client(write=False)

        if match is not None:
            match = self.make_pattern(match, version=version)

        try:
            new_cursor, keys = client.scan(cursor=cursor, match=match, count=count)
            return new_cursor, [self.reverse_key(k.decode()) for k in keys]
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def getex(
        self,
        key: str,
        default: Any = None,
        version: int | None = None,
        *,
        ex: ExpiryT | None = None,
        px: ExpiryT | None = None,
        exat: AbsExpiryT | None = None,
        pxat: AbsExpiryT | None = None,
        persist: bool = False,
    ) -> Any:
        """Get value and optionally update its expiry."""
        nkey = self.make_key(key, version=version)
        client = self.get_client(nkey, write=True)

        try:
            val = client.getex(
                nkey,
                ex=ex,
                px=px,
                exat=exat,
                pxat=pxat,
                persist=persist,
            )
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

        if val is None:
            return default

        return self.decode(val)

    @omit_exception
    def getdel(
        self,
        key: str,
        default: Any = None,
        version: int | None = None,
    ) -> Any:
        """Get value and delete the key."""
        nkey = self.make_key(key, version=version)
        client = self.get_client(nkey, write=True)

        try:
            val = client.getdel(nkey)
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

        if val is None:
            return default

        return self.decode(val)

    @omit_exception
    def setex(
        self,
        key: str,
        timeout: int,
        value: Any,
        version: int | None = None,
    ) -> bool:
        """Set value with expiry in seconds (atomic)."""
        nkey = self.make_key(key, version=version)
        nvalue = self.encode(value)
        client = self.get_client(nkey, write=True)

        try:
            return bool(client.setex(nkey, timeout, nvalue))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def psetex(
        self,
        key: str,
        timeout: int,
        value: Any,
        version: int | None = None,
    ) -> bool:
        """Set value with expiry in milliseconds (atomic)."""
        nkey = self.make_key(key, version=version)
        nvalue = self.encode(value)
        client = self.get_client(nkey, write=True)

        try:
            return bool(client.psetex(nkey, timeout, nvalue))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def setnx(
        self,
        key: str,
        value: Any,
        version: int | None = None,
    ) -> bool:
        """Set value only if key doesn't exist."""
        nkey = self.make_key(key, version=version)
        nvalue = self.encode(value)
        client = self.get_client(nkey, write=True)

        try:
            return bool(client.setnx(nkey, nvalue))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def mget(
        self,
        keys: Iterable[str],
        version: int | None = None,
    ) -> list[Any]:
        """Get multiple values (returns list, preserving order)."""
        if not keys:
            return []

        client = self.get_client(write=False)
        nkeys = [self.make_key(k, version=version) for k in keys]

        try:
            results = client.mget(nkeys)
            return [
                self.decode(v) if v is not None else None
                for v in results
            ]
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    @omit_exception
    def mset(
        self,
        data: Mapping[str, Any],
        version: int | None = None,
    ) -> bool:
        """Set multiple values (no expiry)."""
        if not data:
            return True

        client = self.get_client(write=True)
        prepared = {
            self.make_key(k, version=version): self.encode(v)
            for k, v in data.items()
        }

        try:
            return bool(client.mset(prepared))
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    def close(self, **kwargs: Any) -> None:
        """Close all connection pools if configured to do so."""
        close_flag = self._options.get(
            "close_connection",
            getattr(settings, "DJANGO_REDIS_CLOSE_CONNECTION", False),
        )
        if close_flag:
            for pool in self._pools.values():
                pool.disconnect()
            self._pools.clear()

    def pipeline(
        self,
        transaction: bool = True,
        version: int | None = None,
    ) -> "Pipeline":
        """Create a pipeline for batched operations.

        Args:
            transaction: If True, use MULTI/EXEC for atomicity
            version: Default version for keys in this pipeline

        Returns:
            Pipeline object that wraps Redis pipeline with encoding/decoding

        """
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

except ImportError:
    # Valkey not installed - create stub that raises on instantiation
    class ValkeyCacheClient(KeyValueCacheClient):  # type: ignore[no-redef]
        """Valkey cache backend (requires valkey-py to be installed)."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "ValkeyCacheClient requires valkey-py to be installed. "
                "Install it with: pip install valkey"
            )
