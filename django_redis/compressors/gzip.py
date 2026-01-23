import gzip

from django_redis.compressors.base import BaseCompressor
from django_redis.exceptions import CompressorError


class GzipCompressor(BaseCompressor):
    def _compress_impl(self, value: bytes) -> bytes:
        return gzip.compress(value)

    def decompress(self, value: bytes) -> bytes:
        try:
            return gzip.decompress(value)
        except gzip.BadGzipFile as e:
            raise CompressorError from e
