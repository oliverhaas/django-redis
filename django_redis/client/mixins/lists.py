from typing import Any, Generic, cast

from redis.typing import KeyT

from django_redis.client.mixins.protocols import ClientProtocol, RawClientT


class ListMixin(ClientProtocol, Generic[RawClientT]):
    """Mixin providing Redis list operations."""

    def lpush(
        self,
        key: KeyT,
        *values: Any,
        version: int | None = None,
        client: RawClientT | None = None,
    ) -> int:
        """Insert values at head of list."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        encoded_values = [self.encode(value) for value in values]
        return cast("int", client.lpush(nkey, *encoded_values))

    def rpush(
        self,
        key: KeyT,
        *values: Any,
        version: int | None = None,
        client: RawClientT | None = None,
    ) -> int:
        """Insert values at tail of list."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        encoded_values = [self.encode(value) for value in values]
        return cast("int", client.rpush(nkey, *encoded_values))

    def lpop(
        self,
        key: KeyT,
        count: int | None = None,
        version: int | None = None,
        client: RawClientT | None = None,
    ) -> Any | list[Any] | None:
        """Remove and return element(s) from head of list."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        result = cast("bytes | list[bytes] | None", client.lpop(nkey, count=count))

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
        client: RawClientT | None = None,
    ) -> Any | list[Any] | None:
        """Remove and return element(s) from tail of list."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        result = cast("bytes | list[bytes] | None", client.rpop(nkey, count=count))

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
        client: RawClientT | None = None,
    ) -> list[Any]:
        """Return range of elements from list."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        result = cast("list[bytes]", client.lrange(nkey, start, end))
        return [self.decode(item) for item in result]

    def lindex(
        self,
        key: KeyT,
        index: int,
        version: int | None = None,
        client: RawClientT | None = None,
    ) -> Any | None:
        """Return element at index in list."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        result = cast("bytes | None", client.lindex(nkey, index))
        if result is None:
            return None
        return self.decode(result)

    def llen(
        self,
        key: KeyT,
        version: int | None = None,
        client: RawClientT | None = None,
    ) -> int:
        """Return length of list."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        return cast("int", client.llen(nkey))

    def lrem(
        self,
        key: KeyT,
        count: int,
        value: Any,
        version: int | None = None,
        client: RawClientT | None = None,
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
        return cast("int", client.lrem(nkey, count, encoded_value))

    def ltrim(
        self,
        key: KeyT,
        start: int,
        end: int,
        version: int | None = None,
        client: RawClientT | None = None,
    ) -> bool:
        """Trim list to the specified range."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        return cast("bool", client.ltrim(nkey, start, end))

    def lset(
        self,
        key: KeyT,
        index: int,
        value: Any,
        version: int | None = None,
        client: RawClientT | None = None,
    ) -> bool:
        """Set the value at index in list."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        encoded_value = self.encode(value)
        return cast("bool", client.lset(nkey, index, encoded_value))

    def linsert(
        self,
        key: KeyT,
        where: str,
        pivot: Any,
        value: Any,
        version: int | None = None,
        client: RawClientT | None = None,
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
        return cast("int", client.linsert(nkey, where, encoded_pivot, encoded_value))

    def lpos(
        self,
        key: KeyT,
        value: Any,
        rank: int | None = None,
        count: int | None = None,
        maxlen: int | None = None,
        version: int | None = None,
        client: RawClientT | None = None,
    ) -> int | list[int] | None:
        """Return the index of matching elements in list.

        Args:
            value: The value to find
            rank: The rank of the element to return (1 for first, -1 for last)
            count: Return up to count matches (returns list if set)
            maxlen: Limit search to first maxlen elements

        Returns:
            Index, list of indices (if count set), or None if not found.

        """
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        encoded_value = self.encode(value)
        return cast(
            "int | list[int] | None",
            client.lpos(nkey, encoded_value, rank=rank, count=count, maxlen=maxlen),
        )

    def lmove(
        self,
        source: KeyT,
        destination: KeyT,
        src_direction: str = "LEFT",
        dest_direction: str = "RIGHT",
        version: int | None = None,
        client: RawClientT | None = None,
    ) -> Any | None:
        """Atomically move element from source list to destination list.

        Args:
            source: Source list key
            destination: Destination list key
            src_direction: "LEFT" or "RIGHT" - which end to pop from source
            dest_direction: "LEFT" or "RIGHT" - which end to push to destination

        Returns:
            The element being moved, or None if source is empty.

        """
        if client is None:
            client = self.get_client(write=True)

        nsrc = self.make_key(source, version=version)
        ndst = self.make_key(destination, version=version)
        result = cast("bytes | None", client.lmove(nsrc, ndst, src_direction, dest_direction))
        if result is None:
            return None
        return self.decode(result)

    def blpop(
        self,
        *keys: KeyT,
        timeout: float = 0,
        version: int | None = None,
        client: RawClientT | None = None,
    ) -> tuple[str, Any] | None:
        """Blocking pop from head of list.

        Blocks until an element is available or timeout expires.

        Args:
            *keys: One or more list keys to pop from (first available)
            timeout: Seconds to block (0 = block indefinitely)
            version: Key version

        Returns:
            Tuple of (key, value) or None if timeout expires.

        """
        if client is None:
            client = self.get_client(write=True)

        nkeys = [self.make_key(key, version=version) for key in keys]
        result = cast("tuple[bytes, bytes] | None", client.blpop(nkeys, timeout=timeout))
        if result is None:
            return None
        key_bytes, value_bytes = result
        return (key_bytes.decode(), self.decode(value_bytes))

    def brpop(
        self,
        *keys: KeyT,
        timeout: float = 0,
        version: int | None = None,
        client: RawClientT | None = None,
    ) -> tuple[str, Any] | None:
        """Blocking pop from tail of list.

        Blocks until an element is available or timeout expires.

        Args:
            *keys: One or more list keys to pop from (first available)
            timeout: Seconds to block (0 = block indefinitely)
            version: Key version

        Returns:
            Tuple of (key, value) or None if timeout expires.

        """
        if client is None:
            client = self.get_client(write=True)

        nkeys = [self.make_key(key, version=version) for key in keys]
        result = cast("tuple[bytes, bytes] | None", client.brpop(nkeys, timeout=timeout))
        if result is None:
            return None
        key_bytes, value_bytes = result
        return (key_bytes.decode(), self.decode(value_bytes))

    def blmove(
        self,
        source: KeyT,
        destination: KeyT,
        timeout: float = 0,
        src_direction: str = "LEFT",
        dest_direction: str = "RIGHT",
        version: int | None = None,
        client: RawClientT | None = None,
    ) -> Any | None:
        """Blocking atomically move element from source list to destination list.

        Blocks until an element is available in source or timeout expires.

        Args:
            source: Source list key
            destination: Destination list key
            timeout: Seconds to block (0 = block indefinitely)
            src_direction: "LEFT" or "RIGHT" - which end to pop from source
            dest_direction: "LEFT" or "RIGHT" - which end to push to destination

        Returns:
            The element being moved, or None if timeout expires.

        """
        if client is None:
            client = self.get_client(write=True)

        nsrc = self.make_key(source, version=version)
        ndst = self.make_key(destination, version=version)
        result = cast(
            "bytes | None",
            client.blmove(nsrc, ndst, timeout, src_direction, dest_direction),
        )
        if result is None:
            return None
        return self.decode(result)
