from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

    from redis.typing import KeyT

    from django_redis.client.mixins import ClientProtocol


class WrappedPipeline:
    """Pipeline wrapper that handles key prefixing and value serialization.

    This class wraps a raw Redis pipeline and provides the same interface
    as the django-redis client, but queues commands for batch execution.
    On execute(), it applies the appropriate decoders to each result.

    Usage:
        with cache.pipeline() as pipe:
            pipe.set("key1", "value1")
            pipe.get("key1")
            pipe.lpush("list1", "a", "b")
            pipe.lrange("list1", 0, -1)
            results = pipe.execute()
        # results = [True, "value1", 2, ["b", "a"]]
    """

    def __init__(
        self,
        client: ClientProtocol,
        pipeline: Any,
        version: int | None = None,
    ) -> None:
        """Initialize the wrapped pipeline.

        Args:
            client: The django-redis client (for make_key, encode, decode)
            pipeline: The raw Redis pipeline object
            version: Default key version (uses client default if None)
        """
        self._client = client
        self._pipeline = pipeline
        self._version = version
        self._decoders: list[Callable[[Any], Any]] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        # Pipeline cleanup is handled by the raw pipeline
        pass

    def execute(self) -> list[Any]:
        """Execute all queued commands and decode the results.

        Returns:
            List of decoded results, one per queued command.
        """
        results = self._pipeline.execute()
        decoded = []
        for result, decoder in zip(results, self._decoders, strict=True):
            decoded.append(decoder(result))
        return decoded

    # --- Decoder helpers ---

    def _noop(self, value: Any) -> Any:
        """Return value unchanged (for int, bool, etc.)."""
        return value

    def _decode_single(self, value: bytes | None) -> Any:
        """Decode a single value, returning None if None."""
        if value is None:
            return None
        return self._client.decode(value)

    def _decode_list(self, value: list[bytes]) -> list[Any]:
        """Decode a list of values."""
        return [self._client.decode(item) for item in value]

    def _decode_single_or_list(self, value: bytes | list[bytes] | None) -> Any:
        """Decode value that may be single item, list, or None (lpop/rpop with count)."""
        if value is None:
            return None
        if isinstance(value, list):
            return [self._client.decode(item) for item in value]
        return self._client.decode(value)

    # --- Key/value helpers ---

    def _make_key(self, key: KeyT, version: int | None = None) -> KeyT:
        """Create a prefixed key."""
        v = version if version is not None else self._version
        return self._client.make_key(key, version=v)

    def _encode(self, value: Any) -> bytes | int:
        """Encode a value for storage."""
        return self._client.encode(value)

    # --- Core cache operations ---

    def set(
        self,
        key: KeyT,
        value: Any,
        timeout: int | None = None,
        version: int | None = None,
        nx: bool = False,
        xx: bool = False,
    ) -> Self:
        """Queue a SET command."""
        nkey = self._make_key(key, version)
        nvalue = self._encode(value)

        kwargs: dict[str, Any] = {}
        if timeout is not None:
            kwargs["ex"] = timeout
        if nx:
            kwargs["nx"] = True
        if xx:
            kwargs["xx"] = True

        self._pipeline.set(nkey, nvalue, **kwargs)
        self._decoders.append(self._noop)
        return self

    def get(self, key: KeyT, version: int | None = None) -> Self:
        """Queue a GET command."""
        nkey = self._make_key(key, version)
        self._pipeline.get(nkey)
        self._decoders.append(self._decode_single)
        return self

    def delete(self, key: KeyT, version: int | None = None) -> Self:
        """Queue a DELETE command.

        Note: Returns True if key was deleted, False otherwise.
        For deleting multiple keys, call delete multiple times.
        """
        nkey = self._make_key(key, version)
        self._pipeline.delete(nkey)
        # DEL returns count of deleted keys, convert to bool
        self._decoders.append(lambda x: bool(x))
        return self

    def exists(self, key: KeyT, version: int | None = None) -> Self:
        """Queue an EXISTS command.

        Note: Returns True if key exists, False otherwise.
        For checking multiple keys, call exists multiple times.
        """
        nkey = self._make_key(key, version)
        self._pipeline.exists(nkey)
        # EXISTS returns count, convert to bool
        self._decoders.append(lambda x: bool(x))
        return self

    def expire(
        self,
        key: KeyT,
        timeout: int,
        version: int | None = None,
    ) -> Self:
        """Queue an EXPIRE command."""
        nkey = self._make_key(key, version)
        self._pipeline.expire(nkey, timeout)
        self._decoders.append(self._noop)
        return self

    def ttl(self, key: KeyT, version: int | None = None) -> Self:
        """Queue a TTL command."""
        nkey = self._make_key(key, version)
        self._pipeline.ttl(nkey)
        self._decoders.append(self._noop)
        return self

    def incr(
        self,
        key: KeyT,
        delta: int = 1,
        version: int | None = None,
    ) -> Self:
        """Queue an INCRBY command."""
        nkey = self._make_key(key, version)
        self._pipeline.incrby(nkey, delta)
        self._decoders.append(self._noop)
        return self

    def decr(
        self,
        key: KeyT,
        delta: int = 1,
        version: int | None = None,
    ) -> Self:
        """Queue a DECRBY command."""
        nkey = self._make_key(key, version)
        self._pipeline.decrby(nkey, delta)
        self._decoders.append(self._noop)
        return self
