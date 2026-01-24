from typing import Any, cast

from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError
from redis.exceptions import TimeoutError as RedisTimeoutError
from redis.typing import EncodableT, KeyT

from django_redis.client.mixins.protocols import ClientProtocol
from django_redis.exceptions import ConnectionInterrupted

_main_exceptions = (
    RedisConnectionError,
    RedisTimeoutError,
    ResponseError,
)


class HashMixin(ClientProtocol):
    """Mixin providing Redis hash operations."""

    def hset(
        self,
        key: KeyT,
        field: str,
        value: EncodableT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Set the value of a field in hash at key.
        Returns the number of fields added to the hash.
        """
        if client is None:
            client = self.get_client(write=True)
        nkey = self.make_key(key, version=version)
        nvalue = self.encode(value)
        return cast("int", client.hset(nkey, field, nvalue))

    def hdel(
        self,
        key: KeyT,
        field: str,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Remove a field from hash at key.
        Returns the number of fields deleted from the hash.
        """
        if client is None:
            client = self.get_client(write=True)
        nkey = self.make_key(key, version=version)
        return cast("int", client.hdel(nkey, field))

    def hlen(
        self,
        key: KeyT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Return the number of fields in hash at key."""
        if client is None:
            client = self.get_client(write=False)
        nkey = self.make_key(key, version=version)
        return cast("int", client.hlen(nkey))

    def hkeys(
        self,
        key: KeyT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> list[str]:
        """Return a list of fields in hash at key."""
        if client is None:
            client = self.get_client(write=False)
        nkey = self.make_key(key, version=version)
        try:
            return [k.decode() for k in cast("list[bytes]", client.hkeys(nkey))]
        except _main_exceptions as e:
            raise ConnectionInterrupted(connection=client) from e

    def hexists(
        self,
        key: KeyT,
        field: str,
        version: int | None = None,
        client: Redis | None = None,
    ) -> bool:
        """Return True if field exists in hash at key, else False."""
        if client is None:
            client = self.get_client(write=False)
        nkey = self.make_key(key, version=version)
        return cast("bool", client.hexists(nkey, field))

    def hget(
        self,
        key: KeyT,
        field: str,
        version: int | None = None,
        client: Redis | None = None,
    ) -> Any:
        """Get the value of a field in hash at key."""
        if client is None:
            client = self.get_client(write=False)
        nkey = self.make_key(key, version=version)
        value = cast("bytes | None", client.hget(nkey, field))
        if value is None:
            return None
        return self.decode(value)

    def hgetall(
        self,
        key: KeyT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> dict[str, Any]:
        """Get all fields and values in hash at key."""
        if client is None:
            client = self.get_client(write=False)
        nkey = self.make_key(key, version=version)
        result = cast("dict[bytes, bytes]", client.hgetall(nkey))
        return {k.decode(): self.decode(v) for k, v in result.items()}

    def hmget(
        self,
        key: KeyT,
        *fields: str,
        version: int | None = None,
        client: Redis | None = None,
    ) -> list[Any]:
        """Get values of multiple fields in hash at key."""
        if client is None:
            client = self.get_client(write=False)
        nkey = self.make_key(key, version=version)
        values = cast("list[bytes | None]", client.hmget(nkey, fields))
        return [self.decode(v) if v is not None else None for v in values]

    def hmset(
        self,
        key: KeyT,
        mapping: dict[str, EncodableT],
        version: int | None = None,
        client: Redis | None = None,
    ) -> bool:
        """Set multiple fields in hash at key."""
        if client is None:
            client = self.get_client(write=True)
        nkey = self.make_key(key, version=version)
        encoded_mapping = {field: self.encode(value) for field, value in mapping.items()}
        return cast("bool", client.hset(nkey, mapping=encoded_mapping))

    def hincrby(
        self,
        key: KeyT,
        field: str,
        amount: int = 1,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Increment the integer value of a field in hash at key."""
        if client is None:
            client = self.get_client(write=True)
        nkey = self.make_key(key, version=version)
        return cast("int", client.hincrby(nkey, field, amount))

    def hincrbyfloat(
        self,
        key: KeyT,
        field: str,
        amount: float = 1.0,
        version: int | None = None,
        client: Redis | None = None,
    ) -> float:
        """Increment the float value of a field in hash at key."""
        if client is None:
            client = self.get_client(write=True)
        nkey = self.make_key(key, version=version)
        return cast("float", client.hincrbyfloat(nkey, field, amount))

    def hsetnx(
        self,
        key: KeyT,
        field: str,
        value: EncodableT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> bool:
        """Set field in hash at key only if field does not exist."""
        if client is None:
            client = self.get_client(write=True)
        nkey = self.make_key(key, version=version)
        nvalue = self.encode(value)
        return bool(client.hsetnx(nkey, field, nvalue))

    def hvals(
        self,
        key: KeyT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> list[Any]:
        """Get all values in hash at key."""
        if client is None:
            client = self.get_client(write=False)
        nkey = self.make_key(key, version=version)
        values = cast("list[bytes]", client.hvals(nkey))
        return [self.decode(v) for v in values]
