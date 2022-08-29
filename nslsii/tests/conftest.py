from contextlib import contextmanager

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


def pytest_addoption(parser):
    parser.addoption(
        "--xs3-data-dir", action="store", help="path to directory where xspress3 writes data files"
    )

    parser.addoption(
        "--xs3-pv-prefix", action="store", help="PV prefix for xspress3, for example `XF:05IDD-ES{Xsp:1}:`"
    )


@pytest.fixture
def xs3_data_dir(request):
    return request.config.getoption("--xs3-data-dir")


@pytest.fixture
def xs3_pv_prefix(request):
    return request.config.getoption("--xs3-pv-prefix")
