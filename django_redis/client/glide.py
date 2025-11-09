"""GLIDE client PoC - Rust-based high-performance client for Redis/Valkey."""

import importlib.util
from typing import Any

from django.core.cache.backends.base import BaseCache
from django.core.exceptions import ImproperlyConfigured

from django_redis.client.default import DefaultClient


class GlideClient(DefaultClient):
    """
    Valkey GLIDE client using valkey-glide (Rust-based, high-performance).

    Example configuration:
        CACHES = {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": "redis://user:pass@127.0.0.1:6379/1",
                "OPTIONS": {
                    "CLIENT_CLASS": "django_redis.client.glide.GlideClient",
                    "CLIENT_CLASS_CONFIG": {
                        "client_type": "standalone",  # or "cluster"
                        "request_timeout": 500,
                    },
                },
            },
        }

    LOCATION is parsed for addresses, database_id, credentials, and TLS.
    CLIENT_CLASS_CONFIG can override LOCATION values.
    """

    def __init__(self, server, params: dict[str, Any], backend: BaseCache) -> None:
        if importlib.util.find_spec("glide") is None:
            msg = "valkey-glide required. Install: pip install valkey-glide"
            raise ImproperlyConfigured(msg)

        # Import GLIDE components
        try:
            from glide import (
                BackoffStrategy,
                GlideClientConfiguration,
                GlideClusterClient,
                GlideClusterClientConfiguration,
                NodeAddress,
                ServerCredentials,
            )
            from glide import (
                GlideClient as GlideStandaloneClient,
            )

            self._GlideStandaloneClient = GlideStandaloneClient
            self._GlideClusterClient = GlideClusterClient
            self._GlideClientConfiguration = GlideClientConfiguration
            self._GlideClusterClientConfiguration = GlideClusterClientConfiguration
            self._NodeAddress = NodeAddress
            self._ServerCredentials = ServerCredentials
            self._BackoffStrategy = BackoffStrategy
        except ImportError as e:
            msg = f"Failed to import GLIDE components: {e}"
            raise ImproperlyConfigured(msg) from e

        self._glide_config = params.get("OPTIONS", {}).get("CLIENT_CLASS_CONFIG", {})
        if not self._glide_config:
            msg = "CLIENT_CLASS_CONFIG required for GlideClient"
            raise ImproperlyConfigured(msg)

        super().__init__(server, params, backend)
        self._glide_client = None

    def _parse_location_string(self) -> dict:  # noqa: C901
        """Parse LOCATION to extract addresses, database_id, credentials, use_tls."""
        from contextlib import suppress
        from urllib.parse import parse_qs, urlparse

        result = {
            "addresses": [],
            "database_id": 0,
            "credentials": None,
            "use_tls": False,
        }

        if isinstance(self._server, (list, tuple)):
            servers = self._server
        else:
            servers = [self._server]

        for server_url in servers:
            if isinstance(server_url, str):
                parsed = urlparse(server_url)
                host = parsed.hostname or "127.0.0.1"
                port = parsed.port or 6379
                result["addresses"].append(self._NodeAddress(host, port))

                if not result["use_tls"] and parsed.scheme == "rediss":
                    result["use_tls"] = True

                if result["database_id"] == 0:
                    if parsed.path and len(parsed.path) > 1:
                        with suppress(ValueError):
                            result["database_id"] = int(parsed.path.lstrip("/"))

                    if result["database_id"] == 0 and parsed.query:
                        query_params = parse_qs(parsed.query)
                        if "db" in query_params:
                            with suppress(ValueError, IndexError):
                                result["database_id"] = int(query_params["db"][0])

                if result["credentials"] is None:
                    username = parsed.username
                    password = parsed.password
                    if username or password:
                        result["credentials"] = {
                            "username": username,
                            "password": password,
                        }

        return result

    def _build_glide_config(self) -> Any:
        """Build GLIDE configuration from LOCATION and CLIENT_CLASS_CONFIG."""
        config = self._glide_config.copy()
        client_type = config.pop("client_type", "standalone")
        location_config = self._parse_location_string()

        # Build addresses
        addresses = []
        for addr in config.pop("addresses", []):
            if isinstance(addr, dict):
                host = addr.get("host", "127.0.0.1")
                port = addr.get("port", 6379)
                addresses.append(self._NodeAddress(host, port))
            else:
                addresses.append(addr)

        if not addresses:
            addresses = location_config.get("addresses", [])

        # Build credentials
        credentials = None
        creds_config = config.pop("credentials", None)
        if creds_config:
            credentials = self._ServerCredentials(
                username=creds_config.get("username"),
                password=creds_config.get("password"),
            )
        elif location_config.get("credentials"):
            creds = location_config["credentials"]
            credentials = self._ServerCredentials(
                username=creds.get("username"),
                password=creds.get("password"),
            )

        # Build reconnect strategy
        reconnect_strategy = None
        reconnect_config = config.pop("reconnect_strategy", None)
        if reconnect_config:
            reconnect_strategy = self._BackoffStrategy(
                num_of_retries=reconnect_config.get("num_of_retries", 5),
                factor=reconnect_config.get("factor", 1000),
                exponent_base=reconnect_config.get("exponent_base", 2),
            )

        use_tls = config.get("use_tls", location_config.get("use_tls", False))
        database_id = config.get("database_id", location_config.get("database_id", 0))

        # Build configuration
        if client_type == "cluster":
            excluded = ["use_tls", "request_timeout"]
            extra = {k: v for k, v in config.items() if k not in excluded}
            return self._GlideClusterClientConfiguration(
                addresses=addresses,
                use_tls=use_tls,
                credentials=credentials,
                reconnect_strategy=reconnect_strategy,
                request_timeout=config.get("request_timeout"),
                **extra,
            )

        excluded = ["use_tls", "database_id", "request_timeout"]
        extra = {k: v for k, v in config.items() if k not in excluded}
        return self._GlideClientConfiguration(
            addresses=addresses,
            use_tls=use_tls,
            database_id=database_id,
            credentials=credentials,
            reconnect_strategy=reconnect_strategy,
            request_timeout=config.get("request_timeout"),
            **extra,
        )

    def connect(self, index: int = 0):
        """Connect to GLIDE server."""
        if self._glide_client is None:
            config = self._build_glide_config()
            client_type = self._glide_config.get("client_type", "standalone")
            self._glide_client = (
                self._GlideClusterClient(config)
                if client_type == "cluster"
                else self._GlideStandaloneClient(config)
            )
        return self._glide_client

    def get_client(self, write: bool = True, tried: list | None = None):
        """Get GLIDE client instance."""
        if self._glide_client is None:
            self._glide_client = self.connect()
        return self._glide_client

    def disconnect(self, index: int = 0, client: Any | None = None) -> None:
        """Disconnect GLIDE client."""
        from contextlib import suppress

        if self._glide_client is not None:
            with suppress(Exception):
                self._glide_client.close()
            self._glide_client = None

    # Note: Additional cache methods (set, get, delete, etc.) would need to be
    # implemented to adapt GLIDE's API to django-redis's interface.
    # This is a minimal PoC showing the configuration and connection handling.
