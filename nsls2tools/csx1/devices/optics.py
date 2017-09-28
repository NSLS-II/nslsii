from ophyd import (EpicsMotor, PVPositioner, PVPositionerPC,
                   EpicsSignal, EpicsSignalRO, Device)
from ophyd import Component as Cpt
from ophyd import FormattedComponent as FmtCpt
from ophyd import DynamicDeviceComponent as DDC
from ophyd import (EpicsMCA, EpicsDXP)
from ophyd import DeviceStatus, OrderedDict

class M3AMirror(Device):
    "a mirror with EpicsMotors, used for M3A"
    x = Cpt(EpicsMotor, '-Ax:XAvg}Mtr')
    pit = Cpt(EpicsMotor, '-Ax:P}Mtr')
    bdr = Cpt(EpicsMotor, '-Ax:Bdr}Mtr')


class PGMEnergy(PVPositionerPC):
    readback = Cpt(EpicsSignalRO, 'o}Enrgy-I')
    setpoint = Cpt(EpicsSignal, 'o}Enrgy-SP', limits=(200,2200))
    stop_signal = Cpt(EpicsSignal, 'o}Cmd:Stop-Cmd')
    stop_value = 1


class PGM(Device):
    energy = Cpt(PGMEnergy, '')
    mir_pit = Cpt(EpicsMotor, 'o-Ax:MirP}Mtr')
    mir_x = Cpt(EpicsMotor, 'o-Ax:MirX}Mtr')
    grt_pit = Cpt(EpicsMotor, 'o-Ax:GrtP}Mtr')
    grt_x = Cpt(EpicsMotor, 'o-Ax:GrtX}Mtr')

    mir_temp_in = FmtCpt(EpicsSignalRO, '{self._temp_pv}-Chan:A}}T-I')
    grt_temp_in = FmtCpt(EpicsSignalRO, '{self._temp_pv}-Chan:B}}T-I')
    mir_temp_out = FmtCpt(EpicsSignalRO, '{self._temp_pv}-Chan:C}}T-I')
    grt_temp_out = FmtCpt(EpicsSignalRO, '{self._temp_pv}-Chan:D}}T-I')

    grt1_temp = Cpt(EpicsSignalRO, '-Grt:1}T-I')
    grt2_temp = Cpt(EpicsSignalRO, '-Grt:2}T-I')
    grt3_temp = Cpt(EpicsSignalRO, '-Grt:3}T-I')
    grt4_temp = Cpt(EpicsSignalRO, '-Grt:4}T-I')

    def __init__(self, *args, temp_pv=None, **kwargs):
        self._temp_pv = temp_pv
        super().__init__(*args, **kwargs)


class PID(PVPositioner):
    readback = Cpt(EpicsSignalRO, 'PID-RB')
    setpoint = Cpt(EpicsSignal, 'PID-SP')
    done = Cpt(EpicsSignalRO, 'PID:Busy-Sts')
    done_value = 0

    output = Cpt(EpicsSignalRO, 'PID.OVAL')
    enable = Cpt(EpicsSignal, 'Sts:FB-Sel')


class SamplePosVirtualMotor(PVPositionerPC):
    readback = Cpt(EpicsSignalRO, 'Pos-RB')
    setpoint = Cpt(EpicsSignal, 'Pos-SP')
    #stop_signal = Cpt(EpicsSignal, 'Cmd:Stop-Cmd')
    stop_value = 1

class Cryoangle(PVPositionerPC):
    readback  = Cpt(EpicsSignalRO, 'XF:23ID1-ES{Dif-Cryo}Pos:Angle-RB')
    setpoint = Cpt(EpicsSignal, 'XF:23ID1-ES{Dif-Cryo}Pos:Angle-SP')
    # TODO original implementation had no stop_signal!!
    stop_value = 1


class Nanopositioner(Device):
    tx = Cpt(EpicsMotor, '-Ax:TopX}Mtr')
    ty = Cpt(EpicsMotor, '-Ax:TopY}Mtr')
    tz = Cpt(EpicsMotor, '-Ax:TopZ}Mtr')
    bx = Cpt(EpicsMotor, '-Ax:BtmX}Mtr')
    by = Cpt(EpicsMotor, '-Ax:BtmY}Mtr')
    bz = Cpt(EpicsMotor, '-Ax:BtmZ}Mtr')


