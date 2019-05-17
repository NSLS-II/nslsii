#!/usr/bin/env python3
from caproto.server import PVGroup, template_arg_parser, run

from nslsii.iocs.epics_motor_record import EpicsMotorRecord


class MotorGroupIOC(PVGroup):
    """
    Simulates a group of EPICS motor records.
    """

    def __init__(self, prefix, *, groups, **kwargs):
        super().__init__(prefix, **kwargs)
        self.groups = groups


def create_ioc(prefix, axes, **ioc_options):

    groups = {}

    mg_prefix = prefix.replace('{', '{'*2, 1)
    ioc = MotorGroupIOC(prefix=mg_prefix, groups=groups, **ioc_options)

    rec_mg_prefix = prefix.replace('{', '{'*4, 1)

    for group_prefix in axes:
        rec_group_prefix = group_prefix.replace('}', '}'*4, 1)
        record_prefix = rec_mg_prefix + rec_group_prefix
        groups[rec_group_prefix] = EpicsMotorRecord(record_prefix,
                                                    ioc=ioc)

    for prefix, group in groups.items():
        ioc.pvdb.update(**group.pvdb)

    return ioc


if __name__ == '__main__':

    parser, split_args = template_arg_parser(
        default_prefix='test{tst-Ax:',
        desc=MotorGroupIOC.__doc__,
    )

    axes_help = 'Comma-separated list of axes'

    parser.add_argument('--axes', help=axes_help,
                        required=True, type=str)

    args = parser.parse_args()
    ioc_options, run_options = split_args(args)

    axes = [x.strip() for x in args.axes.split(',')]

    ioc = create_ioc(axes=axes, **ioc_options)
    run(ioc.pvdb, **run_options)
