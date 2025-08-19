from __future__ import annotations

import time
from pprint import pformat

import numpy as np
import pytest
import redis
import redis.exceptions

from nslsii.md_dict import RunEngineRedisDict


def _build_redis_subscriber(redis_dict):
    """
    Build and return a Redis "pubsub" object subscribed
    to the redis_dict parameter.
    """
    redis_subscriber = redis.Redis(
        host=redis_dict._host, port=redis_dict._port, db=redis_dict._db
    ).pubsub(ignore_subscribe_messages=True)
    redis_subscriber.subscribe(redis_dict._re_md_channel_name)
    return redis_subscriber


def _get_waiting_messages(redis_subscriber):
    """
    Get all messages from a Redis "pubsub" object and
    return them in a list. The returned list may be empty.
    """
    message_list = []
    message = redis_subscriber.get_message()
    if message is None:
        # it can happen that there are messages
        # even if None is returned the first time
        message = redis_subscriber.get_message()
    while message is not None:
        message_list.append(message)
        message = redis_subscriber.get_message()

    print(f"_get_waiting_messages() returning\n{message_list}")
    return message_list


def test_instantiate_with_server(redis_dict_factory):
    """
    Instantiate a RunEngineRedisDict and expect success.
    """
    redis_dict_factory(re_md_channel_name="test_instantiate_with_server")


def test_instantiate_no_server():
    """
    Instantiate a RunEngineRedisDict using a bad port number.
    Expect to fail.
    """
    with pytest.raises(redis.exceptions.ConnectionError):
        # there is no redis server on port 9999
        RunEngineRedisDict(host="localhost", port=9999)


def test__parse_message_data():
    """
    Test a simple message "abc:uuid" and
    a potentially problematic message "a:b:c:uuid"
    """
    message = {"data": b"abc:uuid"}
    key, uuid = RunEngineRedisDict._parse_message_data(message)
    assert key == "abc"
    assert uuid == "uuid"

    # what if the key contains one or more colons?
    message = {"data": b"a:b:c:uuid"}
    key, uuid = RunEngineRedisDict._parse_message_data(message)
    assert key == "a:b:c"
    assert uuid == "uuid"

    message = {"data": b"abcuuid"}
    with pytest.raises(ValueError):
        RunEngineRedisDict._parse_message_data(message)


def test_local_int_value(redis_dict_factory):
    """
    Test that an integer is stored and retrieved.
    """
    redis_dict = redis_dict_factory(re_md_channel_name="test_local_int_value")
    redis_dict["local_int"] = -1
    assert redis_dict["local_int"] == -1


def test_local_float_value(redis_dict_factory):
    """
    Test that a float is stored and retrieved.
    """
    redis_dict = redis_dict_factory(re_md_channel_name="test_local_float_value")
    import math

    redis_dict["local_float"] = math.pi
    assert redis_dict["local_float"] == math.pi


def test_local_ndarray_value(redis_dict_factory):
    """
    Test that a numpy NDArray is stored and retrieved.
    """
    redis_dict = redis_dict_factory(re_md_channel_name="test_local_ndarray_value")

    redis_dict["local_array"] = np.ones((10, 10))
    assert np.array_equal(redis_dict["local_array"], np.ones((10, 10)))


def test_no_global_metadata(redis_dict_factory):
    """
    Construct a RunEngineRedisDict with no "global" metadata.
    """
    redis_dict = redis_dict_factory(
        re_md_channel_name="test_no_global_metadata", global_keys=[]
    )

    assert len(redis_dict) == 0


def test_global_int_value(redis_dict_factory):
    """
    Test that an integer is stored and retrieved.
    """
    redis_dict_1 = redis_dict_factory(re_md_channel_name="test_global_int_value")

    # scan_id does not exist yet
    with pytest.raises(KeyError):
        redis_dict_1["scan_id"]

    redis_dict_1["scan_id"] = 0
    assert redis_dict_1["scan_id"] == 0

    redis_dict_2 = redis_dict_factory(re_md_channel_name="test_global_int_value")
    assert redis_dict_2["scan_id"] == 0

    # expect an exception because "scan_id" is
    # constrained to be an integer
    with pytest.raises(ValueError):
        redis_dict_1["scan_id"] = "one"

    assert redis_dict_1["scan_id"] == 0


def test_del_global_key(redis_dict_factory):
    """
    Test that attempting to delete a "global" key raises KeyError.
    """
    redis_dict = redis_dict_factory(re_md_channel_name="test_del_global_key")
    with pytest.raises(KeyError):
        del redis_dict[redis_dict._global_keys[0]]


def test_del_local_key(redis_dict_factory):
    """
    Test that a "local" key can be deleted and that
    a message is published.
    """
    redis_dict = redis_dict_factory(re_md_channel_name="test_del_local_key")
    redis_subscriber = _build_redis_subscriber(redis_dict)

    redis_dict["local_key"] = "local_value"
    assert redis_dict["local_key"] == "local_value"

    _local_md = redis_dict._get_local_metadata_from_server()
    assert _local_md["local_key"] == "local_value"

    del redis_dict["local_key"]
    _local_md = redis_dict._get_local_metadata_from_server()

    assert "local_key" not in _local_md
    assert "local_key" not in redis_dict

    messages = _get_waiting_messages(redis_subscriber)
    assert len(messages) == 2

    for message in messages:
        updated_key, publisher_uuid = RunEngineRedisDict._parse_message_data(message)
        assert updated_key == "local_key"
        assert publisher_uuid == redis_dict._uuid


