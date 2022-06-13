import time

import pytest

import redis
import redis.exceptions

from nslsii.redis_dict import RedisDict


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


def test_instantiate_good(redis_dict_factory):
    redis_dict = redis_dict_factory(re_md_channel_name="test_instantiate_good")
    assert redis_dict["proposal_id"] == b"-1"


def test_instantiate_bad():
    with pytest.raises(redis.exceptions.ConnectionError):
        # there is no redis server on port 9999
        RedisDict(host="localhost", port=9999)


def test_one_message(redis_dict_factory):
    redis_dict = redis_dict_factory(re_md_channel_name="test_one_message")

    redis_subscriber = _build_redis_subscriber(redis_dict)

    # remove any waiting messages
    _get_waiting_messages(redis_subscriber)
    # should be no messages left
    messages = _get_waiting_messages(redis_subscriber)
    assert len(messages) == 0

    redis_dict["generate_one_message"] = 1

    messages = _get_waiting_messages(redis_subscriber)
    assert len(messages) == 1


def test_two_messages(redis_dict_factory):
    redis_dict = redis_dict_factory(re_md_channel_name="test_one_message")

    redis_subscriber = _build_redis_subscriber(redis_dict)

    # remove any waiting messages
    _get_waiting_messages(redis_subscriber)
    # should be no messages left
    messages = _get_waiting_messages(redis_subscriber)
    assert len(messages) == 0

    redis_dict["generate_one_message"] = 1
    redis_dict["generate_another_message"] = 2

    messages = _get_waiting_messages(redis_subscriber)
    assert len(messages) == 2


def test_global_key(redis_dict_factory):
    redis_dict = redis_dict_factory(re_md_channel_name="test_global_key")
    redis_dict["proposal_id"] = "ABC123"
    redis_dict["proposal_id"] == "ABC123"


def test_local_key(redis_dict_factory):
    redis_dict = redis_dict_factory(re_md_channel_name="test_local_key")

    # there may be old messages from a previous test run
    old_messages = redis_dict._get_waiting_messages()
    print(f"flushed old messages: {old_messages}")

    redis_dict["local"] = "normal"

    # does redis_dict receive publications for its own changes?
    # looks like it does
    new_messages = redis_dict._get_waiting_messages()
    assert len(new_messages) == 1


def test_local_int_value(redis_dict_factory):
    redis_dict = redis_dict_factory(re_md_channel_name="test_local_int_value")

    redis_dict["local_int"] = -1

    assert redis_dict["local_int"] == -1


def test_local_float_value(redis_dict_factory):
    redis_dict = redis_dict_factory(re_md_channel_name="test_local_int_value")

    import math
    redis_dict["local_float"] = math.pi

    assert redis_dict["local_float"] == math.pi


# def test_synchronization_messages_1(redis_dict_factory):
#     """
#     create two redis_dicts at the same time
#     """
#     redis_dict_1 = redis_dict_factory(re_md_channel_name="test_synchronization")
#     redis_dict_2 = redis_dict_factory(re_md_channel_name="test_synchronization")
#
#     # remove any waiting messages
#     redis_dict_1._get_waiting_messages()
#     redis_dict_2._get_waiting_messages()
#     # should be no messages left
#     messages_1 = redis_dict_1._get_waiting_messages()
#     messages_2 = redis_dict_2._get_waiting_messages()
#     assert len(messages_1) == 0
#     assert len(messages_2) == 0
#
#     # make one change
#     redis_dict_1["one"] = "one"
#     #redis_dict_1["two"] = "two"
#
#     # does redis_dict_1 get a notification about its own update?
#     messages_1 = redis_dict_1._get_waiting_messages()
#     assert len(messages_1) == 1
#
#     # does redis_dict_2 get a notification about the update?
#     messages_2 = redis_dict_2._get_waiting_messages()
#     assert len(messages_2) == 1


def test_synchronization_2(redis_dict_factory):
    """
    create two redis_dicts at the same time
    """
    redis_dict_1 = redis_dict_factory(re_md_channel_name="test_synchronization_2")
    redis_dict_2 = redis_dict_factory(re_md_channel_name="test_synchronization_2")

    # make one change
    redis_dict_1["one"] = "two"
    time.sleep(2)
    assert redis_dict_2["one"] == "two"
