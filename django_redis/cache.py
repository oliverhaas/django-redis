from __future__ import annotations

import functools
import logging
from typing import TYPE_CHECKING, Any

from django import VERSION as DJANGO_VERSION

if TYPE_CHECKING:
    import builtins
    from collections.abc import Callable, Iterator, Mapping
from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.utils.module_loading import import_string

from django_redis.exceptions import ConnectionInterrupted

# Type alias matching Django's cache interface
_DEFAULT_TIMEOUT: Any = DEFAULT_TIMEOUT  # Sentinel type

CONNECTION_INTERRUPTED = object()


def omit_exception(
    method: Callable | None = None,
    return_value: Any | None = None,
):
    """Simple decorator that intercepts connection
    errors and ignores these if settings specify this.
    """
    if method is None:
        return functools.partial(omit_exception, return_value=return_value)

    @functools.wraps(method)
    def _decorator(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except ConnectionInterrupted as e:
            if self._ignore_exceptions:
                if self._log_ignored_exceptions:
                    self.logger.exception("Exception ignored")

                return return_value
            raise e.__cause__  # noqa: B904

    return _decorator


class RedisCache(BaseCache):
    def __init__(self, server: str, params: dict[str, Any]) -> None:
        super().__init__(params)
        self._server = server
        self._params = params
        self._default_scan_itersize = getattr(
            settings,
            "DJANGO_REDIS_SCAN_ITERSIZE",
            10,
        )

        options = params.get("OPTIONS", {})
        self._client_cls = options.get(
            "CLIENT_CLASS",
            "django_redis.client.DefaultClient",
        )
        self._client_cls = import_string(self._client_cls)
        self._client = None

        self._ignore_exceptions = options.get(
            "IGNORE_EXCEPTIONS",
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

    @property
    def client(self):
        """Lazy client connection property."""
        if self._client is None:
            self._client = self._client_cls(self._server, self._params, self)
        return self._client

    # =========================================================================
    # Django Cache Interface Methods
    # =========================================================================

    @omit_exception
    def set(
        self,
        key: str,
        value: Any,
        timeout: float | None = _DEFAULT_TIMEOUT,
        version: int | None = None,
        client: Any | None = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        return self.client.set(
            key,
            value,
            timeout=timeout,
            version=version,
            client=client,
            nx=nx,
            xx=xx,
        )

    @omit_exception
    def incr_version(
        self,
        key: str,
        delta: int = 1,
        version: int | None = None,
    ) -> int:
        return self.client.incr_version(key, delta=delta, version=version)

    @omit_exception
    def add(
        self,
        key: str,
        value: Any,
        timeout: float | None = _DEFAULT_TIMEOUT,
        version: int | None = None,
    ) -> bool:
        return self.client.add(key, value, timeout=timeout, version=version)

    def get(
        self,
        key: str,
        default: Any | None = None,
        version: int | None = None,
        client: Any | None = None,
    ) -> Any:
        value = self._get(key, default, version, client)
        if value is CONNECTION_INTERRUPTED:
            value = default
        return value

    @omit_exception(return_value=CONNECTION_INTERRUPTED)
    def _get(
        self,
        key: str,
        default: Any | None,
        version: int | None,
        client: Any | None,
    ) -> Any:
        return self.client.get(key, default=default, version=version, client=client)

    @omit_exception
    def delete(self, key: str, version: int | None = None) -> bool:
        """Returns a boolean instead of int since django version 3.1."""
        result = self.client.delete(key, version=version)
        return bool(result) if DJANGO_VERSION >= (3, 1, 0) else result

    @omit_exception
    def delete_pattern(
        self,
        pattern: str,
        version: int | None = None,
        itersize: int | None = None,
    ) -> int:
        if itersize is None:
            itersize = self._default_scan_itersize
        return self.client.delete_pattern(pattern, version=version, itersize=itersize)

    @omit_exception
    def delete_many(self, keys: list[str], version: int | None = None) -> None:
        return self.client.delete_many(keys, version=version)

    @omit_exception
    def clear(self) -> bool:
        return self.client.clear()

    @omit_exception(return_value={})
    def get_many(
        self,
        keys: list[str],
        version: int | None = None,
    ) -> dict[str, Any]:
        return self.client.get_many(keys, version=version)

    @omit_exception
    def set_many(
        self,
        data: Mapping[str, Any],
        timeout: float | None = _DEFAULT_TIMEOUT,
        version: int | None = None,
    ) -> list[str]:
        return self.client.set_many(data, timeout=timeout, version=version)

    @omit_exception
    def incr(
        self,
        key: str,
        delta: int = 1,
        version: int | None = None,
        client: Any | None = None,
        ignore_key_check: bool = False,
    ) -> int:
        return self.client.incr(
            key,
            delta=delta,
            version=version,
            client=client,
            ignore_key_check=ignore_key_check,
        )

    @omit_exception
    def decr(
        self,
        key: str,
        delta: int = 1,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.decr(key, delta=delta, version=version, client=client)

    @omit_exception
    def has_key(self, key: str, version: int | None = None) -> bool:
        return self.client.has_key(key, version=version)

    @omit_exception
    def keys(
        self,
        pattern: str = "*",
        version: int | None = None,
    ) -> list[str]:
        return self.client.keys(pattern, version=version)

    @omit_exception
    def iter_keys(
        self,
        pattern: str = "*",
        version: int | None = None,
        itersize: int | None = None,
    ) -> Iterator[str]:
        return self.client.iter_keys(pattern, version=version, itersize=itersize)

    @omit_exception
    def ttl(self, key: str, version: int | None = None) -> int | None:
        return self.client.ttl(key, version=version)

    @omit_exception
    def pttl(self, key: str, version: int | None = None) -> int | None:
        return self.client.pttl(key, version=version)

    @omit_exception
    def persist(self, key: str, version: int | None = None) -> bool:
        return self.client.persist(key, version=version)

    @omit_exception
    def expire(
        self,
        key: str,
        timeout: float,
        version: int | None = None,
    ) -> bool:
        return self.client.expire(key, timeout, version=version)

    @omit_exception
    def expire_at(
        self,
        key: str,
        when: Any,
        version: int | None = None,
    ) -> bool:
        return self.client.expire_at(key, when, version=version)

    @omit_exception
    def pexpire(
        self,
        key: str,
        timeout: int,
        version: int | None = None,
    ) -> bool:
        return self.client.pexpire(key, timeout, version=version)

    @omit_exception
    def pexpire_at(
        self,
        key: str,
        when: Any,
        version: int | None = None,
    ) -> bool:
        return self.client.pexpire_at(key, when, version=version)

    @omit_exception
    def lock(
        self,
        key: str,
        version: int | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> Any:
        return self.client.lock(key, version=version, timeout=timeout, **kwargs)

    @omit_exception
    def close(self, **kwargs: Any) -> None:
        self.client.close(**kwargs)

    @omit_exception
    def touch(
        self,
        key: str,
        timeout: float | None = _DEFAULT_TIMEOUT,
        version: int | None = None,
    ) -> bool:
        return self.client.touch(key, timeout=timeout, version=version)

    # =========================================================================
    # Redis Set Operations
    # =========================================================================

    @omit_exception
    def sadd(self, *args, **kwargs) -> int:
        return self.client.sadd(*args, **kwargs)

    @omit_exception
    def scard(self, *args, **kwargs) -> int:
        return self.client.scard(*args, **kwargs)

    @omit_exception
    def sdiff(self, *args, **kwargs) -> builtins.set[Any]:
        return self.client.sdiff(*args, **kwargs)

    @omit_exception
    def sdiffstore(self, *args, **kwargs) -> int:
        return self.client.sdiffstore(*args, **kwargs)

    @omit_exception
    def sinter(self, *args, **kwargs) -> builtins.set[Any]:
        return self.client.sinter(*args, **kwargs)

    @omit_exception
    def sinterstore(self, *args, **kwargs) -> int:
        return self.client.sinterstore(*args, **kwargs)

    @omit_exception
    def sismember(self, *args, **kwargs) -> bool:
        return self.client.sismember(*args, **kwargs)

    @omit_exception
    def smembers(self, *args, **kwargs) -> builtins.set[Any]:
        return self.client.smembers(*args, **kwargs)

    @omit_exception
    def smove(self, *args, **kwargs) -> bool:
        return self.client.smove(*args, **kwargs)

    @omit_exception
    def spop(self, *args, **kwargs) -> Any:
        return self.client.spop(*args, **kwargs)

    @omit_exception
    def srandmember(self, *args, **kwargs) -> Any:
        return self.client.srandmember(*args, **kwargs)

    @omit_exception
    def srem(self, *args, **kwargs) -> int:
        return self.client.srem(*args, **kwargs)

    @omit_exception
    def sscan(self, *args, **kwargs) -> builtins.set[Any]:
        return self.client.sscan(*args, **kwargs)

    @omit_exception
    def sscan_iter(self, *args, **kwargs) -> Iterator[Any]:
        return self.client.sscan_iter(*args, **kwargs)

    @omit_exception
    def smismember(self, *args, **kwargs) -> list[bool]:
        return self.client.smismember(*args, **kwargs)

    @omit_exception
    def sunion(self, *args, **kwargs) -> builtins.set[Any]:
        return self.client.sunion(*args, **kwargs)

    @omit_exception
    def sunionstore(self, *args, **kwargs) -> int:
        return self.client.sunionstore(*args, **kwargs)

    # =========================================================================
    # Redis Hash Operations
    # =========================================================================

    @omit_exception
    def hset(self, *args, **kwargs) -> int:
        return self.client.hset(*args, **kwargs)

    @omit_exception
    def hdel(self, *args, **kwargs) -> int:
        return self.client.hdel(*args, **kwargs)

    @omit_exception
    def hlen(self, *args, **kwargs) -> int:
        return self.client.hlen(*args, **kwargs)

    @omit_exception
    def hkeys(self, *args, **kwargs) -> list[str]:
        return self.client.hkeys(*args, **kwargs)

    @omit_exception
    def hexists(self, *args, **kwargs) -> bool:
        return self.client.hexists(*args, **kwargs)

    @omit_exception
    def hget(self, *args, **kwargs) -> Any | None:
        return self.client.hget(*args, **kwargs)

    @omit_exception
    def hgetall(self, *args, **kwargs) -> dict[str, Any]:
        return self.client.hgetall(*args, **kwargs)

    @omit_exception
    def hmget(self, *args, **kwargs) -> list[Any | None]:
        return self.client.hmget(*args, **kwargs)

    @omit_exception
    def hmset(self, *args, **kwargs) -> bool:
        return self.client.hmset(*args, **kwargs)

    @omit_exception
    def hincrby(self, *args, **kwargs) -> int:
        return self.client.hincrby(*args, **kwargs)

    @omit_exception
    def hincrbyfloat(self, *args, **kwargs) -> float:
        return self.client.hincrbyfloat(*args, **kwargs)

    @omit_exception
    def hsetnx(self, *args, **kwargs) -> bool:
        return self.client.hsetnx(*args, **kwargs)

    @omit_exception
    def hvals(self, *args, **kwargs) -> list[Any]:
        return self.client.hvals(*args, **kwargs)

    # =========================================================================
    # Redis Sorted Set Operations
    # =========================================================================

    @omit_exception
    def zadd(self, *args, **kwargs) -> int | float | None:
        return self.client.zadd(*args, **kwargs)

    @omit_exception
    def zcard(self, *args, **kwargs) -> int:
        return self.client.zcard(*args, **kwargs)

    @omit_exception
    def zcount(self, *args, **kwargs) -> int:
        return self.client.zcount(*args, **kwargs)

    @omit_exception
    def zincrby(self, *args, **kwargs) -> float:
        return self.client.zincrby(*args, **kwargs)

    @omit_exception
    def zpopmax(self, *args, **kwargs) -> list[tuple[Any, float]]:
        return self.client.zpopmax(*args, **kwargs)

    @omit_exception
    def zpopmin(self, *args, **kwargs) -> list[tuple[Any, float]]:
        return self.client.zpopmin(*args, **kwargs)

    @omit_exception
    def zrange(self, *args, **kwargs) -> list[Any] | list[tuple[Any, float]]:
        return self.client.zrange(*args, **kwargs)

    @omit_exception
    def zrangebyscore(self, *args, **kwargs) -> list[Any] | list[tuple[Any, float]]:
        return self.client.zrangebyscore(*args, **kwargs)

    @omit_exception
    def zrank(self, *args, **kwargs) -> int | None:
        return self.client.zrank(*args, **kwargs)

    @omit_exception
    def zrem(self, *args, **kwargs) -> int:
        return self.client.zrem(*args, **kwargs)

    @omit_exception
    def zremrangebyscore(self, *args, **kwargs) -> int:
        return self.client.zremrangebyscore(*args, **kwargs)

    @omit_exception
    def zrevrange(self, *args, **kwargs) -> list[Any] | list[tuple[Any, float]]:
        return self.client.zrevrange(*args, **kwargs)

    @omit_exception
    def zrevrangebyscore(self, *args, **kwargs) -> list[Any] | list[tuple[Any, float]]:
        return self.client.zrevrangebyscore(*args, **kwargs)

    @omit_exception
    def zscore(self, *args, **kwargs) -> float | None:
        return self.client.zscore(*args, **kwargs)

    @omit_exception
    def zrevrank(self, *args, **kwargs) -> int | None:
        return self.client.zrevrank(*args, **kwargs)

    @omit_exception
    def zmscore(self, *args, **kwargs) -> list[float | None]:
        return self.client.zmscore(*args, **kwargs)

    @omit_exception
    def zremrangebyrank(self, *args, **kwargs) -> int:
        return self.client.zremrangebyrank(*args, **kwargs)

    # =========================================================================
    # Redis List Operations
    # =========================================================================

    @omit_exception
    def lpush(self, *args, **kwargs) -> int:
        return self.client.lpush(*args, **kwargs)

    @omit_exception
    def rpush(self, *args, **kwargs) -> int:
        return self.client.rpush(*args, **kwargs)

    @omit_exception
    def lpop(self, *args, **kwargs) -> Any | list[Any] | None:
        return self.client.lpop(*args, **kwargs)

    @omit_exception
    def rpop(self, *args, **kwargs) -> Any | list[Any] | None:
        return self.client.rpop(*args, **kwargs)

    @omit_exception
    def lrange(self, *args, **kwargs) -> list[Any]:
        return self.client.lrange(*args, **kwargs)

    @omit_exception
    def lindex(self, *args, **kwargs) -> Any | None:
        return self.client.lindex(*args, **kwargs)

    @omit_exception
    def llen(self, *args, **kwargs) -> int:
        return self.client.llen(*args, **kwargs)

    @omit_exception
    def lrem(self, *args, **kwargs) -> int:
        return self.client.lrem(*args, **kwargs)

    @omit_exception
    def ltrim(self, *args, **kwargs) -> bool:
        return self.client.ltrim(*args, **kwargs)

    @omit_exception
    def lset(self, *args, **kwargs) -> bool:
        return self.client.lset(*args, **kwargs)

    @omit_exception
    def linsert(self, *args, **kwargs) -> int:
        return self.client.linsert(*args, **kwargs)

    @omit_exception
    def lpos(self, *args, **kwargs) -> int | list[int] | None:
        return self.client.lpos(*args, **kwargs)

    @omit_exception
    def lmove(self, *args, **kwargs) -> Any | None:
        return self.client.lmove(*args, **kwargs)
