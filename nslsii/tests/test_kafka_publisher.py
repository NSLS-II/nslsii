from functools import partial
import multiprocessing
import queue
import time

import msgpack
import msgpack_numpy as mpn
import numpy as np

from bluesky.plans import count
from bluesky_kafka import RemoteDispatcher
from event_model import RunRouter, sanitize_doc
import nslsii


def test_kafka_publisher(RE, hw, bootstrap_servers):
    kafka_topic, runrouter_token = nslsii.subscribe_kafka_publisher(
        RE=RE,
        beamline_name="test",
        bootstrap_servers=bootstrap_servers,
        producer_config={
            "acks": "all",
            "enable.idempotence": False,
            "request.timeout.ms": 1000,
        },
    )

    assert kafka_topic == "test.bluesky.documents"
    assert isinstance(runrouter_token, int)

    # Run a RemoteDispatcher on a separate process. Pass the documents
    # it receives over a multiprocessing.Queue back to this process so
    # we can compare with locally stored documents.
    # The default "auto.commit.interval.ms" is 5000, but using the default
    # means some of the Kafka messages consumed here are not committed
    # and so are DELIVERED AGAIN the next time this test runs. The solution
    # is setting a very short "auto.commit.interval.ms" for this test.
    def make_and_start_dispatcher(document_queue):
        def put_in_queue(name, doc):
            document_queue.put((name, doc))

        kafka_dispatcher = RemoteDispatcher(
            topics=[kafka_topic],
            bootstrap_servers=bootstrap_servers,
            group_id="test_kafka_publisher",
            consumer_config={
                "auto.offset.reset": "latest",
                "auto.commit.interval.ms": 100,
            },
            polling_duration=1.0,
            deserializer=partial(msgpack.loads, object_hook=mpn.decode),
        )
        kafka_dispatcher.subscribe(put_in_queue)
        kafka_dispatcher.start()

    queue_ = multiprocessing.Queue()
    dispatcher_proc = multiprocessing.Process(
        target=make_and_start_dispatcher, daemon=True, args=(queue_,)
    )
    dispatcher_proc.start()
    # give the dispatcher process time to start
    time.sleep(10)

    local_documents = []

    # use a RunRouter to get event_pages locally because
    # the KafkaPublisher will produce event_pages
    def document_accumulator_factory(start_doc_name, start_doc):
        def document_accumulator(name, doc):
            local_documents.append((name, doc))

        return [document_accumulator], []

    local_run_router = RunRouter(factories=[document_accumulator_factory])
    RE.subscribe(local_run_router)

    # test that numpy data is transmitted correctly
    md1 = {
        "numpy_data": {"nested": np.array([1, 2, 3])},
        "numpy_scalar": np.float64(4),
        "numpy_array": np.ones((3, 3)),
    }

    RE(count([hw.det1]), md=md1)

    # test that numpy data is transmitted correctly
    md2 = {
        "numpy_data": {"nested": np.array([4, 5, 6])},
        "numpy_scalar": np.float64(7),
        "numpy_array": np.ones((4, 4)),
    }

    RE(count([hw.det2]), md=md2)

    # Get the documents from the inter-process queue (or timeout)
    remote_documents = []
    while True:
        try:
            name_, doc_ = queue_.get(timeout=1)
            remote_documents.append((name_, doc_))
        except queue.Empty:
            print("the queue is empty!")
            break

    dispatcher_proc.terminate()
    dispatcher_proc.join()

    # sanitize_doc normalizes some document data, such as numpy arrays,
    # that are problematic for direct document comparison by "assert"
    sanitized_local_published_documents = [
        (name, sanitize_doc(doc)) for name, doc in local_documents
    ]
    sanitized_remote_published_documents = [
        (name, sanitize_doc(doc)) for name, doc in remote_documents
    ]

    assert len(remote_documents) == len(local_documents)
    assert len(sanitized_remote_published_documents) == len(
        sanitized_local_published_documents
    )
    assert sanitized_remote_published_documents == sanitized_local_published_documents

    # test that we got the correct subscription token for the Kafka Publisher
    # KeyError is raised if the token is not known
    RE.unsubscribe(token=runrouter_token)


def test_publisher_with_no_broker(RE, hw):
    # specify a bootstrap server that does not exist
    kafka_topic = nslsii.subscribe_kafka_publisher(
        RE=RE,
        beamline_name="test",
        bootstrap_servers="100.100.100.100:9092",
        producer_config={
            "acks": "all",
            "enable.idempotence": False,
            "request.timeout.ms": 1000,
        }
    )

    # use a RunRouter to get event_pages locally because
    # the KafkaPublisher will produce event_pages
    local_published_documents = list()

    def document_accumulator_factory(start_doc_name, start_doc):
        def document_accumulator(name, doc):
            local_published_documents.append((name, doc))

        return [document_accumulator], []

    local_run_router = RunRouter(factories=[document_accumulator_factory])
    RE.subscribe(local_run_router)

    t0 = time.time()
    RE(count([hw.det1]))
    t1 = time.time()

    # timeout is set at 1s but it takes longer than 5s to run count
    print(f"time for count: {t1-t0:.3f}")
    assert (t1 - t0) < 10.0

    assert len(local_published_documents) == 4
