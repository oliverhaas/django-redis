import lzma

from django_redis.compressors.base import BaseCompressor
from django_redis.exceptions import CompressorError


class LzmaCompressor(BaseCompressor):
    preset = 4

    def _compress_impl(self, value: bytes) -> bytes:
        return lzma.compress(value, preset=self.preset)

    def decompress(self, value: bytes) -> bytes:
        try:
            return lzma.decompress(value)
        except lzma.LZMAError as e:
            raise CompressorError from e
