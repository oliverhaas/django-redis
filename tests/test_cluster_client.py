"""Tests for ClusterClient and ClusterConnectionFactory."""

from unittest.mock import MagicMock, patch

import pytest

from django_redis.client.cluster import ClusterClient
from django_redis.pool import ClusterConnectionFactory


class TestClusterConnectionFactory:
    """Tests for ClusterConnectionFactory."""

    def setup_method(self):
        """Clear the cluster cache before each test."""
        ClusterConnectionFactory._clusters.clear()

    def test_init(self):
        """Test factory initialization."""
        options = {"PASSWORD": "secret", "SOCKET_TIMEOUT": 10}
        factory = ClusterConnectionFactory(options)

        assert factory.options == options
        assert factory.redis_client_cls_kwargs == {}

    def test_init_with_client_kwargs(self):
        """Test factory initialization with client kwargs."""
        options = {"REDIS_CLIENT_KWARGS": {"decode_responses": True}}
        factory = ClusterConnectionFactory(options)

        assert factory.redis_client_cls_kwargs == {"decode_responses": True}

    def test_make_connection_params_basic(self):
        """Test basic connection params from URL."""
        factory = ClusterConnectionFactory({})
        params = factory.make_connection_params("redis://localhost:7000")

        assert params["host"] == "localhost"
        assert params["port"] == 7000

    def test_make_connection_params_with_password(self):
        """Test connection params include password from options."""
        factory = ClusterConnectionFactory({"PASSWORD": "secret123"})
        params = factory.make_connection_params("redis://localhost:7000")

        assert params["password"] == "secret123"  # noqa: S105

    def test_make_connection_params_with_timeouts(self):
        """Test connection params include timeout settings."""
        factory = ClusterConnectionFactory(
            {
                "SOCKET_TIMEOUT": 5.0,
                "SOCKET_CONNECT_TIMEOUT": 3.0,
            },
        )
        params = factory.make_connection_params("redis://localhost:7000")

        assert params["socket_timeout"] == 5.0
        assert params["socket_connect_timeout"] == 3.0

    def test_make_connection_params_invalid_timeout(self):
        """Test that invalid timeout raises error."""
        from django.core.exceptions import ImproperlyConfigured

        factory = ClusterConnectionFactory({"SOCKET_TIMEOUT": "invalid"})

        with pytest.raises(ImproperlyConfigured):
            factory.make_connection_params("redis://localhost:7000")

    @patch("django_redis.pool.RedisCluster")
    def test_connect_creates_cluster(self, mock_cluster_cls):
        """Test connect creates a RedisCluster instance."""
        mock_cluster = MagicMock()
        mock_cluster_cls.return_value = mock_cluster

        factory = ClusterConnectionFactory({})
        result = factory.connect("redis://localhost:7000")

        assert result == mock_cluster
        mock_cluster_cls.assert_called_once()

    @patch("django_redis.pool.RedisCluster")
    def test_connect_caches_cluster(self, mock_cluster_cls):
        """Test connect caches cluster instances."""
        mock_cluster = MagicMock()
        mock_cluster_cls.return_value = mock_cluster

        factory = ClusterConnectionFactory({})
        result1 = factory.connect("redis://localhost:7000")
        result2 = factory.connect("redis://localhost:7000")

        assert result1 is result2
        assert mock_cluster_cls.call_count == 1

    def test_disconnect(self):
        """Test disconnect calls close on cluster."""
        mock_cluster = MagicMock()
        factory = ClusterConnectionFactory({})

        factory.disconnect(mock_cluster)

        mock_cluster.close.assert_called_once()


