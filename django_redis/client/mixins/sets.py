import builtins
from collections.abc import Iterator
from typing import Any, cast

from redis import Redis
from redis.typing import EncodableT, KeyT, PatternT

from django_redis.client.mixins.protocols import ClientProtocol


class SetMixin(ClientProtocol):
    """Mixin providing Redis set operations."""

    def sadd(
        self,
        key: KeyT,
        *values: Any,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Add members to a set."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        encoded_values = [self.encode(value) for value in values]
        return int(client.sadd(nkey, *encoded_values))

    def scard(
        self,
        key: KeyT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Get the number of members in a set."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        return int(client.scard(nkey))

    def sdiff(
        self,
        *keys: KeyT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> builtins.set[Any]:
        """Return the difference of multiple sets."""
        if client is None:
            client = self.get_client(write=False)

        nkeys = [self.make_key(key, version=version) for key in keys]
        return {self.decode(value) for value in client.sdiff(*nkeys)}

    def sdiffstore(
        self,
        dest: KeyT,
        *keys: KeyT,
        version_dest: int | None = None,
        version_keys: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Store the difference of multiple sets in a destination set."""
        if client is None:
            client = self.get_client(write=True)

        ndest = self.make_key(dest, version=version_dest)
        nkeys = [self.make_key(key, version=version_keys) for key in keys]
        return int(client.sdiffstore(ndest, *nkeys))

    def sinter(
        self,
        *keys: KeyT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> builtins.set[Any]:
        """Return the intersection of multiple sets."""
        if client is None:
            client = self.get_client(write=False)

        nkeys = [self.make_key(key, version=version) for key in keys]
        return {self.decode(value) for value in client.sinter(*nkeys)}

    def sinterstore(
        self,
        dest: KeyT,
        *keys: KeyT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Store the intersection of multiple sets in a destination set."""
        if client is None:
            client = self.get_client(write=True)

        ndest = self.make_key(dest, version=version)
        nkeys = [self.make_key(key, version=version) for key in keys]
        return int(client.sinterstore(ndest, *nkeys))

    def smismember(
        self,
        key: KeyT,
        *members,
        version: int | None = None,
        client: Redis | None = None,
    ) -> list[bool]:
        """Check if multiple members exist in a set."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        encoded_members = [self.encode(member) for member in members]
        return [bool(value) for value in client.smismember(nkey, *encoded_members)]

    def sismember(
        self,
        key: KeyT,
        member: Any,
        version: int | None = None,
        client: Redis | None = None,
    ) -> bool:
        """Check if a member exists in a set."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        nmember = self.encode(member)
        return bool(client.sismember(nkey, nmember))

    def smembers(
        self,
        key: KeyT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> builtins.set[Any]:
        """Get all members of a set."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        return {self.decode(value) for value in client.smembers(nkey)}

    def smove(
        self,
        source: KeyT,
        destination: KeyT,
        member: Any,
        version: int | None = None,
        client: Redis | None = None,
    ) -> bool:
        """Move a member from one set to another."""
        if client is None:
            client = self.get_client(write=True)

        nsource = self.make_key(source, version=version)
        ndestination = self.make_key(destination, version=version)
        nmember = self.encode(member)
        return bool(client.smove(nsource, ndestination, nmember))

    def spop(
        self,
        key: KeyT,
        count: int | None = None,
        version: int | None = None,
        client: Redis | None = None,
    ) -> builtins.set | Any:
        """Remove and return random member(s) from a set."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        result = client.spop(nkey, count)
        return self._decode_iterable_result(result)

    def srandmember(
        self,
        key: KeyT,
        count: int | None = None,
        version: int | None = None,
        client: Redis | None = None,
    ) -> list | Any:
        """Get random member(s) from a set without removing."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        result = client.srandmember(nkey, count)
        return self._decode_iterable_result(result, convert_to_set=False)

    def srem(
        self,
        key: KeyT,
        *members: EncodableT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Remove members from a set."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        nmembers = [self.encode(member) for member in members]
        return int(client.srem(nkey, *nmembers))

    def sscan(
        self,
        key: KeyT,
        match: str | None = None,
        count: int | None = 10,
        version: int | None = None,
        client: Redis | None = None,
    ) -> builtins.set[Any]:
        """Scan members of a set."""
        if self._has_compression_enabled() and match:
            err_msg = "Using match with compression is not supported."
            raise ValueError(err_msg)

        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        cursor, result = client.sscan(
            nkey,
            match=cast("PatternT", self.encode(match)) if match else None,
            count=count,
        )
        return {self.decode(value) for value in result}

    def sscan_iter(
        self,
        key: KeyT,
        match: str | None = None,
        count: int | None = 10,
        version: int | None = None,
        client: Redis | None = None,
    ) -> Iterator[Any]:
        """Iterate over members of a set using scan."""
        if self._has_compression_enabled() and match:
            err_msg = "Using match with compression is not supported."
            raise ValueError(err_msg)

        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        for value in client.sscan_iter(
            nkey,
            match=cast("PatternT", self.encode(match)) if match else None,
            count=count,
        ):
            yield self.decode(value)

    def sunion(
        self,
        *keys: KeyT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> builtins.set[Any]:
        """Return the union of multiple sets."""
        if client is None:
            client = self.get_client(write=False)

        nkeys = [self.make_key(key, version=version) for key in keys]
        return {self.decode(value) for value in client.sunion(*nkeys)}

    def sunionstore(
        self,
        destination: Any,
        *keys: KeyT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Store the union of multiple sets in a destination set."""
        if client is None:
            client = self.get_client(write=True)

        ndestination = self.make_key(destination, version=version)
        nkeys = [self.make_key(key, version=version) for key in keys]
        return int(client.sunionstore(ndestination, *nkeys))
