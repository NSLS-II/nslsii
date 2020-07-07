from functools import partial
import multiprocessing
import time

import msgpack
import msgpack_numpy as mpn
import numpy as np

from bluesky.plans import count
from bluesky_kafka import RemoteDispatcher
from event_model import RunRouter, sanitize_doc
import nslsii


def test_kafka_publisher(RE, hw):
    beamline_name = "test"
    kafka_topic = nslsii.subscribe_kafka_publisher(
        RE=RE,
        beamline_name=beamline_name,
        bootstrap_servers="127.0.0.1:9092",
        producer_config={
            "acks": "all",
            "enable.idempotence": False,
            "request.timeout.ms": 5000,
            "linger.ms": 0,
        }
    )

    # COMPONENT 3
    # Run a RemoteDispatcher on a separate process. Pass the documents
    # it receives over a Queue to this process so we can count them for our
    # test.

    def make_and_start_dispatcher(queue):
        def put_in_queue(name, doc):
            queue.put((name, doc))

        kafka_dispatcher = RemoteDispatcher(
            topics=[kafka_topic],
            bootstrap_servers="127.0.0.1:9092",
            group_id="kafka-test-group-id",
            consumer_config={"auto.offset.reset": "latest"},
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

    local_published_documents = []

    # use a RunRouter to get event_pages locally
    # since the KafkaPublisher will produce event_pages
    def local_callback_factory(start_doc_name, start_doc):
        def local_callback(name, doc):
            local_published_documents.append((name, doc))

        return [local_callback], []

    local_callback_run_router = RunRouter(factories=[local_callback_factory])
    RE.subscribe(local_callback_run_router)

    # test that numpy data is transmitted correctly
    md = {
        "numpy_data": {"nested": np.array([1, 2, 3])},
        "numpy_scalar": np.float64(4),
        "numpy_array": np.ones((3, 3)),
    }

    RE(count([hw.det]), md=md)
    # time.sleep(10)

    # test that numpy data is transmitted correctly
    md = {
        "numpy_data": {"nested": np.array([4, 5, 6])},
        "numpy_scalar": np.float64(7),
        "numpy_array": np.ones((4, 4)),
    }

    RE(count([hw.det]), md=md)
    time.sleep(10)

    # Get the documents from the queue (or timeout --- test will fail)
    remote_published_documents = []
    for i in range(len(local_published_documents)):
        remote_published_documents.append(queue_.get(timeout=2))

    dispatcher_proc.terminate()
    dispatcher_proc.join()

    # sanitize_doc normalizes some document data, such as numpy arrays, that are
    # problematic for direct comparison of documents by "assert"
    sanitized_local_published_documents = [
        sanitize_doc(doc) for doc in local_published_documents
    ]
    sanitized_remote_published_documents = [
        sanitize_doc(doc) for doc in remote_published_documents
    ]

    assert sanitized_remote_published_documents == sanitized_local_published_documents
