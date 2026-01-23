class BaseCompressor:
    min_length = 256

    def __init__(self, options):
        self._options = options

    def compress(self, value: bytes) -> bytes:
        if len(value) > self.min_length:
            return self._compress_impl(value)
        return value

    def _compress_impl(self, value: bytes) -> bytes:
        raise NotImplementedError

    def decompress(self, value: bytes) -> bytes:
        raise NotImplementedError
