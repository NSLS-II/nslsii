import datetime
from ophyd import Device, EpicsSignal, EpicsSignalRO
from ophyd.device import (Component as Cpt, FormattedComponent as FmtCpt,
                          DeviceStatus)
import time


class nslsiiValves_and_ShuttersValueError(ValueError):
    pass


class EPSTwoStateDevice(Device):
    '''An ``ophyd.Device`` class for two state EPS objects at NSLS-II.

    This is a base class that should be used as a parent for classes related
    to pneumatic actuators, gate valves, photon shutters or any other NSLS-II
    EPS objects that have 2 distinct states .

    Parameters
    ----------
    prefix : str, keyword only
        The PV prefix for all components of the device
    name : str, keyword only
        The name of the device as will be reported via read()
    state1_val : float, int or str, optional
        The value displayed when the device is read that signifys state 1
    state2_val : float, int or str, optional
        The value displayed when the device is read that signifys state 2
    state1_str : str, optional
        The string value to be passed to ``RE(mv(device, val))`` to move to
        state 1
    state2_str : str, optional
        The string value to be passed to ``RE(mv(device, val))`` to move to
        state 2
    state1_pv_uid : str, optional
        The unique part of the EPICS PV for the state 1 command(see note below)
    state2_pv_uid : str, optional
        The unique part of the EPICS PV for the state 2 command(see note below)
    num_retries : int, optional
        The number of attempts at changing the state prior to raising an
        error, the default is 1.
    retry_sleep_time : float, optional
        This is the time in seconds to wait between retries on changing the
        state, the default is 0.5 s.
    stop_str : str or None, optional
        The value of ``state1_str`` or ``state2_str`` to be called in the
        ``stop`` method. The default, if None is entered, is ``state2_str``.
    **kwargs : dict, optional
        The kwargs passed to the ``ophyd.Device`` ``__init__`` method

    ..note ::

        The PV associated with moving to 'state 1' is derived from the
        ``prefix`` and the ``state1_pv_uid`` using the following format:
        ``'{prefix}Cmd:{state1_pv_uid}-Cmd'``
   '''

    def __init__(self, *, prefix, name,
                 state1_val='Open', state2_val='Closed',
                 state1_str='open', state2_str='close',
                 state1_pv_uid='Opn', state2_pv_uid='Cls',
                 num_retries=1, retry_sleep_time=0.5,
                 stop_str=None, **kwargs):

        self._state1_pv_uid = state1_pv_uid
        self._state2_pv_uid = state2_pv_uid

        super().__init__(prefix=prefix, name=name, **kwargs)

        self._set_st = None
        self.read_attrs = ['status']
        self._state1_val = state1_val
        self._state2_val = state2_val
        self._state1_str = state1_str
        self._state2_str = state2_str
        self._num_retries = num_retries
        self._retry_sleep_time = retry_sleep_time
        if stop_str == state1_str:
            self._stop_str = self._state1_str
            self._resume_str = self._state2_str
        elif stop_str == state2_str or stop_str is None:
            self._stop_str = self._state2_str
            self._resume_str = self._state1_str
        else:
            raise nslsiiValves_and_ShuttersValueError(
                'the kwarg ``stop_str`` in the EpicsTwoStateDevice class'
                '``__init__`` method needs to be None or needs to match one of'
                'the kwargs ``state1_str`` or ``state2_str``')

        self._cmd_map = {self._state1_str: self._state1_cmd,
                         self._state2_str: self._state2_cmd}
        self._target_map = {self._state1_str: self._state1_val,
                            self._state2_str: self._state2_val}

        self._time_fmtstr = '%Y-%m-%d %H:%M:%S'

    _state1_cmd = FmtCpt(EpicsSignal,
                         '{self.prefix}Cmd:{self._state1_pv_uid}-Cmd',
                         string=True)
    _state2_cmd = FmtCpt(EpicsSignal,
                         '{self.prefix}Cmd:{self._state2_pv_uid}-Cmd',
                         string=True)

    status = Cpt(EpicsSignalRO, 'Pos-Sts', string=True)

    enabled_status = Cpt(EpicsSignalRO, 'Enbl-Sts', string=True)

    _fail_to_state1 = FmtCpt(EpicsSignalRO,
                             '{self.prefix}Sts:Fail{self._state1_pv_uid}-Sts',
                             string=True)
    _fail_to_state2 = FmtCpt(EpicsSignalRO,
                             '{self.prefix}Sts:Fail{self._state2_pv_uid}-Sts',
                             string=True)

    def set(self, val):
        if self._set_st is not None:
            raise RuntimeError(
                f'trying to set {self.name} while a set is in progress')

        cmd_sig = self._cmd_map[val]
        target_val = self._target_map[val]

        st = self._set_st = DeviceStatus(self)
        enums = self.status.enum_strs

        def state_cb(value, timestamp, **kwargs):
            value = enums[int(value)]
            if value == target_val:
                self._set_st._finished()
                self._set_st = None
                self.status.clear_sub(state_cb)

        cmd_enums = cmd_sig.enum_strs
        count = 0

        def cmd_retry_cb(value, timestamp, **kwargs):
            nonlocal count
            value = cmd_enums[int(value)]
            count += 1
            if count > self._num_retries:
                cmd_sig.clear_sub(cmd_retry_cb)
                st._finished(success=False)
            if value == 'None':
                if not st.done:
                    time.sleep(self._retry_sleep_time)
                    cmd_sig.set(1)
                    ts = datetime.datetime.fromtimestamp(
                        timestamp).strftime(self._time_fmtstr)
                    print(f'** ({ts}) Had to reactuate {self.name} while'
                          f'moving to {val}')
                else:
                    cmd_sig.clear_sub(cmd_retry_cb)

        cmd_sig.subscribe(cmd_retry_cb, run=False)
        cmd_sig.set(1)
        self.status.subscribe(state_cb)

        return st

    def stop(self, success):
        import time
        prev_st = self._set_st
        cmd_sig = self._cmd_map[self._stop_str]
        stop_val = self._target_map[self._stop_str]

        if prev_st is not None:
            while not prev_st.done:
                time.sleep(.1)
        self._was_stopped = (stop_val == self.status.get())
        st = self.set(cmd_sig)
        while not st.done:
            time.sleep(self._retry_sleep_time)

    def resume(self):
        import time
        cmd_sig = self._cmd_map[self._resume_str]
        prev_st = self._set_st
        if prev_st is not None:
            while not prev_st.done:
                time.sleep(.1)
        if not self._was_stopped:
            st = self.set(cmd_sig)
            while not st.done:
                time.sleep(self._retry_sleep_time)

    def unstage(self):
        self._was_stopped = True
        return super().unstage()


