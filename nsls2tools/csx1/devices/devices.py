from ophyd import (EpicsMotor, PVPositioner, PVPositionerPC,
                   EpicsSignal, EpicsSignalRO, Device)
from ophyd import Component as Cpt
from ophyd import FormattedComponent as FmtCpt
from ophyd import DynamicDeviceComponent as DDC
from ophyd import (EpicsMCA, EpicsDXP)
from ophyd import DeviceStatus, OrderedDict

class Lakeshore336(PVPositioner):
    readback = Cpt(EpicsSignalRO, 'T-RB')
    setpoint = Cpt(EpicsSignal, 'T-SP')
    done = Cpt(EpicsSignalRO, 'Sts:Ramp-Sts')
    ramp_enabled = Cpt(EpicsSignal, 'Enbl:Ramp-Sel')
    done_value = 0

class LakeshoreChannel(Device):
    T = Cpt(EpicsSignalRO, 'T-I')
    V = Cpt(EpicsSignalRO, 'Val:Sens-I')
    status = Cpt(EpicsSignalRO, 'T-Sts')

    def __init__(self, *args, read_attrs=None, **kwargs):
        if read_attrs is None:
            read_attrs = ['T']
        super().__init__(*args, read_attrs=read_attrs, **kwargs)

from collections import deque

class Lakeshore336Picky(Device):
    setpoint = Cpt(EpicsSignal, read_pv='-Out:1}T-RB', write_pv='-Out:1}T-SP',
                   add_prefix=('read_pv', 'write_pv'))
    # TODO expose ramp rate
    ramp_done = Cpt(EpicsSignalRO, '-Out:1}Sts:Ramp-Sts')
    ramp_enabled = Cpt(EpicsSignal, '-Out:1}Enbl:Ramp-Sel')
    ramp_rate = Cpt(EpicsSignal, read_pv='-Out:1}Val:Ramp-RB',
                    write_pv='-Out:1}Val:Ramp-SP',
                    add_prefix=('read_pv', 'write_pv'))

    chanA = Cpt(LakeshoreChannel, '-Chan:A}')
    chanB = Cpt(LakeshoreChannel, '-Chan:B}')

    def __init__(self, *args, timeout=60*60*30, target='chanA', **kwargs):
        # do the base stuff
        super().__init__(*args, **kwargs)
        # status object for communication
        self._done_sts = None

        # state for deciding if we are done or not
        self._cache = deque()
        self._start_time = 0
        self._setpoint = None
        self._count = -1

        # longest we can wait before giving up
        self._timeout = timeout
        self._lagtime = 120

        # the channel to watch to see if we are done
        self._target_channel = target

        # parameters for done testing
        self.mean_thresh = .01
        self.ptp_thresh = .1

    def _value_cb(self, value, timestamp, **kwargs):
        self._cache.append((value, timestamp))

        if (timestamp - self._cache[0][1]) < self._lagtime / 2:
            return

        while (timestamp - self._cache[0][1]) > self._lagtime:
            self._cache.popleft()

        buff = np.array([v[0] for v in self._cache])
        if self._done_test(self._setpoint, buff):
            self._done_sts._finished()
            self._reset()

    def _setpoint_cb(value, **kwargs):
        print('in cb', value)
        if value == self._setpoint:
            self._done_sts._finished()
            self.setpoint.clear_sub(self._setpoint_cb, 'value')

    def _reset(self):
        if self._target_channel == 'setpoint':
            target = self.setpoint
            target.clear_sub(self._setpoint_cb, 'value')
        else:
            target = getattr(self, self._target_channel).T
            target.clear_sub(self._value_cb, 'value')
        self._done_sts = None
        self._setpoint = None
        self._cache.clear()

    def _done_test(self, target, buff):
        mn = np.mean(np.abs(buff - target))

        if mn > self.mean_thresh:
            return False

        if np.ptp(buff) > self.ptp_thresh:
            return False

        return True


    def set(self, new_position, *, timeout=None):
        # to be subscribed to 'value' cb on readback
        sts = self._done_sts = DeviceStatus(self, timeout=timeout)
        if self.setpoint.get() == new_position:
            self._done_sts._finished()
            self._done_sts = None
            return sts

        self._setpoint = new_position

        self.setpoint.set(self._setpoint)

        # todo, set up subscription forwarding
        if self._target_channel == 'setpoint':
            self.setpoint.subscribe(local_cb, 'value')
        else:
            target = getattr(self, self._target_channel).T
            target.subscribe(self._value_cb, 'value')

        return self._done_sts


class DelayGeneratorChan(EpicsSignal):
    def __init__(self, prefix, **kwargs):
        super().__init__(prefix + '-RB', write_pv=prefix + '-SP', **kwargs)


class DelayGenerator(Device):
    A = Cpt(DelayGeneratorChan, '-Chan:A}DO:Dly')
    B = Cpt(DelayGeneratorChan, '-Chan:B}DO:Dly')
    C = Cpt(DelayGeneratorChan, '-Chan:C}DO:Dly')
    D = Cpt(DelayGeneratorChan, '-Chan:D}DO:Dly')
    E = Cpt(DelayGeneratorChan, '-Chan:E}DO:Dly')
    F = Cpt(DelayGeneratorChan, '-Chan:F}DO:Dly')
    G = Cpt(DelayGeneratorChan, '-Chan:G}DO:Dly')
    H = Cpt(DelayGeneratorChan, '-Chan:H}DO:Dly')

# Current-Voltage meter, driven in current mode

#class VIMeterVirtualMotorCurr(PVPositionerPC):
#    readback = Cpt(EpicsSignalRO, 'Val:RB-I')
#    #setpoint = Cpt(EpicsSignal, 'Val:SP-I')
#    setpoint = EpicsSignal('XF:23ID1-ES{K2611:1}Val:RB-I','XF:23ID1-ES{K2611:1}Val:SP-I')
#    stop_value = 1
#
#class VIMeterVirtualMotorVolt(PVPositionerPC):
#    readback = Cpt(EpicsSignalRO, 'Val:RB-E')
#    setpoint = Cpt(EpicsSignal, 'Val:SP-E')
#    stop_value = 1
#
#
#class VIMeter(Device):
#    curr = Cpt(VIMeterVirtualMotorCurr, '')
#    volt = Cpt(VIMeterVirtualMotorVolt, '')
#    ohm = Cpt(EpicsSignalRO, 'Val:RB-R')
#    #ohm = Cpt(VIMeterVirtualMotorOhm, '')
#
## Vortex MCA - saturn dxp and not Xpress3
#
#class Vortex(Device):
#    mca = Cpt(EpicsMCA, 'mca1')
#    vortex = Cpt(EpicsDXP, 'dxp1:')
#
#    @property
#    def trigger_signals(self):
#        return [self.mca.erase_start]


