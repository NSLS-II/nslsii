from ophyd import (EpicsMotor, Device, EpicsSignal, EpicsSignalRO,
                   PVPositioner)
from ophyd.device import Component as Cpt
from ophyd.device import FormattedComponent as FmtCpt

class FMBHexapodMirrorAxis(PVPositioner):
    readback = Cpt(EpicsSignalRO, 'Mtr_MON')
    setpoint = Cpt(EpicsSignal, 'Mtr_POS_SP')
    actuate = FmtCpt(EpicsSignal, '{self.parent.prefix}}}MOVE_CMD.PROC')
    actual_value = 1
    stop_signal = FmtCpt(EpicsSignal, '{self.parent.prefix}}}STOP_CMD.PROC')
    stop_value = 1
    done = FmtCpt(EpicsSignalRO, '{self.parent.prefix}}}BUSY_STS')
    done_value = 0


class FMBHexapodMirror(Device):
    z = Cpt(FMBHexapodMirrorAxis, '-Ax:Z}')
    y = Cpt(FMBHexapodMirrorAxis, '-Ax:Y}')
    x = Cpt(FMBHexapodMirrorAxis, '-Ax:X}')
    pit = Cpt(FMBHexapodMirrorAxis, '-Ax:Pit}')
    yaw = Cpt(FMBHexapodMirrorAxis, '-Ax:Yaw}')
    rol = Cpt(FMBHexapodMirrorAxis, '-Ax:Rol}')


class SlitsGapCenter(Device):
    xg = Cpt(EpicsMotor, '-Ax:XGap}Mtr')
    xc = Cpt(EpicsMotor, '-Ax:XCtr}Mtr')
    yg = Cpt(EpicsMotor, '-Ax:YGap}Mtr')
    yc = Cpt(EpicsMotor, '-Ax:YCtr}Mtr')


class SlitsXY(Device):
    x = Cpt(EpicsMotor, '-Ax:X}Mtr', name='x')
    y = Cpt(EpicsMotor, '-Ax:Y}Mtr', name='y')


