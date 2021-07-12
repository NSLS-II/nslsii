import io
import logging
import re
import uuid

from bluesky.plans import count
from event_model import sanitize_doc
import nslsii


def configure_debug_logging(logger_name):
    # create logger
    logger_ = logging.getLogger(logger_name)
    logger_.setLevel(logging.DEBUG)
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger_.addHandler(ch)


configure_debug_logging("nslsii")


def test_build_and_subscribe_kafka_publisher(
    kafka_bootstrap_servers,
    temporary_topics,
    consume_documents_from_kafka_until_first_stop_document,
    RE,
    hw,
):
    """Test threaded publishing of Kafka messages.

    This test follows the pattern in bluesky_kafka/tests/test_in_single_process.py,
    which is to publish Kafka messages _before_ subscribing a Kafka consumer to
    those messages. After the messages have been published a consumer is subscribed
    to the topic and should receive all messages since they will have been cached by
    the Kafka broker(s). This keeps the test code relatively simple.

    Start Kafka and Zookeeper like this:
      $ sudo docker-compose -f scripts/bitnami-kafka-docker-compose.yml up

    Remove Kafka and Zookeeper containers like this:
      $ sudo docker ps -a -q
      78485383ca6f
      8a80fb4a385f
      $ sudo docker stop 78485383ca6f 8a80fb4a385f
      78485383ca6f
      8a80fb4a385f
      $ sudo docker rm 78485383ca6f 8a80fb4a385f
      78485383ca6f
      8a80fb4a385f

    Or remove ALL containers like this:
      $ sudo docker stop $(sudo docker ps -a -q)
      $ sudo docker rm $(sudo docker ps -a -q)
    Use this in difficult cases:
      $ sudo docker system prune -a

    Parameters
    ----------
    kafka_bootstrap_servers: str (pytest fixture)
        comma-delimited string of Kafka broker host:port, for example "kafka1:9092,kafka2:9092"
    temporary_topics: context manager (pytest fixture)
        creates and cleans up temporary Kafka topics for testing
    RE: pytest fixture
        bluesky RunEngine
    hw: pytest fixture
        ophyd simulated hardware objects
    """

    # use a random string as the beamline name so topics will not be duplicated across tests
    beamline_name = str(uuid.uuid4())[:8]
    with temporary_topics(topics=[f"{beamline_name}.bluesky.runengine.documents"]) as (
        beamline_topic,
    ):

        (
            nslsii_beamline_topic,
            subscription_token,
        ) = nslsii.build_and_subscribe_kafka_publisher(
            RE=RE,
            beamline_name=beamline_name,
            bootstrap_servers=kafka_bootstrap_servers,
            producer_config={
                "acks": "all",
                "enable.idempotence": False,
                "request.timeout.ms": 1000,
            },
        )

        assert nslsii_beamline_topic == beamline_topic
        assert isinstance(subscription_token, int)

        published_bluesky_documents = []

        # this function will store all documents
        # published by the RunEngine in a list
        def store_published_document(name, document):
            published_bluesky_documents.append((name, document))

        RE.subscribe(store_published_document)

        RE(count([hw.det]))

        # it is known that RE(count()) will produce four
        # documents: start, descriptor, event, stop
        assert len(published_bluesky_documents) == 4

        consumed_bluesky_documents = (
            consume_documents_from_kafka_until_first_stop_document(
                kafka_topic=nslsii_beamline_topic
            )
        )

        assert len(published_bluesky_documents) == len(consumed_bluesky_documents)

        # sanitize_doc normalizes some document data, such as numpy arrays, that are
        # problematic for direct comparison of documents by 'assert'
        sanitized_published_bluesky_documents = [
            sanitize_doc(doc) for doc in published_bluesky_documents
        ]
        sanitized_consumed_bluesky_documents = [
            sanitize_doc(doc) for doc in consumed_bluesky_documents
        ]

        assert len(sanitized_consumed_bluesky_documents) == len(
            sanitized_published_bluesky_documents
        )
        assert (
            sanitized_consumed_bluesky_documents
            == sanitized_published_bluesky_documents
        )


