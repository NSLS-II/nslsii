#!/usr/bin/env python3
from caproto.server import PVGroup, ioc_arg_parser, run

from epics_motor_record import EpicsMotorRecord


class MotorGroupIOC(PVGroup):
    """
    Simulates a group of EPICS motor records.
    """

    def __init__(self, prefix, *, groups, **kwargs):
        super().__init__(prefix, **kwargs)
        self.groups = groups


def create_ioc(prefix, axes, **ioc_options):

    groups = {}

    ioc = MotorGroupIOC(prefix=prefix, groups=groups, **ioc_options)

    for group_prefix in axes:
        groups[group_prefix] = EpicsMotorRecord(f'{prefix}{group_prefix}',
                                                ioc=ioc)

    for prefix, group in groups.items():
        ioc.pvdb.update(**group.pvdb)

    return ioc


if __name__ == '__main__':
    ioc_options, run_options = ioc_arg_parser(
        default_prefix='test-Ax:',
        desc=MotorGroupIOC.__doc__,
    )

    axes = {"HGMtr", "HCMtr", "VGMtr", "VCMtr",
            "IMtr", "OMtr", "TMtr", "BMtr",}

    ioc = create_ioc(axes=axes, **ioc_options)

    run(ioc.pvdb, **run_options)
