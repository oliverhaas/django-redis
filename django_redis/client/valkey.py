"""
Valkey client implementation for django-redis.

This module provides a DefaultValkeyClient that uses valkey-py instead
of redis-py. Since valkey-py is a fork of redis-py with nearly identical
API, most functionality is inherited from DefaultClient.
"""

import importlib.util
from typing import Any, Optional

from django.core.cache.backends.base import BaseCache
from django.core.exceptions import ImproperlyConfigured

from django_redis.client.default import DefaultClient


class DefaultValkeyClient(DefaultClient):
    """
    Default Valkey client implementation using valkey-py.

    This client uses the valkey-py library instead of redis-py.
    Since valkey-py is a fork of redis-py, the API is nearly identical,
    and we can inherit almost all functionality from DefaultClient.

    The main differences are:
    1. Uses ValkeyConnectionFactory instead of ConnectionFactory
    2. Type hints use Valkey client types
    3. Imports come from valkey package instead of redis package
    """

    def __init__(self, server, params: dict[str, Any], backend: BaseCache) -> None:
        """
        Initialize the Valkey client.

        Validates that valkey-py is installed and sets up the connection
        factory to use Valkey instead of Redis.
        """
        if importlib.util.find_spec("valkey") is None:
            error_message = (
                "valkey-py is required to use DefaultValkeyClient. "
                "Install it with: pip install valkey"
            )
            raise ImproperlyConfigured(error_message)

        # Ensure we use ValkeyConnectionFactory
        if "OPTIONS" not in params:
            params["OPTIONS"] = {}

        # Set the connection factory to ValkeyConnectionFactory if not explicitly set
        params["OPTIONS"].setdefault(
            "CONNECTION_FACTORY",
            "django_redis.pool.ValkeyConnectionFactory",
        )

        # Initialize parent class with valkey-specific settings
        super().__init__(server, params, backend)

    def get_client(self, write: bool = True, tried: Optional[list[int]] = None):
        """
        Get a Valkey client instance.

        Returns a valkey.Valkey client instead of redis.Redis.
        """
        return super().get_client(write=write, tried=tried)

    def connect(self, index: int = 0):
        """
        Connect to Valkey server.

        Returns a valkey.Valkey client instance.
        """
        return super().connect(index=index)
