from pprint import pformat
import time

import pytest

import redis
import redis.exceptions

from nslsii.redis_dict import RunEngineRedisDict


def _build_redis_subscriber(redis_dict):
    redis_subscriber = redis.Redis(
        host=redis_dict._host,
        port=redis_dict._port,
        db=redis_dict._db
    ).pubsub(ignore_subscribe_messages=True)
    redis_subscriber.subscribe(redis_dict._re_md_channel_name)
    return redis_subscriber


def _get_waiting_messages(redis_subscriber):
    message_list = []
    message = redis_subscriber.get_message()
    while message is not None:
        message_list.append(message)
        message = redis_subscriber.get_message()

    print(f"_get_waiting_messages() returning\n{message_list}")
    return message_list


def test_instantiate_with_server(redis_dict_factory):
    try:
        redis_dict = redis_dict_factory(re_md_channel_name="test_instantiate_with_server")
    finally:
        redis_dict._update_on_message_thread.stop()


def test_instantiate_no_server():
    with pytest.raises(redis.exceptions.ConnectionError):
        # there is no redis server on port 9999
        # note: __init__ fails before _update_on_message_thread is started
        # so there is no need to explicitly stop that thread in this test
        RunEngineRedisDict(host="localhost", port=9999)


def test_local_int_value(redis_dict_factory):
    try:
        redis_dict = redis_dict_factory(re_md_channel_name="test_local_int_value")
        redis_dict["local_int"] = -1
        assert redis_dict["local_int"] == -1
    finally:
        redis_dict._update_on_message_thread.stop()


def test_local_float_value(redis_dict_factory):
    try:
        redis_dict = redis_dict_factory(re_md_channel_name="test_local_float_value")
        import math
        redis_dict["local_float"] = math.pi
        assert redis_dict["local_float"] == math.pi
    finally:
        redis_dict._update_on_message_thread.stop()


def test_del_global_key(redis_dict_factory):
    try:
        redis_dict = redis_dict_factory(re_md_channel_name="test_del_global_key")
        with pytest.raises(KeyError):
            del redis_dict[redis_dict._global_keys[0]]
    finally:
        redis_dict._update_on_message_thread.stop()


def test_del_local_key(redis_dict_factory):
    try:
        redis_dict = redis_dict_factory(re_md_channel_name="test_del_local_key")
        redis_dict["local_key"] = "local_value"
        assert redis_dict["local_key"] == "local_value"
        _local_md = redis_dict._get_local_metadata_from_server()
        assert _local_md["local_key"] == "local_value"
        del redis_dict["local_key"]
        _local_md = redis_dict._get_local_metadata_from_server()
        assert "local_key" not in _local_md
        assert "local_key" not in redis_dict
    finally:
        redis_dict._update_on_message_thread.stop()

def test_items(redis_dict_factory):
    """
    Test .items() starting from an empty Redis database.
    """
    try:
        redis_dict = redis_dict_factory(re_md_channel_name="test_items")

        # expect to find the global keys with value None
        expected_global_items = {gk: None for gk in redis_dict._global_keys}
        actual_global_items = {gk: gv for gk, gv in redis_dict.items()}
        assert actual_global_items == expected_global_items

        # set a value for each global key
        global_md_updates = {gk: gk for gk in redis_dict._global_keys}
        redis_dict.update(global_md_updates)
        actual_global_items = {gk: gv for gk, gv in redis_dict.items()}
        # _local_md should still be empty
        # since only global metadata was updated
        # this is not the behavior of ChainMap!
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
    finally:
        redis_dict._update_on_message_thread.stop()


def test_one_message(redis_dict_factory):
    try:
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
        while len(messages) == 0:
            messages = _get_waiting_messages(redis_subscriber)
        print(f"messages:\n {pformat(messages)}")
        assert len(messages) == 1
        updated_key, _ = redis_dict._parse_message_data(messages[0])
        assert updated_key == "generate_one_message"
    finally:
        redis_dict._update_on_message_thread.stop()


def test_two_messages(redis_dict_factory):
    try:
        redis_dict = redis_dict_factory(re_md_channel_name="test_two_messages")
        print(redis_dict._local_md)
        assert len(redis_dict._local_md) == 0

        redis_subscriber = _build_redis_subscriber(redis_dict)

        # should be no messages left
        messages = _get_waiting_messages(redis_subscriber)
        assert len(messages) == 0

        redis_dict["generate_one_message"] = 1
        redis_dict["generate_another_message"] = 2

        messages = _get_waiting_messages(redis_subscriber)
        while len(messages) == 0:
            messages = _get_waiting_messages(redis_subscriber)
        assert len(messages) == 2
        first_updated_key, _ = redis_dict._parse_message_data(messages[0])
        assert first_updated_key == "generate_one_message"
        second_updated_key, _ = redis_dict._parse_message_data(messages[1])
        assert second_updated_key == "generate_another_message"
    finally:
        redis_dict._update_on_message_thread.stop()


def test_synchronization(redis_dict_factory):
    """
    create two redis_dicts at the same time
    """
    try:
        redis_dict_1 = redis_dict_factory(re_md_channel_name="test_synchronization_2")
        redis_dict_2 = redis_dict_factory(re_md_channel_name="test_synchronization_2")
        redis_dict_2_subscriber = _build_redis_subscriber(redis_dict_2)

        # make one change
        redis_dict_1["one"] = "two"
        redis_dict_2_messages = _get_waiting_messages(redis_dict_2_subscriber)
        while len(redis_dict_2_messages) == 0:
            redis_dict_2_messages = _get_waiting_messages(redis_dict_2_subscriber)
        time.sleep(1)
        assert redis_dict_2["one"] == "two"
    finally:
        redis_dict_1._update_on_message_thread.stop()
        redis_dict_2._update_on_message_thread.stop()
