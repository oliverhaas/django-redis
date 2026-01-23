import pickle
from typing import Any

from django.core.exceptions import ImproperlyConfigured

from django_redis.exceptions import SerializerError
from django_redis.serializers.base import BaseSerializer


class PickleSerializer(BaseSerializer):
    def __init__(self, options) -> None:
        self._pickle_version = pickle.DEFAULT_PROTOCOL
        self.setup_pickle_version(options)

        super().__init__(options=options)

    def setup_pickle_version(self, options) -> None:
        if "PICKLE_VERSION" in options:
            try:
                self._pickle_version = int(options["PICKLE_VERSION"])
                if self._pickle_version > pickle.HIGHEST_PROTOCOL:
                    error_message = (
                        f"PICKLE_VERSION can't be higher than pickle.HIGHEST_PROTOCOL: {pickle.HIGHEST_PROTOCOL}"
                    )
                    raise ImproperlyConfigured(error_message)
            except (ValueError, TypeError) as e:
                error_message = "PICKLE_VERSION value must be an integer"
                raise ImproperlyConfigured(error_message) from e

    def dumps(self, value: Any) -> bytes:
        return pickle.dumps(value, self._pickle_version)

    def loads(self, value: bytes) -> Any:
        try:
            return pickle.loads(value)
        except Exception as e:
            raise SerializerError from e
