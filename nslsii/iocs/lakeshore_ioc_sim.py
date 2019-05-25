#!/usr/bin/env python3
from caproto.server import PVGroup, ioc_arg_parser, run

from nslsii.iocs.lakeshore_temperature import TemperatureRecord
from nslsii.iocs.lakeshore_control import ControlRecord


class LakeshoreIOC(PVGroup):
    """
    Simulates a Lakeshore IOC.
    """

    def __init__(self, prefix, *, groups, **kwargs):
        super().__init__(prefix, **kwargs)
        self.groups = groups


def create_ioc(prefix, temperatures, controls, **ioc_options):

    groups = {}

    ioc = LakeshoreIOC(prefix, groups=groups, **ioc_options)

    for t in temperatures:
        t_prefix = f'{prefix}-Chan:{t}'
        print('t_prefix:', t_prefix)
        groups[t_prefix] = TemperatureRecord(t_prefix, indx=t, ioc=ioc)

    for c in controls:
        c_prefix = f'{prefix}-Out:{c}'
        print('c_prefix:', c_prefix)
        groups[c_prefix] = ControlRecord(c_prefix, indx=c, ioc=ioc)

    for prefix, group in groups.items():
        ioc.pvdb.update(**group.pvdb)

    return ioc


if __name__ == '__main__':

    ioc_options, run_options = ioc_arg_parser(
        default_prefix='test:{{{{',
        desc='Lakeshore IOC.')

    temperatures = ['A', 'B', 'C', 'D']
    controls = [1, 2]

    ioc = create_ioc(temperatures=temperatures,
                     controls=controls,
                     **ioc_options)

    run(ioc.pvdb, **run_options)