def test_no_beamline_topic(kafka_bootstrap_servers, RE):
    """
    If the beamline Kafka topic does not exist then an exception
    should be raised and handled by writing an exception message
    to the nslsii logger.

    Parameters
    ----------
    kafka_bootstrap_servers: str (pytest fixture)
        comma-delimited string of Kafka broker host:port, for example "kafka1:9092,kafka2:9092"
    RE: RunEngine (pytest fixture)
        bluesky RunEngine
    """
    try:
        logging_test_output = io.StringIO()
        nslsii_logger = logging.getLogger("nslsii")
        logging_test_handler = logging.StreamHandler(stream=logging_test_output)
        logging_test_handler.setFormatter(logging.Formatter("%(message)s"))
        nslsii_logger.addHandler(logging_test_handler)

        # use a random string as the beamline name so topics will not be duplicated across tests
        beamline_name = str(uuid.uuid4())[:8]
        nslsii.build_and_subscribe_kafka_publisher(
            RE=RE,
            beamline_name=beamline_name,
            bootstrap_servers=kafka_bootstrap_servers,
            producer_config={
                "acks": "all",
                "enable.idempotence": False,
                "request.timeout.ms": 1000,
            },
        )

        assert (
            f"topic `{beamline_name}.bluesky.runengine.documents` does not exist on Kafka broker(s)"
            in logging_test_output.getvalue()
        )

    finally:
        nslsii_logger.removeHandler(hdlr=logging_test_handler)


def test_subscribe_kafka_publisher(temporary_topics, RE):
    """
    Test exception handling when a bluesky_kafka.Publisher raises an exception.

    Parameter
    ---------
    RE: RunEngine

    """
    # use a random string as the beamline name so topics will not be duplicated across tests
    beamline_name = str(uuid.uuid4())[:8]
    with temporary_topics(topics=[f"{beamline_name}.bluesky.runengine.documents"]) as (
        beamline_topic,
    ):
        import time
        import queue
        from unittest.mock import Mock
        from bluesky_kafka import BlueskyKafkaException

        logging_test_output = io.StringIO()
        nslsii_logger = logging.getLogger("nslsii")
        logging_test_handler = logging.StreamHandler(stream=logging_test_output)
        logging_test_handler.setFormatter(
            logging.Formatter("%(threadName)s - %(message)s")
        )
        nslsii_logger.addHandler(logging_test_handler)

        publisher_queue = queue.Queue()
        mock_kafka_publisher = Mock(side_effect=BlueskyKafkaException())
        (
            _,
            kafka_publisher_thread,
            kafka_publisher_thread_stop_event,
        ) = nslsii.subscribe_kafka_publisher(
            RE=RE, publisher_queue=publisher_queue, kafka_publisher=mock_kafka_publisher
        )

        # provoke two exceptions
        publisher_queue.put(("blarg", {}))
        publisher_queue.put(("barf", {}))

        while not publisher_queue.empty():
            time.sleep(1)
            print("ha!")
        print("done!")

        kafka_publisher_thread_stop_event.set()
        kafka_publisher_thread.join()

        log_output = logging_test_output.getvalue()
        print("****************")
        print(log_output)
        print("****************")
        exception_message_pattern = re.compile(
            r"an error occurred after 0 successful Kafka messages when '<Mock id='\d+'>' attempted to publish",
        )

        first_match = exception_message_pattern.search(log_output)
        assert first_match

        print(f"log_output[{first_match.endpos}:]: {log_output[first_match.endpos:]}")
        second_match = exception_message_pattern.search(
            log_output, pos=first_match.endpos
        )
        assert second_match

        # third_match = exception_message_pattern.search(log_output, pos=second_match.endpos)
        # assert third_match is None
