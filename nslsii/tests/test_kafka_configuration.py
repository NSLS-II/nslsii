import os
from pathlib import Path

import pytest

from nslsii import configure_kafka_publisher, _read_bluesky_kafka_config_file


test_bluesky_kafka_config = """\
---
  abort_run_on_kafka_exception: true
  bootstrap_servers:
    - kafka1:9092
    - kafka2:9092
    - kafka3:9092
  runengine_producer_config:
    acks: 0
    message.timeout.ms: 3000
    compression.codec: snappy
"""


def test_bluesky_kafka_config_path_env_var(tmp_path, RE):
    """Test specifying a configuration file path by environment variable."""
    # write a temporary file for this test
    test_config_file_path = tmp_path / "test_bluesky_kafka_config.yml"
    with open(test_config_file_path, "wt") as f:
        f.write(test_bluesky_kafka_config)
        # add an extra item to test for later
        f.write(f"  config_file_path: {test_config_file_path}")

    os.environ["BLUESKY_KAFKA_CONFIG_PATH"] = str(test_config_file_path)
    bluesky_kafka_configuration = configure_kafka_publisher(RE, "abc")

    assert bluesky_kafka_configuration["config_file_path"] == str(test_config_file_path)


def test_bluesky_kafka_config_path_env_var_negative(tmp_path, RE):
    """Test specifying a configuration file path that does not exist by environment variable."""
    # write a temporary file for this test
    test_config_file_path = tmp_path / "test_bluesky_kafka_config.yml"
    os.environ["BLUESKY_KAFKA_CONFIG_PATH"] = str(test_config_file_path)
    with pytest.raises(FileNotFoundError, match=str(test_config_file_path)):
        bluesky_kafka_configuration = configure_kafka_publisher(RE, "abc")


def test_bluesky_kafka_config_path_default_negative(tmp_path, RE):
    """Test the default configuration file path.

    It is not possible to install a test file to the default location.
    This test checks for FileNotFoundError with the expected default file path.

    """
    # a previous test may have left this
    if "BLUESKY_KAFKA_CONFIG_PATH" in os.environ:
        del os.environ["BLUESKY_KAFKA_CONFIG_PATH"]
    with pytest.raises(FileNotFoundError, match="/etc/bluesky/kafka.yml"):
        bluesky_kafka_configuration = configure_kafka_publisher(RE, "abc")


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
    """Raise FileNotFoundError if the configuration file does not exist.

    The configuration file path should be reported in the error.
    """
    test_config_file_path = tmp_path / "test_bluesky_kafka_config.yml"

    with pytest.raises(FileNotFoundError, match=str(test_config_file_path)):
        _read_bluesky_kafka_config_file(test_config_file_path)


def test__read_bluesky_kafka_config_file_missing_sections(tmp_path):
    """Raise Exception if the configuration file is missing one or more required sections.

    The configuration file path and all missing required sections should be reported in the Exception.
    """
    # write a temporary file for this test
    test_config_file_path = tmp_path / "test_bluesky_kafka_config.yml"
    with open(test_config_file_path, "wt") as f:
        # write a configuration file with none of the required sections
        f.write("---\n  a\n  b\n")

    with pytest.raises(
        Exception,
        match=f".*{str(test_config_file_path)}.*\['abort_run_on_kafka_exception', 'bootstrap_servers', 'runengine_producer_config'\]",
    ):
        _read_bluesky_kafka_config_file(test_config_file_path)
