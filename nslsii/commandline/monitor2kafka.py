"""
caproto-monitor-to-kafka ...

It can equivalently be invoked as:

python3 -m nslsii.commandline.monitor2kafka ...

For access to the underlying functionality from a Python script or interactive
Python session, do not import this module; instead import caproto.sync.client.
"""
import argparse
from caproto.sync.client import subscribe, block
from caproto import SubscriptionType, __version__
import msgpack
import msgpack_numpy as mpn
from confluent_kafka import Producer


def main():
    parser = argparse.ArgumentParser(
        description="Publish a PV monitor to a kafka topic.",
        epilog=f"caproto version {__version__}",
    )
    exit_group = parser.add_mutually_exclusive_group()
    parser.add_argument(
        "kafka_server", type=str, help="bootstrap server to connect to."
    )
    parser.add_argument("topic", type=str, help="The topic to publish to.")

    parser.add_argument("pv_names", type=str, nargs="+", help="PV (channel) name")

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        help="Show more log messages. (Use -vvv for even more.)",
    )
    exit_group.add_argument(
        "--duration",
        type=float,
        default=None,
        help=(
            "Maximum number seconds to run before "
            "exiting. Runs indefinitely by default."
        ),
    )
    exit_group.add_argument(
        "--maximum",
        type=int,
        default=None,
        help=(
            "Maximum number of monitor events to "
            "process exiting. Unlimited by "
            "default."
        ),
    )
    parser.add_argument(
        "--timeout",
        "-w",
        type=float,
        default=1,
        help=("Timeout ('wait') in seconds for server " "responses."),
    )
    parser.add_argument(
        "-m",
        type=str,
        metavar="MASK",
        default="va",
        help=(
            "Channel Access mask. Any combination of "
            "'v' (value), 'a' (alarm), 'l' (log/archive), "
            "'p' (property). Default is 'va'."
        ),
    )
    parser.add_argument(
        "--priority",
        "-p",
        type=int,
        default=0,
        help="Channel Access Virtual Circuit priority. " "Lowest is 0; highest is 99.",
    )
    parser.add_argument(
        "-n",
        action="store_true",
        help=("Retrieve enums as integers (default is " "strings)."),
    )
    parser.add_argument(
        "--no-repeater",
        action="store_true",
        help=("Do not spawn a Channel Access repeater daemon " "process."),
    )

    args = parser.parse_args()

    mask = 0
    if "v" in args.m:
        mask |= SubscriptionType.DBE_VALUE
    if "a" in args.m:
        mask |= SubscriptionType.DBE_ALARM
    if "l" in args.m:
        mask |= SubscriptionType.DBE_LOG
    if "p" in args.m:
        mask |= SubscriptionType.DBE_PROPERTY

    tokens = {"callback_count": 0}
    producer = Producer({"bootstrap.servers": args.kafka_server})

    def callback(sub, response):
        tokens["callback_count"] += 1
        payload = {
            "pvname": sub.pv_name,
            **{k: getattr(response, k) for k in ("data", "data_count", "data_type")},
            "medatadata": {
                k: getattr(response.metadata, k)
                for k in ("status", "severity", "timestamp")
            },
        }
        msg = msgpack.dumps(payload, default=mpn.encode)
        producer.produce(topic=args.topic, key=sub.pv_name, value=msg)

        if args.maximum is not None:
            if tokens["callback_count"] >= args.maximum:
                raise KeyboardInterrupt()

    try:
        subs = []
        cbs = []
        for pv_name in args.pv_names:
            sub = subscribe(pv_name, mask=mask, priority=args.priority)
            sub.add_callback(callback)
            cbs.append(callback)  # Hold ref to keep it from being garbage collected.
            subs.append(sub)
        # Wait to be interrupted by KeyboardInterrupt.
        block(
            *subs,
            duration=args.duration,
            timeout=args.timeout,
            force_int_enums=args.n,
            repeater=not args.no_repeater,
        )
    except BaseException as exc:
        if args.verbose:
            # Show the full traceback.
            raise
        else:
            # Print a one-line error message.
            print(exc)


if __name__ == "__main__":
    main()
