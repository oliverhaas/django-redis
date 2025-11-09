"""
GLIDE client implementation for django-redis.

This module provides a GlideClient that uses valkey-glide instead of redis-py.
GLIDE is a high-performance Rust-based client library that supports both Redis
and Valkey servers, with optimized performance for cluster and standalone modes.

Unlike redis-py and valkey-py, GLIDE has a different API and requires explicit
configuration objects. This client bridges the django-redis API to GLIDE's API.
"""

import importlib.util
from collections import OrderedDict
from collections.abc import Iterable
from typing import Any, Optional

from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.core.exceptions import ImproperlyConfigured
from redis.typing import EncodableT, KeyT

from django_redis.client.default import DefaultClient
from django_redis.exceptions import ConnectionInterrupted


class GlideClient(DefaultClient):
    """
    GLIDE client implementation for django-redis.

    This client uses valkey-glide, a high-performance Rust-based client library.

    LOCATION string is parsed to extract connection details (addresses, database_id,
    credentials, TLS settings). CLIENT_CLASS_CONFIG can override any of these values
    and provides additional GLIDE-specific configuration.

    Basic configuration (using LOCATION):
        CACHES = {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": "redis://user:pass@127.0.0.1:6379/1",
                "OPTIONS": {
                    "CLIENT_CLASS": "django_redis.client.glide.GlideClient",
                    "CLIENT_CLASS_CONFIG": {
                        "client_type": "standalone",  # or "cluster"
                        "request_timeout": 500,  # milliseconds
                    },
                },
            },
        }

    Advanced configuration (overriding LOCATION):
        CACHES = {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": "redis://127.0.0.1:6379/1",  # Provides defaults
                "OPTIONS": {
                    "CLIENT_CLASS": "django_redis.client.glide.GlideClient",
                    "CLIENT_CLASS_CONFIG": {
                        "client_type": "standalone",
                        # Override addresses from LOCATION
                        "addresses": [
                            {"host": "primary.example.com", "port": 6379},
                            {"host": "replica.example.com", "port": 6379},
                        ],
                        "request_timeout": 500,
                        "database_id": 2,  # Override from LOCATION
                        "use_tls": True,  # Override from LOCATION
                        "credentials": {  # Override from LOCATION
                            "username": "admin",
                            "password": "secret",
                        },
                        "reconnect_strategy": {
                            "num_of_retries": 5,
                            "factor": 1000,
                            "exponent_base": 2,
                        },
                    },
                },
            },
        }

    LOCATION parsing extracts:
    - addresses: from host:port
    - database_id: from URL path (/1) or query param (?db=1)
    - credentials: from username:password in URL
    - use_tls: from rediss:// scheme

    CLIENT_CLASS_CONFIG parameters map directly to GLIDE's API and override LOCATION.
    """

    def __init__(self, server, params: dict[str, Any], backend: BaseCache) -> None:
        """
        Initialize the GLIDE client.

        Validates that valkey-glide is installed and parses the configuration
        from CLIENT_CLASS_CONFIG.
        """
        if importlib.util.find_spec("glide") is None:
            error_message = (
                "valkey-glide is required to use GlideClient. "
                "Install it with: pip install valkey-glide"
            )
            raise ImproperlyConfigured(error_message)

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
            error_message = (
                f"Failed to import GLIDE components: {e}. "
                "Make sure valkey-glide is properly installed."
            )
            raise ImproperlyConfigured(error_message) from e

        # Store configuration before calling parent __init__
        self._glide_config = params.get("OPTIONS", {}).get("CLIENT_CLASS_CONFIG", {})

        if not self._glide_config:
            error_message = (
                "CLIENT_CLASS_CONFIG is required for GlideClient. "
                "See django_redis.client.glide.GlideClient docstring for examples."
            )
            raise ImproperlyConfigured(error_message)

        # Initialize parent (this sets up serializers, compressors, etc.)
        # Note: We don't use the standard connection factory for GLIDE
        super().__init__(server, params, backend)

        # GLIDE clients - these will be created lazily
        self._glide_client: Optional[Any] = None

    def _build_glide_config(self) -> Any:
        """
        Build GLIDE configuration from CLIENT_CLASS_CONFIG and LOCATION.

        LOCATION string is parsed to extract:
        - addresses (host:port)
        - database_id (from URL path or db query parameter)
        - credentials (username:password from URL)
        - use_tls (from rediss:// scheme)

        CLIENT_CLASS_CONFIG can override any of these values.

        Returns:
            GlideClientConfiguration or GlideClusterClientConfiguration
        """
        config = self._glide_config.copy()
        client_type = config.pop("client_type", "standalone")

        # Parse LOCATION string to get defaults
        location_config = self._parse_location_string()

        # Build addresses - use CLIENT_CLASS_CONFIG if provided, else LOCATION
        addresses = []
        for addr in config.pop("addresses", []):
            if isinstance(addr, dict):
                host = addr.get("host", "127.0.0.1")
                port = addr.get("port", 6379)
                addresses.append(self._NodeAddress(host, port))
            else:
                # Assume it's already a NodeAddress
                addresses.append(addr)

        if not addresses:
            # Use addresses from LOCATION
            addresses = location_config.get("addresses", [])

        # Build credentials - use CLIENT_CLASS_CONFIG if provided, else LOCATION
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

        # Build reconnect strategy if provided
        reconnect_strategy = None
        reconnect_config = config.pop("reconnect_strategy", None)
        if reconnect_config:
            reconnect_strategy = self._BackoffStrategy(
                num_of_retries=reconnect_config.get("num_of_retries", 5),
                factor=reconnect_config.get("factor", 1000),
                exponent_base=reconnect_config.get("exponent_base", 2),
            )

        # Get TLS setting - CLIENT_CLASS_CONFIG overrides LOCATION
        use_tls = config.get("use_tls", location_config.get("use_tls", False))

        # Get database_id - CLIENT_CLASS_CONFIG overrides LOCATION
        database_id = config.get("database_id", location_config.get("database_id", 0))

        # Build configuration object
        if client_type == "cluster":
            excluded_keys = ["use_tls", "request_timeout"]
            extra_config = {k: v for k, v in config.items() if k not in excluded_keys}
            return self._GlideClusterClientConfiguration(
                addresses=addresses,
                use_tls=use_tls,
                credentials=credentials,
                reconnect_strategy=reconnect_strategy,
                request_timeout=config.get("request_timeout"),
                **extra_config,
            )
        # standalone
        excluded_keys = ["use_tls", "database_id", "request_timeout"]
        extra_config = {k: v for k, v in config.items() if k not in excluded_keys}
        return self._GlideClientConfiguration(
            addresses=addresses,
            use_tls=use_tls,
            database_id=database_id,
            credentials=credentials,
            reconnect_strategy=reconnect_strategy,
            request_timeout=config.get("request_timeout"),
            **extra_config,
        )

    def _parse_location_string(self) -> dict:  # noqa: C901
        """
        Parse LOCATION string to extract configuration.

        Extracts:
        - addresses: List of NodeAddress objects
        - database_id: From URL path or 'db' query parameter
        - credentials: Username and password from URL
        - use_tls: True if scheme is 'rediss://'

        Returns:
            Dictionary with parsed configuration
        """
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

                # Extract address
                host = parsed.hostname or "127.0.0.1"
                port = parsed.port or 6379
                result["addresses"].append(self._NodeAddress(host, port))

                # Extract TLS setting (from first server URL)
                if not result["use_tls"] and parsed.scheme == "rediss":
                    result["use_tls"] = True

                # Extract database ID (from first server URL)
                if result["database_id"] == 0:
                    # Try path first (e.g., redis://host/1)
                    if parsed.path and len(parsed.path) > 1:
                        with suppress(ValueError):
                            result["database_id"] = int(parsed.path.lstrip("/"))

                    # Try query parameter (e.g., redis://host?db=1)
                    if result["database_id"] == 0 and parsed.query:
                        query_params = parse_qs(parsed.query)
                        if "db" in query_params:
                            with suppress(ValueError, IndexError):
                                result["database_id"] = int(query_params["db"][0])

                # Extract credentials (from first server URL)
                if result["credentials"] is None:
                    username = parsed.username
                    password = parsed.password
                    if username or password:
                        result["credentials"] = {
                            "username": username,
                            "password": password,
                        }

        return result

    def connect(self, index: int = 0):
        """
        Connect to GLIDE server.

        GLIDE uses async by default, but provides sync wrappers.
        We use the sync version for django-redis compatibility.
        """
        if self._glide_client is None:
            config = self._build_glide_config()
            client_type = self._glide_config.get("client_type", "standalone")

            # Create sync client
            if client_type == "cluster":
                self._glide_client = self._GlideClusterClient(config)
            else:
                self._glide_client = self._GlideStandaloneClient(config)

        return self._glide_client

    def get_client(self, write: bool = True, tried: Optional[list[int]] = None):
        """
        Get the GLIDE client instance.

        For GLIDE, we use a single client instance regardless of read/write.
        """
        if self._glide_client is None:
            self._glide_client = self.connect()
        return self._glide_client

    def disconnect(self, index: int = 0, client: Optional[Any] = None) -> None:
        """
        Disconnect the GLIDE client.
        """
        from contextlib import suppress

        if self._glide_client is not None:
            with suppress(Exception):
                self._glide_client.close()
            self._glide_client = None

    def set(
        self,
        key: KeyT,
        value: EncodableT,
        timeout: Optional[float] = DEFAULT_TIMEOUT,
        version: Optional[int] = None,
        client: Optional[Any] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        Set a value with GLIDE.

        GLIDE's set method returns bytes, and we need to handle the response properly.
        """
        nkey = self.make_key(key, version=version)
        nvalue = self.encode(value)

        if timeout is DEFAULT_TIMEOUT:
            timeout = self._backend.default_timeout

        if client is None:
            client = self.get_client(write=True)

        try:
            # GLIDE set options
            set_options = {}

            if nx:
                set_options["conditional_set"] = "onlyIfDoesNotExist"
            elif xx:
                set_options["conditional_set"] = "onlyIfExists"

            if timeout is not None and timeout > 0:
                # GLIDE uses milliseconds
                timeout_ms = int(timeout * 1000)
                set_options["expiry"] = {"type": "milliseconds", "count": timeout_ms}

            result = client.set(nkey, nvalue, **set_options)
            return result is not None
        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

    def get(
        self,
        key: KeyT,
        default: Optional[Any] = None,
        version: Optional[int] = None,
        client: Optional[Any] = None,
    ) -> Any:
        """
        Get a value from GLIDE.
        """
        if client is None:
            client = self.get_client(write=False)

        key = self.make_key(key, version=version)

        try:
            value = client.get(key)
        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

        if value is None:
            return default

        return self.decode(value)

    def delete(
        self,
        key: KeyT,
        version: Optional[int] = None,
        prefix: Optional[str] = None,
        client: Optional[Any] = None,
    ) -> int:
        """
        Delete a key from GLIDE.
        """
        if client is None:
            client = self.get_client(write=True)

        try:
            cache_key = self.make_key(key, version=version, prefix=prefix)
            return int(client.delete([cache_key]))
        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

    def delete_many(
        self,
        keys: Iterable[KeyT],
        version: Optional[int] = None,
        client: Optional[Any] = None,
    ) -> int:
        """
        Delete multiple keys from GLIDE.
        """
        if client is None:
            client = self.get_client(write=True)

        key_list = [self.make_key(k, version=version) for k in keys]

        if not key_list:
            return 0

        try:
            return int(client.delete(key_list))
        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

    def get_many(
        self,
        keys: Iterable[KeyT],
        version: Optional[int] = None,
        client: Optional[Any] = None,
    ) -> OrderedDict:
        """
        Get multiple values from GLIDE.
        """
        if client is None:
            client = self.get_client(write=False)

        if not keys:
            return OrderedDict()

        recovered_data = OrderedDict()
        map_keys = OrderedDict((self.make_key(k, version=version), k) for k in keys)

        try:
            results = client.mget(list(map_keys.keys()))
        except Exception as e:
            raise ConnectionInterrupted(connection=client) from e

        for key, value in zip(map_keys, results):
            if value is None:
                continue
            recovered_data[map_keys[key]] = self.decode(value)

        return recovered_data

    # Note: Additional methods (incr, decr, ttl, etc.) would need similar adaptations
    # for GLIDE's API. This is a starting implementation showing the pattern.
