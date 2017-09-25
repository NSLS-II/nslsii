from ophyd import (PVPositioner, PVPositionerPC, Device,
                   EpicsSignal, EpicsSignalRO)
from ophyd import Component as Cpt
from ophyd import FormattedComponent as FmCpt

# Undulator
                        'SR:C23-ID:G1A{EPU:1-Ax:Gap}-Mtr.STOP'

class EPU(Device):

class EPUMotor(PVPositionerPC):
    readback = Cpt(EpicsSignalRO, 'Pos-I')
    setpoint = Cpt(EpicsSignal, 'Pos-SP')
    stop_signal = FmCpt(EpicsSignal,
                        '{self._stop_prefix}{self._stop_suffix}-Mtr.STOP',
                        add_prefix=())
    stop_value = 1

    def __init__(self, suffix=None, *args, epu_prefix=None, **kwargs):
        self._stop_suffix = suffix
        self._stop_prefix = epu_prefix
        super().__init__(suffix, *args, epu_prefix=epu_prefix, **kwargs)


                        'SR:C23-ID:G1A{EPU:1-Ax:Phase}-Mtr.STOP', add_prefix=())

class EPU(Device):
    gap = FmCpt(EPUMotor, '-Ax:Gap}')
    phase = FmCpt(EPUMotor, '-Ax:Phase}')

epu1 = EPU('XF:23ID-ID{EPU:1', epu_prefix='SR:C23-ID:G1A{EPU:1', name='epu1')
epu2 = EPU('XF:23ID-ID{EPU:2', epu_prefix='SR:C23-ID:G1A{EPU:2', name='epu2')


