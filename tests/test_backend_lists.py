from django_redis.cache import RedisCache


class TestListOperations:
    """Tests for Redis list operations."""

    def test_lpush_basic(self, cache: RedisCache):
        """Test pushing values to the head of a list."""
        result = cache.lpush("mylist", "world")
        assert result == 1
        result = cache.lpush("mylist", "hello")
        assert result == 2
        assert cache.llen("mylist") == 2

    def test_rpush_basic(self, cache: RedisCache):
        """Test pushing values to the tail of a list."""
        result = cache.rpush("mylist", "hello")
        assert result == 1
        result = cache.rpush("mylist", "world")
        assert result == 2
        assert cache.llen("mylist") == 2

    def test_lpush_multiple(self, cache: RedisCache):
        """Test pushing multiple values at once."""
        result = cache.lpush("mylist", "a", "b", "c")
        assert result == 3

    def test_rpush_multiple(self, cache: RedisCache):
        """Test pushing multiple values at once."""
        result = cache.rpush("mylist", "a", "b", "c")
        assert result == 3

    def test_lpop_single(self, cache: RedisCache):
        """Test popping a single value from the head."""
        cache.rpush("mylist", "a", "b", "c")
        result = cache.lpop("mylist")
        assert result == "a"
        assert cache.llen("mylist") == 2

    def test_rpop_single(self, cache: RedisCache):
        """Test popping a single value from the tail."""
        cache.rpush("mylist", "a", "b", "c")
        result = cache.rpop("mylist")
        assert result == "c"
        assert cache.llen("mylist") == 2

    def test_lpop_multiple(self, cache: RedisCache):
        """Test popping multiple values from the head."""
        cache.rpush("mylist", "a", "b", "c", "d")
        result = cache.lpop("mylist", count=2)
        assert result == ["a", "b"]
        assert cache.llen("mylist") == 2

    def test_rpop_multiple(self, cache: RedisCache):
        """Test popping multiple values from the tail."""
        cache.rpush("mylist", "a", "b", "c", "d")
        result = cache.rpop("mylist", count=2)
        assert result == ["d", "c"]
        assert cache.llen("mylist") == 2

    def test_lpop_empty(self, cache: RedisCache):
        """Test popping from an empty list."""
        result = cache.lpop("nonexistent")
        assert result is None

    def test_rpop_empty(self, cache: RedisCache):
        """Test popping from an empty list."""
        result = cache.rpop("nonexistent")
        assert result is None

    def test_llen(self, cache: RedisCache):
        """Test getting list length."""
        assert cache.llen("mylist") == 0
        cache.rpush("mylist", "a", "b", "c")
        assert cache.llen("mylist") == 3

    def test_lrange_full(self, cache: RedisCache):
        """Test getting full range of a list."""
        cache.rpush("mylist", "a", "b", "c", "d", "e")
        result = cache.lrange("mylist", 0, -1)
        assert result == ["a", "b", "c", "d", "e"]

    def test_lrange_partial(self, cache: RedisCache):
        """Test getting partial range of a list."""
        cache.rpush("mylist", "a", "b", "c", "d", "e")
        result = cache.lrange("mylist", 1, 3)
        assert result == ["b", "c", "d"]

    def test_lrange_negative_indices(self, cache: RedisCache):
        """Test lrange with negative indices."""
        cache.rpush("mylist", "a", "b", "c", "d", "e")
        result = cache.lrange("mylist", -3, -1)
        assert result == ["c", "d", "e"]

    def test_lindex(self, cache: RedisCache):
        """Test getting element by index."""
        cache.rpush("mylist", "a", "b", "c")
        assert cache.lindex("mylist", 0) == "a"
        assert cache.lindex("mylist", 1) == "b"
        assert cache.lindex("mylist", -1) == "c"

    def test_lindex_out_of_range(self, cache: RedisCache):
        """Test lindex with out of range index."""
        cache.rpush("mylist", "a", "b")
        assert cache.lindex("mylist", 10) is None

    def test_lset(self, cache: RedisCache):
        """Test setting element by index."""
        cache.rpush("mylist", "a", "b", "c")
        result = cache.lset("mylist", 1, "x")
        assert result is True
        assert cache.lindex("mylist", 1) == "x"

    def test_lrem_positive_count(self, cache: RedisCache):
        """Test removing elements from head."""
        cache.rpush("mylist", "a", "b", "a", "c", "a")
        result = cache.lrem("mylist", 2, "a")
        assert result == 2
        assert cache.lrange("mylist", 0, -1) == ["b", "c", "a"]

    def test_lrem_negative_count(self, cache: RedisCache):
        """Test removing elements from tail."""
        cache.rpush("mylist", "a", "b", "a", "c", "a")
        result = cache.lrem("mylist", -2, "a")
        assert result == 2
        assert cache.lrange("mylist", 0, -1) == ["a", "b", "c"]

    def test_lrem_zero_count(self, cache: RedisCache):
        """Test removing all occurrences."""
        cache.rpush("mylist", "a", "b", "a", "c", "a")
        result = cache.lrem("mylist", 0, "a")
        assert result == 3
        assert cache.lrange("mylist", 0, -1) == ["b", "c"]

    def test_ltrim(self, cache: RedisCache):
        """Test trimming a list."""
        cache.rpush("mylist", "a", "b", "c", "d", "e")
        result = cache.ltrim("mylist", 1, 3)
        assert result is True
        assert cache.lrange("mylist", 0, -1) == ["b", "c", "d"]

    def test_linsert_before(self, cache: RedisCache):
        """Test inserting before an element."""
        cache.rpush("mylist", "a", "c", "d")
        result = cache.linsert("mylist", "BEFORE", "c", "b")
        assert result == 4
        assert cache.lrange("mylist", 0, -1) == ["a", "b", "c", "d"]

    def test_linsert_after(self, cache: RedisCache):
        """Test inserting after an element."""
        cache.rpush("mylist", "a", "b", "d")
        result = cache.linsert("mylist", "AFTER", "b", "c")
        assert result == 4
        assert cache.lrange("mylist", 0, -1) == ["a", "b", "c", "d"]

    def test_linsert_not_found(self, cache: RedisCache):
        """Test inserting when pivot element not found."""
        cache.rpush("mylist", "a", "b")
        result = cache.linsert("mylist", "BEFORE", "x", "c")
        assert result == -1

    def test_list_with_version(self, cache: RedisCache):
        """Test list operations with version parameter."""
        cache.rpush("data", "v1", version=1)
        cache.rpush("data", "v2", version=2)

        assert cache.lrange("data", 0, -1, version=1) == ["v1"]
        assert cache.lrange("data", 0, -1, version=2) == ["v2"]

    def test_list_with_complex_objects(self, cache: RedisCache):
        """Test that complex objects serialize correctly."""
        cache.rpush("complex", {"key": "value"}, 123, ("tuple", "item"))
        result = cache.lrange("complex", 0, -1)
        assert len(result) == 3
        assert {"key": "value"} in result
        assert 123 in result

    def test_list_order_lpush_rpush(self, cache: RedisCache):
        """Test order when mixing lpush and rpush."""
        cache.rpush("mylist", "b")
        cache.lpush("mylist", "a")
        cache.rpush("mylist", "c")
        assert cache.lrange("mylist", 0, -1) == ["a", "b", "c"]

    def test_list_fifo_queue(self, cache: RedisCache):
        """Test using list as FIFO queue (rpush + lpop)."""
        cache.rpush("queue", "first", "second", "third")
        assert cache.lpop("queue") == "first"
        assert cache.lpop("queue") == "second"
        assert cache.lpop("queue") == "third"
        assert cache.lpop("queue") is None

    def test_list_stack(self, cache: RedisCache):
        """Test using list as stack (rpush + rpop)."""
        cache.rpush("stack", "first", "second", "third")
        assert cache.rpop("stack") == "third"
        assert cache.rpop("stack") == "second"
        assert cache.rpop("stack") == "first"
        assert cache.rpop("stack") is None

    def test_empty_list_operations(self, cache: RedisCache):
        """Test operations on empty/non-existent lists."""
        assert cache.llen("nonexistent") == 0
        assert cache.lrange("nonexistent", 0, -1) == []
        assert cache.lindex("nonexistent", 0) is None
        assert cache.lpop("nonexistent") is None
        assert cache.rpop("nonexistent") is None
