from django_redis.compressors.base import BaseCompressor


class IdentityCompressor(BaseCompressor):
    def compress(self, value: bytes) -> bytes:
        return value

    def decompress(self, value: bytes) -> bytes:
        return value

    def check(self, value: bytes) -> bool:
        # Identity compressor accepts any data (no magic bytes)
        # Should be last in fallback list as a catch-all
        return True
