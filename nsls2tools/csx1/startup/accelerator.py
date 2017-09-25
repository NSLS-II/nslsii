from ophyd import (PVPositioner, PVPositionerPC, Device,
                   EpicsSignal, EpicsSignalRO)
from ophyd import Component as Cpt
from ophyd import FormattedComponent as FmCpt

# Undulator

class GapMotor1(PVPositionerPC):
    readback = Cpt(EpicsSignalRO, 'Pos-I')
    setpoint = Cpt(EpicsSignal, 'Pos-SP')
    stop_signal = FmCpt(EpicsSignal,
                        'SR:C23-ID:G1A{EPU:1-Ax:Gap}-Mtr.STOP', add_prefix=())
    stop_value = 1


class PhaseMotor1(PVPositionerPC):
    readback = Cpt(EpicsSignalRO, 'Pos-I')
    setpoint = Cpt(EpicsSignal, 'Pos-SP')
    stop_signal = FmCpt(EpicsSignal,
                        'SR:C23-ID:G1A{EPU:1-Ax:Phase}-Mtr.STOP', add_prefix=())
    stop_value = 1


class GapMotor2(PVPositionerPC):
    readback = Cpt(EpicsSignalRO, 'Pos-I')
    setpoint = Cpt(EpicsSignal, 'Pos-SP')
    stop_signal = FmCpt(EpicsSignal,
                        'SR:C23-ID:G1A{EPU:2-Ax:Gap}-Mtr.STOP', add_prefix=())
    stop_value = 1


class PhaseMotor2(PVPositionerPC):
    readback = Cpt(EpicsSignalRO, 'Pos-I')
    setpoint = Cpt(EpicsSignal, 'Pos-SP')
    stop_signal = FmCpt(EpicsSignal,
                        'SR:C23-ID:G1A{EPU:2-Ax:Phase}-Mtr.STOP', add_prefix=())

    stop_value = 1


class EPU1(Device):
    gap = Cpt(GapMotor1, '-Ax:Gap}')
    phase = Cpt(PhaseMotor1, '-Ax:Phase}')


class EPU2(Device):
    gap = Cpt(GapMotor2, '-Ax:Gap}')
    phase = Cpt(PhaseMotor2, '-Ax:Phase}')


epu1 = EPU1('XF:23ID-ID{EPU:1', name='epu1')
epu2 = EPU2('XF:23ID-ID{EPU:2', name='epu2')


