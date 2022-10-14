import logging
import re
from collections import ChainMap, UserDict
from uuid import uuid4

import msgpack
import msgpack_numpy
import redis


msgpack_numpy.patch()

redis_dict_log = logging.getLogger("nslsii.md_dict.RunEngineRedisDict")


class RunEngineRedisDict(UserDict):
    """
    A class for storing RunEngine metadata added to RE.md on a Redis server.

    This class has two strong ideas about the metadata it manages:
      1. Some key-values are considered "global" or "facility-wide". These
         are in use at all NSLS-II bluesky beamlines and include
         proposal_id, data_session, cycle, saf_id, and scan_id. The "global"
         key-values are stored as Redis key-values. Redis does not support
         numeric types, so the RunEngineRedisDict also keeps track of the
         types of the "global" key-values. The intention is that this
         metadata is accessible by any Redis client.
      2. Non-global, or beamline-specific, metadata is stored in Redis as
         a msgpack-ed blob. This means data type conversion between Redis
         and Python is handled by msgpack, including numpy arrays.
         The drawback is that this "local" metadata key-values are not
         directly readable or writeable by Redis clients.
    """

    PACKED_RUNENGINE_METADATA_KEY = "runengine-metadata-blob"

    def __init__(
        self,
        host="localhost",
        port=6379,
        db=0,
        re_md_channel_name="runengine-metadata",
        global_keys=None,
        global_values_types=None,
    ):
        # send no initial data to UserDict.__init__
        # since we will replace UserDict.data entirely
        # with a ChainMap
        super().__init__()
        self._host = host
        self._port = port
        self._db = db
        self._re_md_channel_name = re_md_channel_name
        self._uuid = str(uuid4())

        redis_dict_log.info("connecting to Redis at %s:%s", self._host, self._port)
        # global metadata will be stored as Redis key-value pairs
        # tell the global metadata Redis client to do bytes-to-str conversion
        self._redis_global_client = redis.Redis(
            host=host, port=port, db=db, decode_responses=True
        )
        # ping() will raise redis.exceptions.ConnectionError on failure
        self._redis_global_client.ping()

        # local metadata will be msgpack-ed, so decoding
        # will be handled by msgpack.unpackb()
        # tell the local metadata Redis client to do NO bytes-to-str conversion
        self._redis_local_client = redis.Redis(
            host=host, port=port, db=db, decode_responses=False
        )
        self._redis_local_client.ping()

        if global_keys is None:
            # "global" key-value pairs are
            # present at all NSLS-II beamlines
            self._global_keys = (
                "proposal_id",
                "data_session",
                "cycle",
                "saf_id",
                "scan_id",
            )
        else:
            self._global_keys = global_keys

        if global_values_types is None:
            # remember numeric types for global metadata
            # global metadata keys not specified here will default to str
            self._global_values_types = {"scan_id": int}
        else:
            self._global_values_types = global_values_types

        # is local metadata already in redis?
        packed_local_md = self._redis_local_client.get(
            self.PACKED_RUNENGINE_METADATA_KEY
        )
        if packed_local_md is None:
            redis_dict_log.info("no local metadata found in Redis")
            self._local_md = dict()
            self._set_local_metadata_on_server()
        else:
            redis_dict_log.info("unpacking local metadata from Redis")
            self._local_md = self._get_local_metadata_from_server()
            redis_dict_log.debug("unpacked local metadata:\n%s", self._local_md)

        self._global_md = dict()
        for global_key in self._global_keys:
            global_value = self._redis_global_client.get(global_key)
            if global_value is None:
                # if a global key does not exist on the Redis server
                # then it will not exist in the RunEngineRedisDict
                redis_dict_log.info("no value yet for global key %s", global_key)
            else:
                if global_key in self._global_values_types:
                    global_value = self._global_values_types[global_key](global_value)
                self._global_md[global_key] = global_value
        redis_dict_log.info("global metadata: %s", self._global_md)

        # when self._local_md has to be replaced with the metadata
        # blob in Redis we must be careful to replace the first
        # dict in the ChainMap's list of mappings
        self.data = ChainMap(self._local_md, self._global_md)

        # Redis documentation says do not issue commands from
        # a client that has been used to subscribe to a channel
        # so create a client just for subscribing
        self._redis_pubsub_client = redis.Redis(host=host, port=port, db=db)
        self._redis_pubsub_client.ping()
        self._redis_pubsub = self._redis_pubsub_client.pubsub(
            ignore_subscribe_messages=True
        )

        # register self._handle_update_message to handle Redis messages
        # this is how the RunEngineMetadataDict knows a key-value
        # has been modified on the Redis server, and therefore
        # self._local_md must be updated from the server
        self._redis_pubsub.subscribe(
            **{self._re_md_channel_name: self._handle_update_message}
        )
        # start a thread to pass messages to _update_on_message
        self._update_on_message_thread = self._redis_pubsub.run_in_thread(
            sleep_time=0.01, daemon=True
        )

    def __setitem__(self, key, value):
        if key in self._global_keys:
            # can't rely on self._global_md for this check because
            # if global metadata is not in Redis it is not added to self._global_md
            redis_dict_log.debug("setting global metadata %s:%s", key, value)
            # global metadata may be constrained to be of a certain type
            # check that value does not violate the type expected for key
            expected_value_type = self._global_values_types.get(key, str)
            if isinstance(value, expected_value_type):
                # everything is good
                pass
            else:
                raise ValueError(
                    f"expected value for key '{key}' to have type '{expected_value_type}'"
                    f"but '{value}' has type '{type(value)}'"
                )
            # update the global key-value pair explicitly in self._global_md
            # because it can not be updated through the self.data ChainMap
            # since self._global_md is not the first dictionary in that ChainMap
            self._global_md[key] = value
            # update the global key-value pair on the Redis server
            self._redis_global_client.set(name=key, value=value)
        else:
            redis_dict_log.debug("setting local metadata %s:%s", key, value)
            # update the key-value pair in the ChainMap
            super().__setitem__(key, value)
            # update the local key-value pair on the Redis server
            self._redis_local_client.set(
                name=self.PACKED_RUNENGINE_METADATA_KEY,
                value=self._pack(self._local_md),
            )

        # tell subscribers a key-value has changed
        redis_dict_log.debug("publishing update %s:%s", key, value)
        self._publish_metadata_update_message(key)

    def __delitem__(self, key):
        if key in self._global_keys:
            raise KeyError(f"deleting key {key} is not allowed")
        else:
            del self._local_md[key]
            self._set_local_metadata_on_server()

        # tell everyone a (local) key-value has been changed
        self._publish_metadata_update_message(key)

    def _publish_metadata_update_message(self, key):
        """
        Publish a message that includes the updated key and
        the identifying UUID for this RunEngineRedisDict.
        The UUID in the message will allow this RunEngineRedisDict
        to ignore updates that come from itself.
        """
        self._redis_pubsub_client.publish(
            channel=self._re_md_channel_name, message=f"{key}:{self._uuid}"
        )

    def _get_local_metadata_from_server(self):
        return self._unpack(
            self._redis_local_client.get(name=self.PACKED_RUNENGINE_METADATA_KEY)
        )

    def _set_local_metadata_on_server(self):
        self._redis_local_client.set(
            self.PACKED_RUNENGINE_METADATA_KEY, self._pack(self._local_md)
        )

    _message_data_pattern = re.compile(r"^(?P<key>.+):(?P<uuid>.+)$")

    @classmethod
    def _parse_message_data(klass, message):
        """
        message["data"] should look like this
            b"abc:39f1f7fa-aeef-4d83-a802-c1c7f5ff5cb8"
        Splitting the message on ":" gives the updated key
        ("abc" in this example) and the UUID of the RunEngineRedisDict
        that made the update. The UUID is used to determine if
        the update message came from this RunEngineRedisDict, in
        which case it is not necessary to update the local metadata
        from the Redis server.
        """
        decoded_message_data = message["data"].decode()
        message_data_match = klass._message_data_pattern.match(decoded_message_data)

        if message_data_match is None:
            raise ValueError(
                f"message[data]=`{decoded_message_data}` could not be parsed"
            )
        return message_data_match.group("key"), message_data_match.group("uuid")

    def _handle_update_message(self, message):
        redis_dict_log.debug("_update_on_message: %s", message)
        updated_key, publisher_uuid = self._parse_message_data(message)
        if publisher_uuid == self._uuid:
            # this RunEngineRedisDict is the source of this update message,
            # so there is no need to go to the Redis server for the new metadata
            redis_dict_log.debug("update published by me!")
        elif updated_key in self._global_keys:
            redis_dict_log.debug("updated key belongs to global metadata")
            # because the updated_key belongs to "global" metadata
            # we can assume it is not a new or deleted key, so just
            # get the key's value from the Redis database and convert
            # its type if necessary (eg, from string to int)
            updated_value = self._redis_global_client.get(name=updated_key)
            if updated_key in self._global_values_types:
                updated_value = self._global_values_types[updated_key](updated_value)
            self._global_md[updated_key] = updated_value
        else:
            redis_dict_log.debug("updated key belongs to local metadata")
            # the updated key belongs to local metadata
            # it may be a newly added or deleted key, so
            # we have to update the entire local metadata dictionary
            self._local_md = self._get_local_metadata_from_server()
            # update the ChainMap - "local" metadata is always the
            # first element in ChainMap.maps
            self.data.maps[0] = self._local_md

    @staticmethod
    def _pack(obj):
        """Encode as msgpack using numpy-aware encoder."""
        return msgpack.packb(obj)

    @staticmethod
    def _unpack(obj):
        return msgpack.unpackb(obj)
