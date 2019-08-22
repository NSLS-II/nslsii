#!/usr/bin/env python3
from caproto.server import pvproperty, PVGroup
from caproto.server import ioc_arg_parser, run
from caproto import ChannelType
from textwrap import dedent


class IOC(PVGroup):
    """
    A Baton IOC for managing

    """

    baton = pvproperty(
        value="",
        dtype=ChannelType.STRING,
        doc='"baton" for running RE',
        mock_record="ai",
    )
    host = pvproperty(
        value="",
        dtype=ChannelType.STRING,
        doc="host name of computer running RE",
        mock_record="ai",
    )
    pid = pvproperty(
        value=0, doc="pid of running RE on host", mock_record="ai"
    )

    current_uid = pvproperty(
        value="",
        dtype=ChannelType.STRING,
        doc="Last finished uid.",
        mock_record="ai",
    )

    current_scanid = pvproperty(
        value=0, doc="Last finished scanid.", mock_record="ai"
    )

    state = pvproperty(
        value="unknown",
        doc="current state of RE",
        enum_strings=[
            "unknown",
            "idle",
            "running",
            "pausing",
            "paused",
            "halting",
            "stopping",
            "aborting",
            "suspending",
            "panicked",
        ],
        dtype=ChannelType.ENUM,
        mock_record="ai",
    )


def main():
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="XF31ID:", desc=dedent(IOC.__doc__)
    )

    ioc = IOC(**ioc_options)

    run(ioc.pvdb, **run_options)


if __name__ == "__main__":
    main()
