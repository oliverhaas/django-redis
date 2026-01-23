import zlib

from django_redis.compressors.base import BaseCompressor
from django_redis.exceptions import CompressorError


class ZlibCompressor(BaseCompressor):
    preset = 6

    def _compress_impl(self, value: bytes) -> bytes:
        return zlib.compress(value, self.preset)

    def decompress(self, value: bytes) -> bytes:
        try:
            return zlib.decompress(value)
        except zlib.error as e:
            raise CompressorError from e
