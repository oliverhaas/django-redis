from django_redis.client.pipeline.base import WrappedPipeline
from django_redis.client.pipeline.hashes import HashPipelineMixin
from django_redis.client.pipeline.lists import ListPipelineMixin
from django_redis.client.pipeline.sets import SetPipelineMixin
from django_redis.client.pipeline.sorted_sets import SortedSetPipelineMixin


class Pipeline(
    ListPipelineMixin,
    SetPipelineMixin,
    HashPipelineMixin,
    SortedSetPipelineMixin,
    WrappedPipeline,
):
    """Full pipeline with all data structure operations.

    Combines the base pipeline with all mixins to provide
    a complete interface for batched Redis operations.
    """


__all__ = [
    "Pipeline",
    "WrappedPipeline",
]
