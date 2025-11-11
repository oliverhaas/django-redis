from typing import Any, Literal, Optional, Union

from redis import Redis
from redis.typing import KeyT

from django_redis.client.mixins.protocols import ClientProtocol


class ListMixin(ClientProtocol):
    """Mixin providing Redis list operations."""

    def lpush(
        self,
        key: KeyT,
        *values: Any,
        version: Optional[int] = None,
        client: Optional[Redis] = None,
    ) -> int:
        """Push values onto the head of the list."""
        if client is None:
            client = self.get_client(write=True)

        key = self.make_key(key, version=version)
        encoded_values = [self.encode(value) for value in values]
        return int(client.lpush(key, *encoded_values))

    def rpush(
        self,
        key: KeyT,
        *values: Any,
        version: Optional[int] = None,
        client: Optional[Redis] = None,
    ) -> int:
        """Push values onto the tail of the list."""
        if client is None:
            client = self.get_client(write=True)

        key = self.make_key(key, version=version)
        encoded_values = [self.encode(value) for value in values]
        return int(client.rpush(key, *encoded_values))

    def lpop(
        self,
        key: KeyT,
        count: Optional[int] = None,
        version: Optional[int] = None,
        client: Optional[Redis] = None,
    ) -> Union[Any, list[Any], None]:
        """Remove and return element(s) from the head of the list."""
        if client is None:
            client = self.get_client(write=True)

        key = self.make_key(key, version=version)
        result = client.lpop(key, count)

        if result is None:
            return None
        if isinstance(result, list):
            return [self.decode(value) for value in result]
        return self.decode(result)

    def rpop(
        self,
        key: KeyT,
        count: Optional[int] = None,
        version: Optional[int] = None,
        client: Optional[Redis] = None,
    ) -> Union[Any, list[Any], None]:
        """Remove and return element(s) from the tail of the list."""
        if client is None:
            client = self.get_client(write=True)

        key = self.make_key(key, version=version)
        result = client.rpop(key, count)

        if result is None:
            return None
        if isinstance(result, list):
            return [self.decode(value) for value in result]
        return self.decode(result)

    def llen(
        self,
        key: KeyT,
        version: Optional[int] = None,
        client: Optional[Redis] = None,
    ) -> int:
        """Get the length of a list."""
        if client is None:
            client = self.get_client(write=False)

        key = self.make_key(key, version=version)
        return int(client.llen(key))

    def lrange(
        self,
        key: KeyT,
        start: int,
        end: int,
        version: Optional[int] = None,
        client: Optional[Redis] = None,
    ) -> list[Any]:
        """Get a range of elements from a list."""
        if client is None:
            client = self.get_client(write=False)

        key = self.make_key(key, version=version)
        result = client.lrange(key, start, end)
        return [self.decode(value) for value in result]

    def lindex(
        self,
        key: KeyT,
        index: int,
        version: Optional[int] = None,
        client: Optional[Redis] = None,
    ) -> Optional[Any]:
        """Get an element from a list by its index."""
        if client is None:
            client = self.get_client(write=False)

        key = self.make_key(key, version=version)
        result = client.lindex(key, index)
        return self.decode(result) if result is not None else None

    def lset(
        self,
        key: KeyT,
        index: int,
        value: Any,
        version: Optional[int] = None,
        client: Optional[Redis] = None,
    ) -> bool:
        """Set the value of an element in a list by its index."""
        if client is None:
            client = self.get_client(write=True)

        key = self.make_key(key, version=version)
        value = self.encode(value)
        return bool(client.lset(key, index, value))

    def lrem(
        self,
        key: KeyT,
        count: int,
        value: Any,
        version: Optional[int] = None,
        client: Optional[Redis] = None,
    ) -> int:
        """Remove elements from a list."""
        if client is None:
            client = self.get_client(write=True)

        key = self.make_key(key, version=version)
        value = self.encode(value)
        return int(client.lrem(key, count, value))

    def ltrim(
        self,
        key: KeyT,
        start: int,
        end: int,
        version: Optional[int] = None,
        client: Optional[Redis] = None,
    ) -> bool:
        """Trim a list to the specified range."""
        if client is None:
            client = self.get_client(write=True)

        key = self.make_key(key, version=version)
        return bool(client.ltrim(key, start, end))

    def linsert(
        self,
        key: KeyT,
        where: Literal["BEFORE", "AFTER", "before", "after"],
        refvalue: Any,
        value: Any,
        version: Optional[int] = None,
        client: Optional[Redis] = None,
    ) -> int:
        """Insert an element before or after another element in a list."""
        if client is None:
            client = self.get_client(write=True)

        key = self.make_key(key, version=version)
        refvalue = self.encode(refvalue)
        value = self.encode(value)
        return int(client.linsert(key, where, refvalue, value))
