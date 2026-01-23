try:
    from compression import zstd
except ImportError:
    from backports import zstd

from django_redis.compressors.base import BaseCompressor
from django_redis.exceptions import CompressorError


class ZStdCompressor(BaseCompressor):
    def _compress_impl(self, value: bytes) -> bytes:
        return zstd.compress(value)

    def decompress(self, value: bytes) -> bytes:
        try:
            return zstd.decompress(value)
        except zstd.ZstdError as e:
            raise CompressorError from e
