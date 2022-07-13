from contextlib import contextmanager

import redis

import pytest

from bluesky.tests.conftest import RE  # noqa
from bluesky_kafka import BlueskyConsumer
from bluesky_kafka.tests.conftest import (
    pytest_addoption,
    kafka_bootstrap_servers,
    broker_authorization_config,
    consume_documents_from_kafka_until_first_stop_document,
    temporary_topics,
)  # noqa
from ophyd.tests.conftest import hw  # noqa

from nslsii.md_dict import RunEngineRedisDict


@pytest.fixture
def redis_dict_factory():
    """
    Return a "fixture as a factory" that will build identical RunEngineRedisDicts.
    Before the factory is returned, the Redis server will be cleared.
    """
    redis_client = redis.Redis(host="localhost", port=6379, db=0)
    redis_client.flushdb()

    def _factory(re_md_channel_name, **kwargs):
        init_kwargs = {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "re_md_channel_name": re_md_channel_name
        }
        init_kwargs.update(kwargs)

        return RunEngineRedisDict(**init_kwargs)

    return _factory


