"""Tests for list operations."""

from django_redis.cache import RedisCache


class TestListOperations:
    def test_lpush_rpush(self, cache: RedisCache):
        # lpush adds to head
        cache.lpush("mylist", "world")
        cache.lpush("mylist", "hello")
        # rpush adds to tail
        cache.rpush("mylist", "!")

        result = cache.lrange("mylist", 0, -1)
        assert result == ["hello", "world", "!"]

    def test_lpush_multiple(self, cache: RedisCache):
        count = cache.lpush("mylist2", "a", "b", "c")
        assert count == 3
        # When pushing multiple, they're pushed in order, so last one ends up at head
        result = cache.lrange("mylist2", 0, -1)
        assert result == ["c", "b", "a"]

    def test_rpush_multiple(self, cache: RedisCache):
        count = cache.rpush("mylist3", "a", "b", "c")
        assert count == 3
        result = cache.lrange("mylist3", 0, -1)
        assert result == ["a", "b", "c"]

    def test_lpop(self, cache: RedisCache):
        cache.rpush("mylist4", "a", "b", "c")

        # Pop single element from head
        result = cache.lpop("mylist4")
        assert result == "a"

        # Pop multiple elements
        result = cache.lpop("mylist4", count=2)
        assert result == ["b", "c"]

        # Pop from empty list
        result = cache.lpop("mylist4")
        assert result is None

    def test_rpop(self, cache: RedisCache):
        cache.rpush("mylist5", "a", "b", "c")

        # Pop single element from tail
        result = cache.rpop("mylist5")
        assert result == "c"

        # Pop multiple elements
        result = cache.rpop("mylist5", count=2)
        assert result == ["b", "a"]

        # Pop from empty list
        result = cache.rpop("mylist5")
        assert result is None

    def test_lrange(self, cache: RedisCache):
        cache.rpush("mylist6", "a", "b", "c", "d", "e")

        # Get all elements
        assert cache.lrange("mylist6", 0, -1) == ["a", "b", "c", "d", "e"]

        # Get first 3
        assert cache.lrange("mylist6", 0, 2) == ["a", "b", "c"]

        # Get last 2
        assert cache.lrange("mylist6", -2, -1) == ["d", "e"]

        # Empty range
        assert cache.lrange("nonexistent", 0, -1) == []

    def test_lindex(self, cache: RedisCache):
        cache.rpush("mylist7", "a", "b", "c")

        assert cache.lindex("mylist7", 0) == "a"
        assert cache.lindex("mylist7", 1) == "b"
        assert cache.lindex("mylist7", -1) == "c"
        assert cache.lindex("mylist7", 100) is None
        assert cache.lindex("nonexistent", 0) is None

    def test_llen(self, cache: RedisCache):
        assert cache.llen("mylist8") == 0

        cache.rpush("mylist8", "a", "b", "c")
        assert cache.llen("mylist8") == 3

    def test_lrem(self, cache: RedisCache):
        cache.rpush("mylist9", "a", "b", "a", "c", "a")

        # Remove 2 occurrences from head
        removed = cache.lrem("mylist9", 2, "a")
        assert removed == 2
        assert cache.lrange("mylist9", 0, -1) == ["b", "c", "a"]

    def test_lrem_from_tail(self, cache: RedisCache):
        cache.rpush("mylist10", "a", "b", "a", "c", "a")

        # Remove 2 occurrences from tail (negative count)
        removed = cache.lrem("mylist10", -2, "a")
        assert removed == 2
        assert cache.lrange("mylist10", 0, -1) == ["a", "b", "c"]

    def test_lrem_all(self, cache: RedisCache):
        cache.rpush("mylist11", "a", "b", "a", "c", "a")

        # Remove all occurrences (count=0)
        removed = cache.lrem("mylist11", 0, "a")
        assert removed == 3
        assert cache.lrange("mylist11", 0, -1) == ["b", "c"]

    def test_ltrim(self, cache: RedisCache):
        cache.rpush("mylist12", "a", "b", "c", "d", "e")

        result = cache.ltrim("mylist12", 1, 3)
        assert result is True
        assert cache.lrange("mylist12", 0, -1) == ["b", "c", "d"]

    def test_lset(self, cache: RedisCache):
        cache.rpush("mylist13", "a", "b", "c")

        result = cache.lset("mylist13", 1, "B")
        assert result is True
        assert cache.lrange("mylist13", 0, -1) == ["a", "B", "c"]

    def test_linsert(self, cache: RedisCache):
        cache.rpush("mylist14", "a", "c")

        # Insert before
        length = cache.linsert("mylist14", "BEFORE", "c", "b")
        assert length == 3
        assert cache.lrange("mylist14", 0, -1) == ["a", "b", "c"]

        # Insert after
        length = cache.linsert("mylist14", "AFTER", "c", "d")
        assert length == 4
        assert cache.lrange("mylist14", 0, -1) == ["a", "b", "c", "d"]

        # Pivot not found
        length = cache.linsert("mylist14", "BEFORE", "z", "x")
        assert length == -1

    def test_list_with_complex_values(self, cache: RedisCache):
        """Test that lists work with complex serialized values."""
        cache.rpush("mylist15", {"name": "Alice"}, {"name": "Bob"})

        result = cache.lrange("mylist15", 0, -1)
        assert result == [{"name": "Alice"}, {"name": "Bob"}]

        popped = cache.lpop("mylist15")
        assert popped == {"name": "Alice"}

    def test_list_version_support(self, cache: RedisCache):
        """Test that version parameter works correctly."""
        cache.rpush("mylist", "v1_a", "v1_b", version=1)
        cache.rpush("mylist", "v2_a", version=2)

        assert cache.llen("mylist", version=1) == 2
        assert cache.llen("mylist", version=2) == 1

        assert cache.lrange("mylist", 0, -1, version=1) == ["v1_a", "v1_b"]
        assert cache.lrange("mylist", 0, -1, version=2) == ["v2_a"]
