from typing import Any

from redis import Redis
from redis.typing import KeyT

from django_redis.client.mixins.protocols import ClientProtocol


class SortedSetMixin(ClientProtocol):
    """Mixin providing Redis sorted set (ZSET) operations."""

    def zadd(
        self,
        key: KeyT,
        mapping: dict[Any, float],
        nx: bool = False,
        xx: bool = False,
        ch: bool = False,
        incr: bool = False,
        gt: bool = False,
        lt: bool = False,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Add members with scores to sorted set."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        # Encode members but NOT scores (scores must remain as floats)
        encoded_mapping = {self.encode(member): score for member, score in mapping.items()}

        return int(
            client.zadd(
                nkey,
                encoded_mapping,  # type: ignore[arg-type]
                nx=nx,
                xx=xx,
                ch=ch,
                incr=incr,
                gt=gt,
                lt=lt,
            ),
        )

    def zcard(
        self,
        key: KeyT,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Get the number of members in sorted set."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        return int(client.zcard(nkey))

    def zcount(
        self,
        key: KeyT,
        min: float | str,
        max: float | str,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Count members in sorted set with scores between min and max."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        return int(client.zcount(nkey, min, max))

    def zincrby(
        self,
        key: KeyT,
        amount: float,
        value: Any,
        version: int | None = None,
        client: Redis | None = None,
    ) -> float:
        """Increment the score of member in sorted set by amount."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        value = self.encode(value)
        return float(client.zincrby(nkey, amount, value))

    def zpopmax(
        self,
        key: KeyT,
        count: int | None = None,
        version: int | None = None,
        client: Redis | None = None,
    ) -> list[tuple[Any, float]] | tuple[Any, float] | None:
        """Remove and return members with highest scores."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        result = client.zpopmax(nkey, count)

        if not result:
            return None if count is None else []

        decoded = [(self.decode(member), score) for member, score in result]

        if count is None:
            return decoded[0] if decoded else None

        return decoded

    def zpopmin(
        self,
        key: KeyT,
        count: int | None = None,
        version: int | None = None,
        client: Redis | None = None,
    ) -> list[tuple[Any, float]] | tuple[Any, float] | None:
        """Remove and return members with lowest scores."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        result = client.zpopmin(nkey, count)

        if not result:
            return None if count is None else []

        decoded = [(self.decode(member), score) for member, score in result]

        if count is None:
            return decoded[0] if decoded else None

        return decoded

    def zrange(
        self,
        key: KeyT,
        start: int,
        end: int,
        desc: bool = False,
        withscores: bool = False,
        score_cast_func: type = float,
        version: int | None = None,
        client: Redis | None = None,
    ) -> list[Any] | list[tuple[Any, float]]:
        """Return members in sorted set by index range."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        result = client.zrange(
            nkey,
            start,
            end,
            desc=desc,
            withscores=withscores,
            score_cast_func=score_cast_func,
        )

        if withscores:
            return [(self.decode(member), score) for member, score in result]

        return [self.decode(member) for member in result]

    def zrangebyscore(
        self,
        key: KeyT,
        min: float | str,
        max: float | str,
        start: int | None = None,
        num: int | None = None,
        withscores: bool = False,
        score_cast_func: type = float,
        version: int | None = None,
        client: Redis | None = None,
    ) -> list[Any] | list[tuple[Any, float]]:
        """Return members in sorted set by score range."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        result = client.zrangebyscore(
            nkey,
            min,
            max,
            start=start,
            num=num,
            withscores=withscores,
            score_cast_func=score_cast_func,
        )

        if withscores:
            return [(self.decode(member), score) for member, score in result]

        return [self.decode(member) for member in result]

    def zrank(
        self,
        key: KeyT,
        value: Any,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int | None:
        """Get the rank (index) of member in sorted set, ordered low to high."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        value = self.encode(value)
        rank = client.zrank(nkey, value)

        return int(rank) if rank is not None else None

    def zrem(
        self,
        key: KeyT,
        *values: Any,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Remove members from sorted set."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        encoded_values = [self.encode(value) for value in values]
        return int(client.zrem(nkey, *encoded_values))

    def zremrangebyscore(
        self,
        key: KeyT,
        min: float | str,
        max: float | str,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Remove members from sorted set with scores between min and max."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        return int(client.zremrangebyscore(nkey, min, max))

    def zrevrange(
        self,
        key: KeyT,
        start: int,
        end: int,
        withscores: bool = False,
        score_cast_func: type = float,
        version: int | None = None,
        client: Redis | None = None,
    ) -> list[Any] | list[tuple[Any, float]]:
        """Return members in sorted set by index range, ordered high to low."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        result = client.zrevrange(
            nkey,
            start,
            end,
            withscores=withscores,
            score_cast_func=score_cast_func,
        )

        if withscores:
            return [(self.decode(member), score) for member, score in result]

        return [self.decode(member) for member in result]

    def zrevrangebyscore(
        self,
        key: KeyT,
        max: float | str,
        min: float | str,
        start: int | None = None,
        num: int | None = None,
        withscores: bool = False,
        score_cast_func: type = float,
        version: int | None = None,
        client: Redis | None = None,
    ) -> list[Any] | list[tuple[Any, float]]:
        """Return members in sorted set by score range, ordered high to low."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        result = client.zrevrangebyscore(
            nkey,
            max,
            min,
            start=start,
            num=num,
            withscores=withscores,
            score_cast_func=score_cast_func,
        )

        if withscores:
            return [(self.decode(member), score) for member, score in result]

        return [self.decode(member) for member in result]

    def zscore(
        self,
        key: KeyT,
        value: Any,
        version: int | None = None,
        client: Redis | None = None,
    ) -> float | None:
        """Get the score of member in sorted set."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        value = self.encode(value)
        score = client.zscore(nkey, value)

        return float(score) if score is not None else None

    def zrevrank(
        self,
        key: KeyT,
        value: Any,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int | None:
        """Get the rank (index) of member in sorted set, ordered high to low."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        value = self.encode(value)
        rank = client.zrevrank(nkey, value)

        return int(rank) if rank is not None else None

    def zmscore(
        self,
        key: KeyT,
        *members: Any,
        version: int | None = None,
        client: Redis | None = None,
    ) -> list[float | None]:
        """Get scores of multiple members in sorted set."""
        if client is None:
            client = self.get_client(write=False)

        nkey = self.make_key(key, version=version)
        encoded_members = [self.encode(member) for member in members]
        scores = client.zmscore(nkey, encoded_members)

        return [float(score) if score is not None else None for score in scores]

    def zremrangebyrank(
        self,
        key: KeyT,
        start: int,
        end: int,
        version: int | None = None,
        client: Redis | None = None,
    ) -> int:
        """Remove members from sorted set by rank range."""
        if client is None:
            client = self.get_client(write=True)

        nkey = self.make_key(key, version=version)
        return int(client.zremrangebyrank(nkey, start, end))
