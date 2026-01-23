from typing import Any

from redis import Redis
from redis.typing import KeyT

from django_redis.client.mixins.protocols import ClientProtocol


class ListMixin(ClientProtocol):
    """Mixin providing Redis list operations."""

    def lpush(
        self,
        key: KeyT,
        *values: Any,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Insert values at head of list."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        encoded_values = [self.encode(value) for value in values]
        return int(client.lpush(nkey, *encoded_values))

    def rpush(
        self,
        key: KeyT,
        *values: Any,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Insert values at tail of list."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        encoded_values = [self.encode(value) for value in values]
        return int(client.rpush(nkey, *encoded_values))

    def lpop(
        self,
        key: KeyT,
        count: int | None = None,
        version: int | None = None,
        client: Redis | None = None,
    ) -> Any | list[Any] | None:
        """Remove and return element(s) from head of list."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        result = client.lpop(nkey, count=count)

        if result is None:
            return None
        if isinstance(result, list):
            return [self.decode(item) for item in result]
        return self.decode(result)

    def rpop(
        self,
        key: KeyT,
        count: int | None = None,
        version: int | None = None,
        client: Redis | None = None,
    ) -> Any | list[Any] | None:
        """Remove and return element(s) from tail of list."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        result = client.rpop(nkey, count=count)

        if result is None:
            return None
        if isinstance(result, list):
            return [self.decode(item) for item in result]
        return self.decode(result)

    def lrange(
        self,
        key: KeyT,
        start: int,
        end: int,
        version: int | None = None,
        client: Redis | None = None,
    ) -> list[Any]:
        """Return range of elements from list."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        result = client.lrange(nkey, start, end)
        return [self.decode(item) for item in result]

    def lindex(
        self,
        key: KeyT,
        index: int,
        version: int | None = None,
        client: Redis | None = None,
    ) -> Any | None:
        """Return element at index in list."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        result = client.lindex(nkey, index)
        if result is None:
            return None
        return self.decode(result)

    def llen(
        self,
        key: KeyT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Return length of list."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        return int(client.llen(nkey))

    def lrem(
        self,
        key: KeyT,
        count: int,
        value: Any,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Remove elements from list equal to value.

        count > 0: Remove elements equal to value moving from head to tail.
        count < 0: Remove elements equal to value moving from tail to head.
        count = 0: Remove all elements equal to value.
        """
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        encoded_value = self.encode(value)
        return int(client.lrem(nkey, count, encoded_value))

    def ltrim(
        self,
        key: KeyT,
        start: int,
        end: int,
        version: int | None = None,
        client: Redis | None = None,
    ) -> bool:
        """Trim list to the specified range."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        return bool(client.ltrim(nkey, start, end))

    def lset(
        self,
        key: KeyT,
        index: int,
        value: Any,
        version: int | None = None,
        client: Redis | None = None,
    ) -> bool:
        """Set the value at index in list."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        encoded_value = self.encode(value)
        return bool(client.lset(nkey, index, encoded_value))

    def linsert(
        self,
        key: KeyT,
        where: str,
        pivot: Any,
        value: Any,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Insert value before or after pivot in list.

        Args:
            where: "BEFORE" or "AFTER"
            pivot: The reference value to insert before/after
            value: The value to insert

        Returns:
            The length of the list after insert, or -1 if pivot not found.
        """
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        encoded_pivot = self.encode(pivot)
        encoded_value = self.encode(value)
        return int(client.linsert(nkey, where, encoded_pivot, encoded_value))