def test_items(redis_dict_factory):
    """
    Test .items() starting from an empty Redis database.
    """
    redis_dict = redis_dict_factory(re_md_channel_name="test_items")

    # no global metadata exists yet
    actual_global_items = {gk: gv for gk, gv in redis_dict.items()}
    assert actual_global_items == {}

    # set a value for each global key
    global_md_updates = {gk: gk for gk in redis_dict._global_keys}
    global_md_updates["scan_id"] = 1
    redis_dict.update(global_md_updates)

    actual_global_items = {gk: gv for gk, gv in redis_dict.items()}
    # _local_md should still be empty
    # since only global metadata was updated
    assert len(redis_dict._local_md) == 0
    assert actual_global_items == global_md_updates

    # set some local metadata
    local_md_updates = {"one": 1, "two": "2"}
    redis_dict.update(local_md_updates)
    assert redis_dict._local_md == local_md_updates
    expected_items = dict()
    expected_items.update(global_md_updates)
    expected_items.update(local_md_updates)
    actual_items = {k: v for k, v in redis_dict.items()}
    assert actual_items == expected_items


def test_one_message(redis_dict_factory):
    redis_dict = redis_dict_factory(re_md_channel_name="test_one_message")
    print(redis_dict._local_md)
    assert len(redis_dict._local_md) == 0

    redis_subscriber = _build_redis_subscriber(redis_dict)

    # expect no messages
    messages = _get_waiting_messages(redis_subscriber)
    assert len(messages) == 0

    redis_dict["generate_one_message"] = 1
    # expect one message
    messages = _get_waiting_messages(redis_subscriber)
    print(f"messages:\n {pformat(messages)}")
    assert len(messages) == 1
    updated_key, publisher_uuid = redis_dict._parse_message_data(messages[0])
    assert updated_key == "generate_one_message"
    assert publisher_uuid == redis_dict._uuid


def test_two_messages(redis_dict_factory):
    redis_dict = redis_dict_factory(re_md_channel_name="test_two_messages")
    print(redis_dict._local_md)
    assert len(redis_dict._local_md) == 0

    redis_subscriber = _build_redis_subscriber(redis_dict)

    redis_dict["generate_one_message"] = 1
    redis_dict["generate_another_message"] = 2

    messages = _get_waiting_messages(redis_subscriber)
    assert len(messages) == 2
    for message, expected_updated_key in zip(messages, redis_dict._local_md.keys()):
        actual_updated_key, publisher_uuid = redis_dict._parse_message_data(message)
        assert actual_updated_key == expected_updated_key
        assert publisher_uuid == redis_dict._uuid


def test_global_metadata_synchronization(redis_dict_factory):
    """
    Test "global metadata" synchronization between separate RunEngineRedisDicts.
    """
    redis_dict_1 = redis_dict_factory(
        re_md_channel_name="test_global_metadata_synchronization"
    )
    redis_dict_2 = redis_dict_factory(
        re_md_channel_name="test_global_metadata_synchronization"
    )
    redis_dict_2_subscriber = _build_redis_subscriber(redis_dict_2)

    # make one change
    redis_dict_1["proposal_id"] = "PROPOSAL ID"
    redis_dict_1["scan_id"] = 0

    time.sleep(1)
    redis_dict_2_messages = _get_waiting_messages(redis_dict_2_subscriber)
    assert len(redis_dict_2_messages) == 2

    assert redis_dict_2["proposal_id"] == "PROPOSAL ID"
    assert redis_dict_2["scan_id"] == 0

    redis_dict_3 = redis_dict_factory(
        re_md_channel_name="test_global_metadata_synchronization"
    )
    assert redis_dict_3["proposal_id"] == "PROPOSAL ID"
    assert redis_dict_3["scan_id"] == 0

    redis_dict_3["scan_id"] = 1
    time.sleep(1)
    assert redis_dict_1["scan_id"] == 1
    assert redis_dict_2["scan_id"] == 1


def test_local_metadata_synchronization(redis_dict_factory):
    """
    Test "local metadata" synchronization between separate RunEngineRedisDicts.
    """
    redis_dict_1 = redis_dict_factory(
        re_md_channel_name="test_local_metadata_synchronization"
    )
    redis_dict_2 = redis_dict_factory(
        re_md_channel_name="test_local_metadata_synchronization"
    )
    redis_dict_2_subscriber = _build_redis_subscriber(redis_dict_2)

    # make one change
    redis_dict_1["string"] = "string"
    redis_dict_1["int"] = 0
    redis_dict_1["float"] = np.pi
    redis_dict_1["array"] = np.ones((10, 10))

    time.sleep(1)
    redis_dict_2_messages = _get_waiting_messages(redis_dict_2_subscriber)
    assert len(redis_dict_2_messages) == 4

    assert redis_dict_2["string"] == "string"
    assert redis_dict_2["int"] == 0
    assert redis_dict_2["float"] == np.pi
    assert np.array_equal(redis_dict_2["array"], np.ones((10, 10)))

    redis_dict_3 = redis_dict_factory(
        re_md_channel_name="test_local_metadata_synchronization"
    )
    assert redis_dict_3["string"] == "string"
    assert redis_dict_3["int"] == 0
    assert redis_dict_3["float"] == np.pi
    assert np.array_equal(redis_dict_3["array"], np.ones((10, 10)))