class PneumaticActuator(EPSTwoStateDevice):
    '''An ``ophyd.Device`` for EPS driven pneumatic actuators at NSLS-II


    This is for use with NSLS-II EPS based pneumatic actuators that have two
    distinct states 'In' and 'Out' and are actuated into these two states by
    the PV's ``'{prefix}Cmd:In-Cmd'`` and ``'{prefix}Cmd:out-Cmd'``.

    The basic use case is to define the device using the line:

    ``my_pneumatic_actuator = PneumaticActuator(prefix='a_PV_prefix',
                                                name='my_pneumatic_actuator')``

    which can then be actuated by:
    ``RE(mv(my_pneumatic_actuator, 'in')`` or
    ``RE(mv(my_pneumatic_actuator, 'out')``

    Parameters
    ----------
    prefix : str, keyword only
        The PV prefix for all components of the device
    name : str, keyword only
        The name of the device as will be reported via read()
    state1_val : float, int or str, optional
        The value displayed when the device is read that signifys state 1
    state2_val : float, int or str, optional
        The value displayed when the device is read that signifys state 2
    state1_str : str, optional
        The string value to be passed to ``RE(mv(device, val))`` to move to
        state 1
    state2_str : str, optional
        The string value to be passed to ``RE(mv(device, val))`` to move to
        state 2
    num_retries : int, optional
        This number of attempts at changing the state prior to raising an
        error, the default is 1.
    retry_sleep_time : float, optional
        This is the time in seconds to wait between retries on changing the
        state, the default is 0.5 s.
    stop_str : str or None, optional
        The value of ``state1_str`` or ``state2_str`` to be called in the
        ``stop`` method. The default, if None is entered, is ``state2_str``.
    **kwargs : dict, optional
        The kwargs passed to the ``ophyd.Device`` ``__init__`` method
    '''

    def __init__(self, *, prefix, name,
                 state1_val='In', state2_val='Out',
                 state1_str='in', state2_str='out',
                 num_retries=1, retry_sleep_time=0.5,
                 stop_str=None, **kwargs):

        kwargs = dict(state1_pv_uid='In', state2_pv_uid='Out',
                      state1_val=state1_val, state2_val=state2_val,
                      state1_str=state1_str, state2_str=state2_str,
                      num_retries=num_retries,
                      retry_sleep_time=retry_sleep_time,
                      stop_str=stop_str, **kwargs)
        super().__init__(prefix, name, **kwargs)


