"""Type aliases for django-redis.

These types are designed to be compatible with:
- Django's cache backend types (django-stubs)
- redis-py's type system
- Our internal API
"""

from datetime import timedelta
from typing import Any, Protocol, TypeVar

# Key types - compatible with redis-py's KeyT and Django's _Key
type KeyT = str | bytes | memoryview

# Expiry/timeout types
type TimeoutT = float | int | timedelta | None

# Value types for cache operations
CacheValueT = TypeVar("CacheValueT")

# Encoded value type (after serialization)
type EncodedT = bytes | int


class SerializerProtocol(Protocol):
    """Protocol for cache value serializers."""

    def dumps(self, value: Any) -> bytes:
        """Serialize a value to bytes."""
        ...

    def loads(self, value: bytes) -> Any:
        """Deserialize bytes to a value."""
        ...


class CompressorProtocol(Protocol):
    """Protocol for cache value compressors."""

    min_length: int

    def compress(self, value: bytes) -> bytes:
        """Compress bytes."""
        ...

    def decompress(self, value: bytes) -> bytes:
        """Decompress bytes."""
        ...
