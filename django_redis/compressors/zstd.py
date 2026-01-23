try:
    from compression import zstd
except ImportError:
    from backports import zstd

from django_redis.compressors.base import BaseCompressor
from django_redis.exceptions import CompressorError


class ZStdCompressor(BaseCompressor):
    min_length = 15
    # Zstd magic bytes: 28 b5 2f fd
    _magic = b"\x28\xb5\x2f\xfd"

    def compress(self, value: bytes) -> bytes:
        if len(value) > self.min_length:
            return zstd.compress(value)
        return value

    def decompress(self, value: bytes) -> bytes:
        try:
            return zstd.decompress(value)
        except zstd.ZstdError as e:
            raise CompressorError from e

    def check(self, value: bytes) -> bool:
        return value.startswith(self._magic)
