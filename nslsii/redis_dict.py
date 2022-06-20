from collections import ChainMap, UserDict
from pprint import pformat
from uuid import uuid4

import msgpack
import msgpack_numpy
import redis


msgpack_numpy.patch()


class RunEngineRedisDict(UserDict):
    PACKED_RUNENGINE_METADATA_KEY = "runengine-metadata-blob"

    def __init__(
        self,
        host="localhost",
        port=6379,
        db=0,
        re_md_channel_name="runengine-metadata",
        global_keys=None,
    ):
        # send no initial data to UserDict.__init__
        # since we will replace UserDict.data entirely
        super().__init__()
        self._host = host
        self._port = port
        self._db = db
        self._re_md_channel_name = re_md_channel_name
        self._uuid = str(uuid4())

        # global metadata will be stored as Redis key-value pairs
        # tell the global Redis client to do bytes-to-str conversion
        self._redis_global_client = redis.Redis(
            host=host, port=port, db=db, decode_responses=True
        )
        self._redis_global_client.ping()

        # local metadata will be msgpack-ed, so decoding
        # will be handled by msgpack.unpackb()
        # tell the local metadata Redis client to do NO bytes-to-str conversion
        self._redis_local_client = redis.Redis(
            host=host, port=port, db=db, decode_responses=False
        )
        # ping() will raise redis.exceptions.ConnectionError on failure
        self._redis_local_client.ping()

        if global_keys is None:
            # present at all NSLS-II beamlines
            self._global_keys = (
                "proposal_id",
                "data_session",
                "cycle",
                "SAF",
                "scan_id",
            )

        # is local metadata already in redis?
        packed_local_md = self._redis_local_client.get(
            self.PACKED_RUNENGINE_METADATA_KEY
        )
        if packed_local_md is None:
            print(f"no local metadata in Redis yet")
            self._local_md = dict()
            self._set_local_metadata_on_server()
        else:
            print(f"unpacking local metadata")
            self._local_md = self._get_local_metadata_from_server()  #self._unpack(packed_local_md)
            print(f"unpacked local metadata:\n{pformat(self._local_md)}")

        # what if the global keys do not exist?
        # could get all Redis keys and exclude the local md blob key ?
        self._global_md = dict()
        for global_key in self._global_keys:
            value = self._redis_global_client.get(global_key)
            if value is None:
                print(f"no value yet for global key {global_key}")
                self._redis_global_client.set(name=global_key, value=global_key)
            self._global_md[global_key] = value
        print(f"global metadata:\n{pformat(self._global_md)}")

        # keep in mind the first dict is _local_md
        # for when _local_md has to be replaced
        self.data = ChainMap(self._local_md, self._global_md)

        self._redis_pubsub_client = redis.Redis(host=host, port=port, db=db)
        self._redis_pubsub_client.ping()
        self._redis_pubsub = self._redis_pubsub_client.pubsub(
            ignore_subscribe_messages=True
        )
        self._redis_pubsub.subscribe(
            **{self._re_md_channel_name: self._update_on_message}
        )
        self._update_on_message_thread = self._redis_pubsub.run_in_thread(
            sleep_time=0.01
        )

    def __setitem__(self, key, value):
        if key in self._global_md:
            print(f"setting global metadata {key}: {value}")
            self._global_md[key] = value
            self._redis_global_client.set(name=key, value=value)
        else:
            print(f"setting local metadata {key}: {value}")
            super().__setitem__(key, value)
            self._redis_local_client.set(
                name=self.PACKED_RUNENGINE_METADATA_KEY,
                value=self._pack(self._local_md),
            )

        # tell everyone else a key-value has changed
        print(f"publishing update {key}: {value}")
        self._publish_metadata_update(key)

    def __delitem__(self, key):
        if key in self._global_keys:
            raise KeyError(f"can not delete global key {key}")
        else:
            del self._local_md[key]
            self._set_local_metadata_on_server()

        # tell everyone a local key-value has changed
        self._publish_metadata_update(key)

    def _publish_metadata_update(self, key):
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

    @staticmethod
    def _parse_message_data(message):
        # expect message["data"] to look like b"abd:39f1f7fa-aeef-4d83-a802-c1c7f5ff5cb8"
        message_key, publisher_uuid = message["data"].rsplit(b":", maxsplit=1)
        return message_key.decode(), publisher_uuid.decode()

    def _update_on_message(self, message):
        print(f"_update_on_message: {pformat(message)}")
        updated_key, publisher_uuid = self._parse_message_data(message)
        print(f"my uuid: {self._uuid}")
        print(f"publisher_uuid: {publisher_uuid}")
        if publisher_uuid == self._uuid:
            print(f"update published by me!")
            pass
        elif updated_key in self._global_keys:
            print(f"updated key belongs to global metadata")
            # we can assume the updated_key is not a new key
            # get the key from the Redis database
            self._global_md[updated_key] = self._redis_global_client.get(
                name=updated_key
            )
        else:
            print(f"updated key belongs to local metadata")
            # assume the updated key belongs to local metadata
            # it may be a newly added key, so we have to update
            # the entire local metadata dictionary
            self._local_md = self._get_local_metadata_from_server()
            # update the ChainMap
            self.data.maps[0] = self._local_md

    @staticmethod
    def _pack(obj):
        """Encode as msgpack using numpy-aware encoder."""
        # See https://github.com/msgpack/msgpack-python#string-and-binary-type
        # for more on use_bin_type.
        return msgpack.packb(obj)

    @staticmethod
    def _unpack(obj):
        return msgpack.unpackb(obj)
