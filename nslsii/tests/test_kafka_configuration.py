from pathlib import Path

import pytest
from nslsii import _read_bluesky_kafka_config_file


test_bluesky_kafka_config = """\
---
  bootstrap_servers:
    - kafka1:9092
    - kafka2:9092
    - kafka3:9092
  runengine_producer_config:
    acks: 0
    message.timeout.ms: 3000
    compression.codec: "snappy"
"""


def test__read_bluesky_kafka_config_file(tmp_path):
    # write a temporary file for this test
    test_config_file_path = tmp_path / "test_bluesky_kafka_config.yml"
    with open(test_config_file_path, "wt") as f:
        f.write(test_bluesky_kafka_config)

    bluesky_kafka_config = _read_bluesky_kafka_config_file(test_config_file_path)

    assert bluesky_kafka_config["bootstrap_servers"] == [
        "kafka1:9092",
        "kafka2:9092",
        "kafka3:9092",
    ]

    runengine_producer_config = bluesky_kafka_config["runengine_producer_config"]
    assert len(runengine_producer_config) == 3
    assert runengine_producer_config["acks"] == 0
    assert runengine_producer_config["message.timeout.ms"] == 3000
    assert runengine_producer_config["compression.codec"] == "snappy"


def test__read_bluesky_kafka_config_file_failure(tmp_path):
    test_config_file_path = tmp_path / "test_bluesky_kafka_config.yml"

    with pytest.raises(FileNotFoundError):
        _read_bluesky_kafka_config_file(test_config_file_path)