class GateValve(EPSTwoStateDevice):
    '''An ``ophyd.Device`` for EPS driven gate valves at NSLS-II

    This is for use with NSLS-II EPS based gate valves that have two
    distinct states 'Open' and 'Close' and are actuated into these two states
    by the PV's ``'{prefix}Cmd:Opn-Cmd'`` and ``'{prefix}Cmd:Cls-Cmd'``.

    The basic use case is to define the device using the line:

    ``my_gate_valve = GateValve(prefix='a_PV_prefix', name='my_gate_valve')``

    which can then be actuated by:
    ``RE(mv(my_gate_valve, 'open')`` or
    ``RE(mv(my_gate_valve, 'close')``

    Parameters
    ----------
    prefix : str, keyword only
        The PV prefix for all components of the device
    name : str, keyword only
        The name of the device as will be reported via read()
    state1_val : float, int or str, optional
        The value displayed when the device is read that signifys state 1
    state2_val : float, int or str, optional
        The value displayed when the device is read that signifys state 2
    state1_str : str, optional
        The string value to be passed to ``RE(mv(device, val))`` to move to
        state 1
    state2_str : str, optional
        The string value to be passed to ``RE(mv(device, val))`` to move to
        state 2
    num_retries : int, optional
        This number of attempts at changing the state prior to raising an
        error, the default is 1.
    retry_sleep_time : float, optional
        This is the time in seconds to wait between retries on changing the
        state, the default is 0.5 s.
    **kwargs : dict, optional
        The kwargs passed to the ``ophyd.Device`` ``__init__`` method
    '''

    def __init__(self, *, prefix, name,
                 state1_val='Open', state2_val='Closed',
                 state1_str='open', state2_str='close',
                 num_retries=1, retry_sleep_time=0.5,
                 stop_str=None, **kwargs):

        kwargs = dict(state1_pv_uid='Opn', state2_pv_uid='Cls',
                      state1_val=state1_val, state2_val=state2_val,
                      state1_str=state1_str, state2_str=state2_str,
                      num_retries=num_retries,
                      retry_sleep_time=retry_sleep_time,
                      stop_str=stop_str, **kwargs)
        super().__init__(prefix, name, **kwargs)


class PhotonShutter(EPSTwoStateDevice):
    '''An ``ophyd.Device`` for EPS driven photon shutters at NSLS-II

    This is for use with NSLS-II EPS based photon shutters that have two
    distinct states 'Open' and 'Close' and are actuated into these two states
    by the PV's ``'{prefix}Cmd:Opn-Cmd'`` and ``'{prefix}Cmd:Cls-Cmd'``. This
    is different from the ``GateValve`` class as it has, as standard, a larger
    number of retries (``num_retries``) as default.

    The basic use case is to define the device using the line:

    ``my_shutter = PhotonShutter(prefix='a_PV_prefix', name='my_shutter')``

    which can then be actuated by:
    ``RE(mv(my_shutter, 'open')`` or
    ``RE(mv(my_shutter, 'close')``

    Parameters
    ----------
    prefix : str, keyword only
        The PV prefix for all components of the device
    name : str, keyword only
        The name of the device as will be reported via read()
    state1_val : float, int or str, optional
        The value displayed when the device is read that signifys state 1
    state2_val : float, int or str, optional
        The value displayed when the device is read that signifys state 2
    state1_str : str, optional
        The string value to be passed to ``RE(mv(device, val))`` to move to
        state 1
    state2_str : str, optional
        The string value to be passed to ``RE(mv(device, val))`` to move to
        state 2
    num_retries : int, optional
        This number of attempts at changing the state prior to raising an
        error, the default is 5.
    retry_sleep_time : float, optional
        This is the time in seconds to wait between retries on changing the
        state, the default is 0.5 s.
    **kwargs : dict, optional
        The kwargs passed to the ``ophyd.Device`` ``__init__`` method
    '''

    def __init__(self, *, prefix, name,
                 state1_val='Open', state2_val='Closed',
                 state1_str='open', state2_str='close',
                 num_retries=5, retry_sleep_time=0.5,
                 stop_str=None, **kwargs):

        kwargs = dict(state1_pv_uid='Opn', state2_pv_uid='Cls',
                      state1_val=state1_val, state2_val=state2_val,
                      state1_str=state1_str, state2_str=state2_str,
                      num_retries=num_retries,
                      retry_sleep_time=retry_sleep_time,
                      stop_str=stop_str, **kwargs)
        super().__init__(prefix, name, **kwargs)
