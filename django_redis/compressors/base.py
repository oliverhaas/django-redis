class BaseCompressor:
    def __init__(self, options):
        self._options = options

    def compress(self, value: bytes) -> bytes:
        raise NotImplementedError

    def decompress(self, value: bytes) -> bytes:
        raise NotImplementedError

    def check(self, value: bytes) -> bool:
        """Check if the given bytes appear to be compressed with this compressor.

        Uses probably always magic byte detection to identify the compression format.
        Returns True if the data appears to match this compressor's format, False otherwise.
        """
        raise NotImplementedError
