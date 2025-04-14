import pytest
import json
import os

from nslsii.re_subs import BlueskyDocStreamPrinter, BlueskyDocJSONWriter

TEST_DOCS = [
    (
        "start",
        {
            "uid": "05275162-aa62-4ef1-97c5-7ced141e3d07",
            "time": 1744206429.5673962,
            "versions": {"ophyd": "1.10.0", "bluesky": "1.13.2.dev44+g0ed50c97"},
            "scan_id": 3,
            "plan_type": "generator",
            "plan_name": "test",
        },
    ),
    (
        "descriptor",
        {
            "configuration": {
                "manta-cam1": {
                    "data": {
                        "manta-cam1-driver-acquire_period": 0.0036960000000000005,
                        "manta-cam1-driver-acquire_time": 0.2,
                    },
                    "timestamps": {
                        "manta-cam1-driver-acquire_time": 1742823799.303813,
                    },
                    "data_keys": {
                        "manta-cam1-driver-acquire_time": {
                            "dtype": "number",
                            "shape": [],
                            "dtype_numpy": "<f8",
                            "source": "ca://XF:31ID1-ES{GigE-Cam:1}cam1:AcquireTime_RBV",
                            "units": "",
                            "precision": 3,
                        },
                    },
                },
            },
            "data_keys": {
                "manta-cam1": {
                    "source": "ca://XF:31ID1-ES{GigE-Cam:1}HDF1:FullFileName_RBV",
                    "shape": [1, 544, 728],
                    "dtype": "array",
                    "dtype_numpy": "|u1",
                    "external": "STREAM:",
                    "object_name": "manta-cam1",
                },
            },
            "name": "primary",
            "object_keys": {"manta-cam1": ["manta-cam1"]},
            "run_start": "05275162-aa62-4ef1-97c5-7ced141e3d07",
            "time": 1744206431.9428892,
            "uid": "44e54ca5-a109-4cda-b75f-2dd58d103fc6",
            "hints": {
                "manta-cam1": {"fields": ["manta-cam1"]},
            },
        },
    ),
    (
        "stream_resource",
        {
            "uid": "603f7d89-db27-46d5-b328-ca1449477de2",
            "data_key": "manta-cam1",
            "mimetype": "application/x-hdf5",
            "uri": "file://localhost/tmp/tiled_storage/data/3a846589-a019-45e9-9521-5e642880e945.h5",
            "parameters": {"dataset": "/entry/data/data", "chunk_shape": [1, 544, 728]},
            "run_start": "05275162-aa62-4ef1-97c5-7ced141e3d07",
        },
    ),
    (
        "stream_datum",
        {
            "stream_resource": "603f7d89-db27-46d5-b328-ca1449477de2",
            "uid": "603f7d89-db27-46d5-b328-ca1449477de2/0",
            "seq_nums": {"start": 1, "stop": 6},
            "indices": {"start": 0, "stop": 5},
            "descriptor": "44e54ca5-a109-4cda-b75f-2dd58d103fc6",
        },
    ),
    (
        "stop",
        {
            "uid": "fedac0af-0491-4d8c-8414-bc7d8276ddde",
            "time": 1744206433.3085756,
            "run_start": "05275162-aa62-4ef1-97c5-7ced141e3d07",
            "exit_status": "success",
            "reason": "",
            "num_events": {"primary": 5},
        },
    ),
]


def test_bs_doc_stream_printer(capsys):
    """Test that the dump_docs_to_stdout function works as expected."""

    doc_stream_printer = BlueskyDocStreamPrinter()

    doc_stream_printer.print_docs_to_stdout = True
    for name, doc in TEST_DOCS:
        doc_stream_printer(name, doc)
        out, err = capsys.readouterr()
        assert f"name = '{name}'" in out
        assert json.dumps(doc, indent=4) in out

    doc_stream_printer.print_docs_to_stdout = False
    for name, doc in TEST_DOCS:
        doc_stream_printer(name, doc)
        out, err = capsys.readouterr()
        assert out == ""
        assert err == ""


def test_json_bluesky_doc_writer(tmp_path):
    """Test that the JSONBlueskyDocWriter works as expected."""
    writer = BlueskyDocJSONWriter(tmp_path)
    expected_filename = TEST_DOCS[0][1]["uid"] + ".json"

    for name, doc in TEST_DOCS:
        writer(name, doc)

    # Make sure that the file wasn't created by default
    assert not (tmp_path / expected_filename).exists()

    # Now turn on the writer and check that the file is created
    # also, check to make sure if we recieve a doc that is not a start doc
    # and the file isn't open, we just drop it.
    writer.write_json_file = True
    for name, doc in TEST_DOCS:
        writer(name, doc)

    assert (tmp_path / expected_filename).exists()

    # Check that the file contains the expected data
    with open(tmp_path / expected_filename) as fp:
        data = json.load(fp)
        for i, doc in enumerate(data):
            print(doc)
            assert doc == {TEST_DOCS[i][0]: TEST_DOCS[i][1]}

    os.remove(tmp_path / expected_filename)

    writer(*TEST_DOCS[1])

    assert not (tmp_path / expected_filename).exists()
