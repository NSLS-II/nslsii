from ophyd import (EpicsMotor, PVPositioner, PVPositionerPC,
                   EpicsSignal, EpicsSignalRO, Device)
from ophyd import Component as Cpt
from ophyd import FormattedComponent as FmtCpt

from ...common.ophyd.optics import (FMBHexapodMirror, SlitsGapCenter,
                                    SlitsXY)
from ...common.ophyd.eps import EPSTwoStateDevice

from ..ophyd.optics import (PGM, M3AMirror, PID)

# M1A, M1B1, M1B2

m1a = FMBHexapodMirror('XF:23IDA-OP:1{Mir:1', name='m1a')

# VLS-PGM

pgm = PGM('XF:23ID1-OP{Mono',
          temp_pv='XF:23ID1-OP{TCtrl:1', name='pgm')

# M3A Mirror

m3a = M3AMirror('XF:23ID1-OP{Mir:3',  name='m3a')

# Slits

slt1 = SlitsGapCenter('XF:23ID1-OP{Slt:1', name='slt1')
slt2 = SlitsGapCenter('XF:23ID1-OP{Slt:2', name='slt2')
slt3 = SlitsXY('XF:23ID1-OP{Slt:3', name='slt3')

# Diagnostic Manipulators

diag2_y = EpicsMotor('XF:23ID1-BI{Diag:2-Ax:Y}Mtr', name='diag2_y')
diag3_y = EpicsMotor('XF:23ID1-BI{Diag:3-Ax:Y}Mtr', name='diag3_y')
diag5_y = EpicsMotor('XF:23ID1-BI{Diag:5-Ax:Y}Mtr', name='diag5_y')
diag6_y = EpicsMotor('XF:23ID1-BI{Diag:6-Ax:Y}Mtr', name='diag6_y')

# Setpoint for PID loop

diag6_pid = PID('XF:23ID1-OP{FBck}', name='diag6_pid')

## FCCD slow shutter

inout = EPSTwoStateDevice('XF:23IDA-EPS{DP:1-Sh:1}',
                          state1='Inserted', state2='Not Inserted',
                          cmd_str1='In', cmd_str2='Out',
                          nm_str1='In', nm_str2='Out',
                          name='inout')

dif_fs = EPSTwoStateDevice('XF:23ID1-ES{Dif-FS}', name='dif_fs',
                           state1='Inserted', state2='Not Inserted',
                           cmd_str1='In', cmd_str2='Out',
                           nm_str1='In', nm_str2='Out')

dif_diode = EPSTwoStateDevice('XF:23ID1-ES{Dif-Abs}', name='dif_diode',
                              state1='Inserted', state2='Not Inserted',
                              cmd_str1='In', cmd_str2='Out',
                              nm_str1='In', nm_str2='Out')




