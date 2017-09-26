from ophyd import (EpicsMotor, PVPositioner, PVPositionerPC,
                   EpicsSignal, EpicsSignalRO, Device)
from ophyd import Component as Cpt
from ophyd import FormattedComponent as FmtCpt

from ..ophyd.devices import (Mirror, PGM, MotorMirror,
                             SlitsGapCenter, SlitsXY, PID)

# M1A, M1B1, M1B2

m1a = Mirror('XF:23IDA-OP:1{Mir:1', name='m1a')

# VLS-PGM

pgm = PGM('XF:23ID1-OP{Mono', name='pgm')

# M3A Mirror

m3a = MotorMirror('XF:23ID1-OP{Mir:3',  name='m3a')

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

diag6_pid = PID('XF:23ID', name='diag6_pid')

## FCCD slow shutter
#ssh_in = LinearActIn('XF:23IDA-EPS{DP:1-Sh:1}', name='ssh_in')
#ssh_out = LinearActOut('XF:23IDA-EPS{DP:1-Sh:1}', name='ssh_out')
#
## Diags Diffractometer Cube
#yag_cube_in = LinearActIn('XF:23ID1-ES{Dif-FS}', name='yag_cube_in')
#yag_cube_out = LinearActOut('XF:23ID1-ES{Dif-FS}', name='yag_cube_out')
#flux_in = LinearActIn('XF:23ID1-ES{Dif-Abs}', name='flux_in')
#flux_out = LinearActOut('XF:23ID1-ES{Dif-Abs}', name='flux_out')




