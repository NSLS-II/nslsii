from contextlib import contextmanager
import pytest
from bluesky.tests.conftest import RE  # noqa
from bluesky_kafka import BlueskyConsumer
from bluesky_kafka.tests.conftest import (
    pytest_addoption,
    kafka_bootstrap_servers,
    temporary_topics,
)  # noqa
from ophyd.tests.conftest import hw  # noqa


# this should move to bluesky_kafka
@pytest.fixture(scope="function")
def consume_documents_from_kafka_until_first_stop_document(request, kafka_bootstrap_servers):

    def _consume_documents_from_kafka(kafka_topic, bootstrap_servers=None):
        if bootstrap_servers is None:
            bootstrap_servers = kafka_bootstrap_servers

        consumed_bluesky_documents = []

        def store_consumed_document(consumer, topic, name, document):
            """
            This function keeps a list of all documents the consumer
            gets from the Kafka broker(s).

            Parameters
            ----------
            consumer: bluesky_kafka.BlueskyConsumer
                unused
            topic: str
                unused
            name: str
                bluesky document name, such as "start", "descriptor", "event", etc
            document: dict
                dictionary of bluesky document data
            """
            consumed_bluesky_documents.append((name, document))

        bluesky_consumer = BlueskyConsumer(
            topics=[kafka_topic],
            bootstrap_servers=bootstrap_servers,
            group_id=f"{kafka_topic}.consumer.group",
            consumer_config={
                # this consumer is intended to read messages that
                # have already been published, so it is necessary
                # to specify "earliest" here
                "auto.offset.reset": "earliest",
            },
            process_document=store_consumed_document,
            polling_duration=1.0,
        )

        def until_first_stop_document():
            """
            This function returns False to end the BlueskyConsumer polling loop after seeing
            a "stop" document. This is important for the test to end.
            """
            if "stop" in [name for name, _ in consumed_bluesky_documents]:
                return False
            else:
                return True

        # start() will return when 'until_first_stop_document' returns False
        bluesky_consumer.start(
            continue_polling=until_first_stop_document,
        )
        # how do we get here?

        return consumed_bluesky_documents

    return _consume_documents_from_kafka
