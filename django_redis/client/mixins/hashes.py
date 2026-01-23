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
        """
        Set the value of a field in hash at key.
        Returns the number of fields added to the hash.
        """
        if client is None:
            client = self.get_client(write=True)
        nkey = self.make_key(key, version=version)
        nvalue = self.encode(value)
        return int(client.hset(nkey, field, nvalue))

    def hdel(
        self,
        key: KeyT,
        field: str,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """
        Remove a field from hash at key.
        Returns the number of fields deleted from the hash.
        """
        if client is None:
            client = self.get_client(write=True)
        nkey = self.make_key(key, version=version)
        return int(client.hdel(nkey, field))

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
        return int(client.hlen(nkey))

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
            return [k.decode() for k in client.hkeys(nkey)]
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
        return bool(client.hexists(nkey, field))
