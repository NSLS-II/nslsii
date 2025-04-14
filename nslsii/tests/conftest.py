from contextlib import contextmanager  # noqa

import redis

import pytest

from bluesky.tests.conftest import RE  # noqa
from bluesky_kafka import BlueskyConsumer  # noqa
from bluesky_kafka.tests.conftest import (  # noqa
    kafka_bootstrap_servers,
    consume_documents_from_kafka_until_first_stop_document,
    temporary_topics,
)
from ophyd.tests.conftest import hw  # noqa

from nslsii.md_dict import RunEngineRedisDict


def pytest_addoption(parser):
    parser.addoption(
        "--xs3-root-path",
        action="store",
        default=None,
        help="path to bluesky 'root' directory where xspress3 writes data files"
    )

    parser.addoption(
        "--xs3-path-template",
        action="store",
        default=None,
        help="path to directory where xspress3 will write files"
    )

    parser.addoption(
        "--xs3-pv-prefix",
        action="store",
        default=None,
        help="PV prefix for xspress3, for example `XF:05IDD-ES{Xsp:1}:`"
    )

    parser.addoption(
        "--xs3-channel-numbers",
        action="store",
        default=None,
        help="comma-separated xspress3 channel numbers, for example `1,2,3`"
    )

    parser.addoption(
        "--xs3-mcaroi-numbers",
        action="store",
        default=None,
        help="comma-separated xspress3 mcaroi numbers, for example `1,2,3`"
    )

    parser.addoption(
        "--kafka-bootstrap-servers",
        action="store",
        default="127.0.0.1:9092",
        help="comma-separated list of address:port for Kafka bootstrap servers",
    )


@pytest.fixture
def xs3_root_path(request):
    return request.config.getoption("--xs3-root-path")


@pytest.fixture
def xs3_path_template(request):
    return request.config.getoption("--xs3-path-template")


@pytest.fixture
def xs3_pv_prefix(request):
    return request.config.getoption("--xs3-pv-prefix")


@pytest.fixture
def xs3_channel_numbers(request):
    comma_separated_numbers = request.config.getoption("--xs3-channel-numbers")
    if comma_separated_numbers is None:
        return None
    else:
        number_list = [int(n) for n in comma_separated_numbers.split(",")]
        return number_list


@pytest.fixture
def xs3_mcaroi_numbers(request):
    comma_separated_numbers = request.config.getoption("--xs3-mcaroi-numbers")
    if comma_separated_numbers is None:
        return None
    else:
        number_list = [int(n) for n in comma_separated_numbers.split(",")]
        return number_list


@pytest.fixture
def redis_dict_factory():
    """
    Return a "fixture as a factory" that will build identical RunEngineRedisDicts.
    Before the factory is returned, the Redis server will be cleared.

    The factory builds only RunEngineRedisDict instances for a Redis server running
    on localhost:6379, db=0.

    If "host", "port", or "db" are specified as kwargs to the factory function
    an exception will be raised.
    """
    redis_server_kwargs = {
        "host": "localhost",
        "port": 6379,
        "db": 0,
    }

    redis_client = redis.Redis(**redis_server_kwargs)
    redis_client.flushdb()

    def _factory(**kwargs):
        disallowed_kwargs_preset = set(redis_server_kwargs.keys()).intersection(
            kwargs.keys()
        )
        if len(disallowed_kwargs_preset) > 0:
            raise KeyError(
                f"{disallowed_kwargs_preset} given, but 'host', 'port', and 'db' may not be specified"
            )
        else:
            kwargs.update(redis_server_kwargs)

        return RunEngineRedisDict(**kwargs)

    return _factory
