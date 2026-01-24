from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django import VERSION as DJANGO_VERSION

if TYPE_CHECKING:
    import builtins
    from collections.abc import Iterator, Mapping
from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.utils.module_loading import import_string

from django_redis.omit_exception import omit_exception

# Type alias matching Django's cache interface
_DEFAULT_TIMEOUT: Any = DEFAULT_TIMEOUT  # Sentinel type

CONNECTION_INTERRUPTED = object()


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
        sleep: float = 0.1,
        blocking: bool = True,
        blocking_timeout: float | None = None,
        thread_local: bool = True,
    ) -> Any:
        """Acquire a distributed lock.

        Args:
            key: Lock key name
            version: Key version
            timeout: Lock timeout in seconds (None = no timeout)
            sleep: Seconds to sleep between acquire attempts
            blocking: If True, block until lock acquired or timeout
            blocking_timeout: Max seconds to wait for lock (None = wait forever)
            thread_local: If True, lock is thread-local (default)

        Returns:
            A lock object (context manager) from redis-py.

        """
        return self.client.lock(
            key,
            version=version,
            timeout=timeout,
            sleep=sleep,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
            thread_local=thread_local,
        )

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
    def sadd(
        self,
        key: str,
        *values: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.sadd(key, *values, version=version, client=client)

    @omit_exception
    def scard(
        self,
        key: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.scard(key, version=version, client=client)

    @omit_exception
    def sdiff(
        self,
        *keys: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> builtins.set[Any]:
        return self.client.sdiff(*keys, version=version, client=client)

    @omit_exception
    def sdiffstore(
        self,
        dest: str,
        *keys: str,
        version_dest: int | None = None,
        version_keys: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.sdiffstore(
            dest,
            *keys,
            version_dest=version_dest,
            version_keys=version_keys,
            client=client,
        )

    @omit_exception
    def sinter(
        self,
        *keys: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> builtins.set[Any]:
        return self.client.sinter(*keys, version=version, client=client)

    @omit_exception
    def sinterstore(
        self,
        dest: str,
        *keys: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.sinterstore(dest, *keys, version=version, client=client)

    @omit_exception
    def sismember(
        self,
        key: str,
        member: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> bool:
        return self.client.sismember(key, member, version=version, client=client)

    @omit_exception
    def smembers(
        self,
        key: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> builtins.set[Any]:
        return self.client.smembers(key, version=version, client=client)

    @omit_exception
    def smove(
        self,
        source: str,
        destination: str,
        member: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> bool:
        return self.client.smove(source, destination, member, version=version, client=client)

    @omit_exception
    def spop(
        self,
        key: str,
        count: int | None = None,
        version: int | None = None,
        client: Any | None = None,
    ) -> builtins.set[Any] | Any:
        return self.client.spop(key, count=count, version=version, client=client)

    @omit_exception
    def srandmember(
        self,
        key: str,
        count: int | None = None,
        version: int | None = None,
        client: Any | None = None,
    ) -> list[Any] | Any:
        return self.client.srandmember(key, count=count, version=version, client=client)

    @omit_exception
    def srem(
        self,
        key: str,
        *members: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.srem(key, *members, version=version, client=client)

    @omit_exception
    def sscan(
        self,
        key: str,
        match: str | None = None,
        count: int | None = 10,
        version: int | None = None,
        client: Any | None = None,
    ) -> builtins.set[Any]:
        return self.client.sscan(key, match=match, count=count, version=version, client=client)

    @omit_exception
    def sscan_iter(
        self,
        key: str,
        match: str | None = None,
        count: int | None = 10,
        version: int | None = None,
        client: Any | None = None,
    ) -> Iterator[Any]:
        return self.client.sscan_iter(key, match=match, count=count, version=version, client=client)

    @omit_exception
    def smismember(
        self,
        key: str,
        *members: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> list[bool]:
        return self.client.smismember(key, *members, version=version, client=client)

    @omit_exception
    def sunion(
        self,
        *keys: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> builtins.set[Any]:
        return self.client.sunion(*keys, version=version, client=client)

    @omit_exception
    def sunionstore(
        self,
        destination: str,
        *keys: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.sunionstore(destination, *keys, version=version, client=client)

    # =========================================================================
    # Redis Hash Operations
    # =========================================================================

    @omit_exception
    def hset(
        self,
        key: str,
        field: str,
        value: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.hset(key, field, value, version=version, client=client)

    @omit_exception
    def hdel(
        self,
        key: str,
        field: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.hdel(key, field, version=version, client=client)

    @omit_exception
    def hlen(
        self,
        key: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.hlen(key, version=version, client=client)

    @omit_exception
    def hkeys(
        self,
        key: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> list[str]:
        return self.client.hkeys(key, version=version, client=client)

    @omit_exception
    def hexists(
        self,
        key: str,
        field: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> bool:
        return self.client.hexists(key, field, version=version, client=client)

    @omit_exception
    def hget(
        self,
        key: str,
        field: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> Any | None:
        return self.client.hget(key, field, version=version, client=client)

    @omit_exception
    def hgetall(
        self,
        key: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> dict[str, Any]:
        return self.client.hgetall(key, version=version, client=client)

    @omit_exception
    def hmget(
        self,
        key: str,
        *fields: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> list[Any | None]:
        return self.client.hmget(key, *fields, version=version, client=client)

    @omit_exception
    def hmset(
        self,
        key: str,
        mapping: dict[str, Any],
        version: int | None = None,
        client: Any | None = None,
    ) -> bool:
        return self.client.hmset(key, mapping, version=version, client=client)

    @omit_exception
    def hincrby(
        self,
        key: str,
        field: str,
        amount: int = 1,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.hincrby(key, field, amount=amount, version=version, client=client)

    @omit_exception
    def hincrbyfloat(
        self,
        key: str,
        field: str,
        amount: float = 1.0,
        version: int | None = None,
        client: Any | None = None,
    ) -> float:
        return self.client.hincrbyfloat(key, field, amount=amount, version=version, client=client)

    @omit_exception
    def hsetnx(
        self,
        key: str,
        field: str,
        value: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> bool:
        return self.client.hsetnx(key, field, value, version=version, client=client)

    @omit_exception
    def hvals(
        self,
        key: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> list[Any]:
        return self.client.hvals(key, version=version, client=client)

    # =========================================================================
    # Redis Sorted Set Operations
    # =========================================================================

    @omit_exception
    def zadd(
        self,
        key: str,
        mapping: dict[Any, float],
        nx: bool = False,
        xx: bool = False,
        ch: bool = False,
        incr: bool = False,
        gt: bool = False,
        lt: bool = False,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.zadd(
            key,
            mapping,
            nx=nx,
            xx=xx,
            ch=ch,
            incr=incr,
            gt=gt,
            lt=lt,
            version=version,
            client=client,
        )

    @omit_exception
    def zcard(
        self,
        key: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.zcard(key, version=version, client=client)

    @omit_exception
    def zcount(
        self,
        key: str,
        min: float | str,
        max: float | str,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.zcount(key, min, max, version=version, client=client)

    @omit_exception
    def zincrby(
        self,
        key: str,
        amount: float,
        value: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> float:
        return self.client.zincrby(key, amount, value, version=version, client=client)

    @omit_exception
    def zpopmax(
        self,
        key: str,
        count: int | None = None,
        version: int | None = None,
        client: Any | None = None,
    ) -> list[tuple[Any, float]] | tuple[Any, float] | None:
        return self.client.zpopmax(key, count=count, version=version, client=client)

    @omit_exception
    def zpopmin(
        self,
        key: str,
        count: int | None = None,
        version: int | None = None,
        client: Any | None = None,
    ) -> list[tuple[Any, float]] | tuple[Any, float] | None:
        return self.client.zpopmin(key, count=count, version=version, client=client)

    @omit_exception
    def zrange(
        self,
        key: str,
        start: int,
        end: int,
        desc: bool = False,
        withscores: bool = False,
        score_cast_func: type = float,
        version: int | None = None,
        client: Any | None = None,
    ) -> list[Any] | list[tuple[Any, float]]:
        return self.client.zrange(
            key,
            start,
            end,
            desc=desc,
            withscores=withscores,
            score_cast_func=score_cast_func,
            version=version,
            client=client,
        )

    @omit_exception
    def zrangebyscore(
        self,
        key: str,
        min: float | str,
        max: float | str,
        start: int | None = None,
        num: int | None = None,
        withscores: bool = False,
        score_cast_func: type = float,
        version: int | None = None,
        client: Any | None = None,
    ) -> list[Any] | list[tuple[Any, float]]:
        return self.client.zrangebyscore(
            key,
            min,
            max,
            start=start,
            num=num,
            withscores=withscores,
            score_cast_func=score_cast_func,
            version=version,
            client=client,
        )

    @omit_exception
    def zrank(
        self,
        key: str,
        value: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> int | None:
        return self.client.zrank(key, value, version=version, client=client)

    @omit_exception
    def zrem(
        self,
        key: str,
        *values: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.zrem(key, *values, version=version, client=client)

    @omit_exception
    def zremrangebyscore(
        self,
        key: str,
        min: float | str,
        max: float | str,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.zremrangebyscore(key, min, max, version=version, client=client)

    @omit_exception
    def zrevrange(
        self,
        key: str,
        start: int,
        end: int,
        withscores: bool = False,
        score_cast_func: type = float,
        version: int | None = None,
        client: Any | None = None,
    ) -> list[Any] | list[tuple[Any, float]]:
        return self.client.zrevrange(
            key,
            start,
            end,
            withscores=withscores,
            score_cast_func=score_cast_func,
            version=version,
            client=client,
        )

    @omit_exception
    def zrevrangebyscore(
        self,
        key: str,
        max: float | str,
        min: float | str,
        start: int | None = None,
        num: int | None = None,
        withscores: bool = False,
        score_cast_func: type = float,
        version: int | None = None,
        client: Any | None = None,
    ) -> list[Any] | list[tuple[Any, float]]:
        return self.client.zrevrangebyscore(
            key,
            max,
            min,
            start=start,
            num=num,
            withscores=withscores,
            score_cast_func=score_cast_func,
            version=version,
            client=client,
        )

    @omit_exception
    def zscore(
        self,
        key: str,
        value: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> float | None:
        return self.client.zscore(key, value, version=version, client=client)

    @omit_exception
    def zrevrank(
        self,
        key: str,
        value: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> int | None:
        return self.client.zrevrank(key, value, version=version, client=client)

    @omit_exception
    def zmscore(
        self,
        key: str,
        *members: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> list[float | None]:
        return self.client.zmscore(key, *members, version=version, client=client)

    @omit_exception
    def zremrangebyrank(
        self,
        key: str,
        start: int,
        end: int,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.zremrangebyrank(key, start, end, version=version, client=client)

    # =========================================================================
    # Redis List Operations
    # =========================================================================

    @omit_exception
    def lpush(
        self,
        key: str,
        *values: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.lpush(key, *values, version=version, client=client)

    @omit_exception
    def rpush(
        self,
        key: str,
        *values: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.rpush(key, *values, version=version, client=client)

    @omit_exception
    def lpop(
        self,
        key: str,
        count: int | None = None,
        version: int | None = None,
        client: Any | None = None,
    ) -> Any | list[Any] | None:
        return self.client.lpop(key, count=count, version=version, client=client)

    @omit_exception
    def rpop(
        self,
        key: str,
        count: int | None = None,
        version: int | None = None,
        client: Any | None = None,
    ) -> Any | list[Any] | None:
        return self.client.rpop(key, count=count, version=version, client=client)

    @omit_exception
    def lrange(
        self,
        key: str,
        start: int,
        end: int,
        version: int | None = None,
        client: Any | None = None,
    ) -> list[Any]:
        return self.client.lrange(key, start, end, version=version, client=client)

    @omit_exception
    def lindex(
        self,
        key: str,
        index: int,
        version: int | None = None,
        client: Any | None = None,
    ) -> Any | None:
        return self.client.lindex(key, index, version=version, client=client)

    @omit_exception
    def llen(
        self,
        key: str,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.llen(key, version=version, client=client)

    @omit_exception
    def lrem(
        self,
        key: str,
        count: int,
        value: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.lrem(key, count, value, version=version, client=client)

    @omit_exception
    def ltrim(
        self,
        key: str,
        start: int,
        end: int,
        version: int | None = None,
        client: Any | None = None,
    ) -> bool:
        return self.client.ltrim(key, start, end, version=version, client=client)

    @omit_exception
    def lset(
        self,
        key: str,
        index: int,
        value: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> bool:
        return self.client.lset(key, index, value, version=version, client=client)

    @omit_exception
    def linsert(
        self,
        key: str,
        where: str,
        pivot: Any,
        value: Any,
        version: int | None = None,
        client: Any | None = None,
    ) -> int:
        return self.client.linsert(key, where, pivot, value, version=version, client=client)

    @omit_exception
    def lpos(
        self,
        key: str,
        value: Any,
        rank: int | None = None,
        count: int | None = None,
        maxlen: int | None = None,
        version: int | None = None,
        client: Any | None = None,
    ) -> int | list[int] | None:
        return self.client.lpos(
            key,
            value,
            rank=rank,
            count=count,
            maxlen=maxlen,
            version=version,
            client=client,
        )

    @omit_exception
    def lmove(
        self,
        source: str,
        destination: str,
        src_direction: str = "LEFT",
        dest_direction: str = "RIGHT",
        version: int | None = None,
        client: Any | None = None,
    ) -> Any | None:
        return self.client.lmove(
            source,
            destination,
            src_direction,
            dest_direction,
            version=version,
            client=client,
        )

    @omit_exception
    def blpop(
        self,
        *keys: str,
        timeout: float = 0,
        version: int | None = None,
        client: Any | None = None,
    ) -> tuple[str, Any] | None:
        return self.client.blpop(*keys, timeout=timeout, version=version, client=client)

    @omit_exception
    def brpop(
        self,
        *keys: str,
        timeout: float = 0,
        version: int | None = None,
        client: Any | None = None,
    ) -> tuple[str, Any] | None:
        return self.client.brpop(*keys, timeout=timeout, version=version, client=client)

    @omit_exception
    def blmove(
        self,
        source: str,
        destination: str,
        timeout: float = 0,
        src_direction: str = "LEFT",
        dest_direction: str = "RIGHT",
        version: int | None = None,
        client: Any | None = None,
    ) -> Any | None:
        return self.client.blmove(
            source,
            destination,
            timeout=timeout,
            src_direction=src_direction,
            dest_direction=dest_direction,
            version=version,
            client=client,
        )
