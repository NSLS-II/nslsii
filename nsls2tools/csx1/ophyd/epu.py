from ophyd import (PVPositioner, PVPositionerPC, Device,
                   EpicsSignal, EpicsSignalRO)
from ophyd import Component as Cpt
from ophyd import FormattedComponent as FmCpt

class EPUMotor(PVPositionerPC):
    readback = Cpt(EpicsSignalRO, 'Pos-I')
    setpoint = Cpt(EpicsSignal, 'Pos-SP')
    stop_signal = FmCpt(EpicsSignal,
                        '{self._stop_prefix}{self._stop_suffix}-Mtr.STOP')
    stop_value = 1

    def __init__(self, *args, parent=None, stop_suffix=None, **kwargs):
        self._stop_prefix = parent._epu_prefix
        self._stop_suffix = stop_suffix
        super().__init__(*args, parent=parent, **kwargs)

class EPU(Device):
    gap = Cpt(EPUMotor, '-Ax:Gap}', stop_suffix='-Ax:Gap}')
    phase = Cpt(EPUMotor, '-Ax:Phase}', stop_suffix='-Ax:Phase}')
    x_off = FmCpt(EpicsSignalRO,'{self._ai_prefix}:FPGA:x_mm-I')
    x_ang = FmCpt(EpicsSignalRO,'{self._ai_prefix}:FPGA:x_mrad-I')
    y_off = FmCpt(EpicsSignalRO,'{self._ai_prefix}:FPGA:y_mm-I')
    y_ang = FmCpt(EpicsSignalRO,'{self._ai_prefix}:FPGA:y_mrad-I')

    def __init__(self, *args, ai_prefix=None, epu_prefix=None, **kwargs):
        self._ai_prefix = ai_prefix
        self._epu_prefix = epu_prefix
        super().__init__(*args, **kwargs)