class TestClusterClient:
    """Tests for ClusterClient."""

    @patch("django_redis.pool.get_connection_factory")
    def test_init(self, mock_get_factory):
        """Test ClusterClient initialization."""
        mock_factory = MagicMock()
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: f"{p}:{v}:{k}"

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        # Cluster client always has single client slot
        assert len(client._clients) == 1

    @patch("django_redis.pool.get_connection_factory")
    def test_get_next_client_index_always_zero(self, mock_get_factory):
        """Test that get_next_client_index always returns 0 for cluster."""
        mock_factory = MagicMock()
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: f"{p}:{v}:{k}"

        client = ClusterClient(
            server=["redis://localhost:7000", "redis://localhost:7001"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        # Should always return 0 regardless of write flag or tried list
        assert client.get_next_client_index(write=True) == 0
        assert client.get_next_client_index(write=False) == 0
        assert client.get_next_client_index(write=True, tried=[0]) == 0

    @patch("django_redis.pool.get_connection_factory")
    def test_get_client(self, mock_get_factory):
        """Test get_client returns cluster connection."""
        mock_cluster = MagicMock()
        mock_factory = MagicMock()
        mock_factory.connect.return_value = mock_cluster
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: f"{p}:{v}:{k}"

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        result = client.get_client()

        assert result == mock_cluster
        mock_factory.connect.assert_called_once_with("redis://localhost:7000")

    @patch("django_redis.pool.get_connection_factory")
    def test_get_client_caches_connection(self, mock_get_factory):
        """Test get_client caches the connection."""
        mock_cluster = MagicMock()
        mock_factory = MagicMock()
        mock_factory.connect.return_value = mock_cluster
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: f"{p}:{v}:{k}"

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        result1 = client.get_client()
        result2 = client.get_client()

        assert result1 is result2
        assert mock_factory.connect.call_count == 1

    @patch("django_redis.pool.get_connection_factory")
    def test_do_close_clients(self, mock_get_factory):
        """Test do_close_clients closes the cluster connection."""
        mock_cluster = MagicMock()
        mock_factory = MagicMock()
        mock_factory.connect.return_value = mock_cluster
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: f"{p}:{v}:{k}"

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        # Connect first
        client.get_client()

        # Close
        client.do_close_clients()

        mock_cluster.close.assert_called_once()
        assert client._clients == [None]

    @patch("django_redis.pool.get_connection_factory")
    def test_group_keys_by_slot(self, mock_get_factory):
        """Test _group_keys_by_slot groups keys correctly."""
        mock_factory = MagicMock()
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: f"{p}:{v}:{k}"

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        # Keys with same hash tag should be in same slot
        keys = ["{user}:1", "{user}:2", "{user}:3"]
        slots = client._group_keys_by_slot(keys)

        # All keys with {user} hash tag should be in the same slot
        assert len(slots) == 1
        slot_keys = list(slots.values())[0]
        assert len(slot_keys) == 3

    @patch("django_redis.pool.get_connection_factory")
    def test_group_keys_by_slot_different_slots(self, mock_get_factory):
        """Test _group_keys_by_slot separates keys in different slots."""
        mock_factory = MagicMock()
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: f"{p}:{v}:{k}"

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        # Keys without hash tags will likely be in different slots
        keys = ["key1", "key2", "key3", "key4", "key5"]
        slots = client._group_keys_by_slot(keys)

        # Should have multiple slots (statistically very likely)
        # At minimum, check the grouping works
        total_keys = sum(len(v) for v in slots.values())
        assert total_keys == 5

    @patch("django_redis.pool.get_connection_factory")
    def test_get_many_groups_by_slot(self, mock_get_factory):
        """Test get_many handles cross-slot keys."""
        import pickle

        mock_cluster = MagicMock()
        mock_factory = MagicMock()
        mock_factory.connect.return_value = mock_cluster
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: k  # Simple key function

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        # Mock get/mget responses with pickled data
        mock_cluster.get.return_value = pickle.dumps("value1")
        mock_cluster.mget.return_value = [pickle.dumps("value2"), pickle.dumps("value3")]

        # Using hash tags to control slot grouping
        result = client.get_many(["{a}key1", "{b}key2", "{b}key3"])

        # Should return decoded values
        assert len(result) == 3
        assert "value1" in result.values()
        assert "value2" in result.values()
        assert "value3" in result.values()

    @patch("django_redis.pool.get_connection_factory")
    def test_get_many_empty_keys(self, mock_get_factory):
        """Test get_many with empty keys list."""
        mock_factory = MagicMock()
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: k

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        result = client.get_many([])
        assert result == {}

    @patch("django_redis.pool.get_connection_factory")
    def test_delete_many_groups_by_slot(self, mock_get_factory):
        """Test delete_many handles cross-slot keys."""
        mock_cluster = MagicMock()
        mock_factory = MagicMock()
        mock_factory.connect.return_value = mock_cluster
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: k

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        # Mock delete to return count of deleted keys
        mock_cluster.delete.return_value = 2

        result = client.delete_many(["{a}key1", "{b}key2", "{b}key3"])

        # delete called for each slot group
        assert mock_cluster.delete.called
        assert result >= 0

    @patch("django_redis.pool.get_connection_factory")
    def test_delete_many_empty_keys(self, mock_get_factory):
        """Test delete_many with empty keys list."""
        mock_factory = MagicMock()
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: k

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        result = client.delete_many([])
        assert result == 0

    @patch("django_redis.pool.get_connection_factory")
    def test_set_many(self, mock_get_factory):
        """Test set_many sets values individually."""
        mock_cluster = MagicMock()
        mock_factory = MagicMock()
        mock_factory.connect.return_value = mock_cluster
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.default_timeout = 300
        mock_backend.key_func = lambda k, p, v: k

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        mock_cluster.set.return_value = True

        client.set_many({"key1": "value1", "key2": "value2"})

        # Should call set for each key
        assert mock_cluster.set.call_count == 2

    @patch("django_redis.pool.get_connection_factory")
    def test_clear_flushes_all_primaries(self, mock_get_factory):
        """Test clear flushes all primary nodes."""
        from redis.cluster import RedisCluster

        mock_cluster = MagicMock()
        mock_factory = MagicMock()
        mock_factory.connect.return_value = mock_cluster
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: k

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        client.clear()

        # Should call flushdb with target_nodes=PRIMARIES
        mock_cluster.flushdb.assert_called_once_with(target_nodes=RedisCluster.PRIMARIES)
