import zlib

from django_redis.compressors.base import BaseCompressor
from django_redis.exceptions import CompressorError


class ZlibCompressor(BaseCompressor):
    min_length = 15
    preset = 6
    # Zlib magic bytes: 78 01 (no compression), 78 9c (default), 78 da (best)
    _magic = (b"\x78\x01", b"\x78\x9c", b"\x78\xda")

    def compress(self, value: bytes) -> bytes:
        if len(value) > self.min_length:
            return zlib.compress(value, self.preset)
        return value

    def decompress(self, value: bytes) -> bytes:
        try:
            return zlib.decompress(value)
        except zlib.error as e:
            raise CompressorError from e

    def check(self, value: bytes) -> bool:
        return any(value.startswith(m) for m in self._magic)
