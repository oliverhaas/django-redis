"""Test fixtures for django-redis."""

from tests.fixtures.cache import (
    cache,
    client_class,
    compressors,
    sentinel_mode,
    serializers,
)
from tests.fixtures.containers import (
    cluster_container,
    cluster_container_factory,
    redis_container,
    redis_container_factory,
    redis_images,
    sentinel_container,
    sentinel_container_factory,
)
from tests.fixtures.settings import settings

__all__ = [
    "cache",
    "client_class",
    "cluster_container",
    "cluster_container_factory",
    "compressors",
    "redis_container",
    "redis_container_factory",
    "redis_images",
    "sentinel_container",
    "sentinel_container_factory",
    "sentinel_mode",
    "serializers",
    "settings",
]
