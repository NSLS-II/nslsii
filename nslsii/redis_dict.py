from collections.abc import MutableMapping

import msgpack
import msgpack_numpy
import redis


class RedisDict(MutableMapping):
    """
    A MutableMapping which syncs it contents to a Redis server.
    """

    RUNENGINE_METADATA_BLOB_KEY = "runengine-metadata-blob"

    def __init__(self, host="localhost", port=6379, db=0, re_md_channel_name="runengine-metadata", global_keys=None):
        self._host = host
        self._port = port
        self._db = db
        self._re_md_channel_name = re_md_channel_name

        self._redis_command_client = redis.Redis(
            host=host, port=port, db=db,
        )
        # ping() will raise redis.exceptions.ConnectionError on failure
        self._redis_command_client.ping()

        self._redis_pubsub_client = redis.Redis(
            host=host, port=port, db=db
        )
        self._redis_pubsub_client.ping()
        self._redis_pubsub = self._redis_pubsub_client.pubsub(ignore_subscribe_messages=True)
        self._redis_pubsub.subscribe(self._re_md_channel_name)

        if global_keys is None:
            # present at all NSLS-II beamlines
            self._global_keys = {
                "proposal_id",
                "data_session",
                "cycle",
                "SAF",
                "scan_id",
            }

        # is there already a local_md in redis?
        packed_local_md = self._redis_command_client.get(self._re_md_channel_name)
        if packed_local_md is None:
            self._local_md = dict()
            self._redis_command_client.set(self.RUNENGINE_METADATA_BLOB_KEY, self._pack(self._local_md))
        else:
            self._local_md = self._unpack(packed_local_md)

        # what if the global keys do not exist?
        for global_key in self._global_keys:
            value = self._redis_command_client.get(global_key)
            if value is None:
                self._redis_command_client.set(global_key, -1)

    def __setitem__(self, key, value):
        if key in self._global_keys:
            # TODO: cache the global metadata?
            self._redis_command_client.set(key, value=value)
        else:
            # have any keys changed?
            self._update_local_md()

            self._local_md[key] = value
            self._redis_command_client.set(self.RUNENGINE_METADATA_BLOB_KEY, value=self._pack(self._local_md))

        # tell everyone else a key-value has changed
        print(f"publishing change to key {key}:{value}")
        self._redis_pubsub_client.publish(channel=self._re_md_channel_name, message=key)

    def __getitem__(self, key):
        print(f"__getitem({key})__")
        if key in self._global_keys:
            value = self._redis_command_client.get(key)
            if value is None:
                raise KeyError(key)
        else:
            self._update_local_md()

            value = self._local_md[key]

        return value

    def __delitem__(self, key):
        if key in self._global_keys:
            raise KeyError(f"can not delete global key {key}")
        else:
            self._update_local_md()

            del self._local_md[key]
            self._redis_command_client.set(self.RUNENGINE_METADATA_BLOB_KEY, self._pack(self._local_md))

        # tell everyone a local key-value has changed
        self._redis_pubsub_client.publish(channel=self._re_md_channel_name, message=key)

    def __iter__(self):
        raise NotImplementedError()

    def __len__(self):
        raise NotImplementedError()

    def _get_waiting_messages(self):
        message_list = []
        message = self._redis_pubsub.get_message()
        while message is not None:
            message_list.append(message)
            message = self._redis_pubsub.get_message()

        print(f"_get_waiting_messages() returning\n{message_list}")
        return message_list

    def _update_local_md(self):
        """If necessary, update the local_md dictionary
        """
        message_list = self._get_waiting_messages()

        if len(message_list) > 0:
            print("_update_local_md is updating _local_md")
            self._local_md = self._unpack(self._redis_command_client.get(self.RUNENGINE_METADATA_BLOB_KEY))

        return len(message_list)

    @staticmethod
    def _pack(obj):
        "Encode as msgpack using numpy-aware encoder."
        # See https://github.com/msgpack/msgpack-python#string-and-binary-type
        # for more on use_bin_type.
        return msgpack.packb(obj, default=msgpack_numpy.encode, use_bin_type=True)

    @staticmethod
    def _unpack(obj):
        return msgpack.unpackb(obj, object_hook=msgpack_numpy.decode, raw=False)

    # def flush(self):
    #     """Force a write of the current state to disk"""
    #     for k, v in self.items():
    #         super().__setitem__(k, v)

    # does this make sense for redis?
    def reload(self):
        """Force a reload from redis, overwriting current cache"""
        # self._cache = dict(super().items())
        pass
