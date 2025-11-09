"""Valkey client using valkey-py (fork of redis-py)."""

import importlib.util
from typing import Any

from django.core.cache.backends.base import BaseCache
from django.core.exceptions import ImproperlyConfigured

from django_redis.client.default import DefaultClient


class DefaultValkeyClient(DefaultClient):
    """Valkey client using valkey-py."""

    def __init__(self, server, params: dict[str, Any], backend: BaseCache) -> None:
        if importlib.util.find_spec("valkey") is None:
            msg = "valkey-py required. Install: pip install valkey"
            raise ImproperlyConfigured(msg)

        if "OPTIONS" not in params:
            params["OPTIONS"] = {}

        params["OPTIONS"].setdefault(
            "CONNECTION_FACTORY",
            "django_redis.pool.ValkeyConnectionFactory",
        )

        super().__init__(server, params, backend)
