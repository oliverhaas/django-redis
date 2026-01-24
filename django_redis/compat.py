"""Utilities for serializer/compressor instantiation."""

from __future__ import annotations

from typing import Any

from django.utils.module_loading import import_string


def is_serializer_instance(obj: Any) -> bool:
    """Check if an object is a serializer instance (has dumps/loads methods)."""
    if isinstance(obj, type):
        return False
    return hasattr(obj, "dumps") and hasattr(obj, "loads") and callable(obj.dumps) and callable(obj.loads)


def is_compressor_instance(obj: Any) -> bool:
    """Check if an object is a compressor instance (has compress/decompress methods)."""
    if isinstance(obj, type):
        return False
    return (
        hasattr(obj, "compress")
        and hasattr(obj, "decompress")
        and callable(obj.compress)
        and callable(obj.decompress)
    )


def create_serializer(config: str | type | Any, options: dict | None = None) -> Any:
    """Create a serializer instance from config.

    Args:
        config: A dotted path string, a class, or an instance
        options: Optional options dict to pass to serializer constructor
    """
    # Already an instance
    if is_serializer_instance(config):
        return config

    # Default to empty dict if None
    if options is None:
        options = {}

    # A class (not a string path)
    if isinstance(config, type):
        try:
            # Try with options first (django-redis-ng serializers)
            return config(options=options)
        except TypeError:
            # Fall back to no args (Django's RedisSerializer style)
            return config()

    # Dotted path string
    cls = import_string(config)
    try:
        # Try with options first (django-redis-ng serializers)
        return cls(options=options)
    except TypeError:
        # Fall back to no args (Django's RedisSerializer style)
        return cls()


def create_compressor(config: str | type | Any | None, options: dict | None = None) -> Any:
    """Create a compressor instance from config.

    Args:
        config: A dotted path string, a class, an instance, or None for identity compressor
        options: Optional options dict to pass to compressor constructor
    """
    # None means identity compressor (no compression)
    if config is None:
        config = "django_redis.compressors.identity.IdentityCompressor"

    # Already an instance
    if is_compressor_instance(config):
        return config

    # Compressors always require the options argument (unlike serializers)
    if options is None:
        options = {}

    # A class (not a string path)
    if isinstance(config, type):
        return config(options=options)

    # Dotted path string
    cls = import_string(config)
    return cls(options=options)
