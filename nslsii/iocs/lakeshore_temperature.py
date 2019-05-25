#!/usr/bin/env python3
from caproto.server import pvproperty, PVGroup
from caproto import ChannelType

from threading import Lock


class TemperatureRecord(PVGroup):

    def __init__(self, prefix, *, indx, ioc, **kwargs):
        super().__init__(prefix, **kwargs)
        self._indx = indx
        self.ioc = ioc

    _false_true_states = ['False', 'True']
    _step_size = 1  # degree

    _T_val = 273.15
    _V_val = 0.
    _status_val = 0.
    _display_name = 'Lakeshore T'
    _alarm_high_val = 400.0
    _alarm_low_val = 200.0

    putter_lock = Lock()

    T = pvproperty(value=_T_val,
                   read_only=True,
                   dtype=ChannelType.DOUBLE,
                   name='}}T-I')

    T_celsius = pvproperty(value=_T_val - 273.15,
                           read_only=True,
                           dtype=ChannelType.DOUBLE,
                           name='}}T:C-I')
    V = pvproperty(value=_V_val,
                   read_only=True,
                   dtype=ChannelType.DOUBLE,
                   name='}}Val:Sens-I')
    status = pvproperty(value=_status_val,
                        read_only=True,
                        dtype=ChannelType.DOUBLE,
                        name='}}T-Sts')
    display_name_rb = pvproperty(value=_display_name,
                                 read_only=True,
                                 dtype=ChannelType.STRING,
                                 name='}}T:Name-RB')
    display_name_sp = pvproperty(value=_display_name,
                                 dtype=ChannelType.STRING,
                                 name='}}T:Name-SP')

    alarm_high = pvproperty(value='False',
                            enum_strings=_false_true_states,
                            dtype=ChannelType.ENUM,
                            name='}}Alrm:High-Sts')
    alarm_low = pvproperty(value='False',
                           enum_strings=_false_true_states,
                           dtype=ChannelType.ENUM,
                           name='}}Alrm:Low-Sts')

    _T_lim_val = 0.

    T_lim_rb = pvproperty(value=_T_lim_val,
                          read_only=True,
                          dtype=ChannelType.DOUBLE,
                          name='}}T:Lim-RB')
    T_lim_sp = pvproperty(value=_T_lim_val,
                          dtype=ChannelType.DOUBLE,
                          name='}}T:Lim-SP')

    # Methods

    _velocity = 1.
    _step_size = 0.1

    cmd = pvproperty(value='',
                     dtype=ChannelType.STRING,
                     name='}}Cmd')

    @cmd.startup
    async def cmd(self, instance, async_lib):
        instance.ev = async_lib.library.Event()
        instance.async_lib = async_lib

    @cmd.putter
    async def cmd(self, instance, cmd):

        cmd_list = cmd.split(',')  # value, ctrl indx
        value = float(cmd_list[0])
        ctrl_indx = int(cmd_list[1])

        # check alarm high

        if value >= self._alarm_high_val:
            await self.alarm_high.write(value=1)
            return instance.value
        else:
            await self.alarm_high.write(value=0)

        # check alarm low

        if value <= self._alarm_low_val:
            await self.alarm_low.write(value=1)
            return instance.value
        else:
            await self.alarm_low.write(value=0)

        # check lock

        if self.putter_lock.locked() is True:
            return instance.value
        else:
            self.putter_lock.acquire()

        # select the lakeshore control

        prefix = self.ioc.prefix.replace('{', '{'*2)
        c_k = f'{prefix}-Out:{ctrl_indx}'
        ctrl = self.ioc.groups[c_k]

        # update the temp and ctrl readbacks

        await ctrl.done.write(value=0)

        p0 = self._T_val
        dwell = self._step_size/ctrl._ramp_rate_val
        N = max(1, int((value - p0) / self._step_size))

        for j in range(N):
            new_value = p0 + self._step_size*(j+1)
            await instance.async_lib.library.sleep(dwell)
            await self.T.write(value=new_value) 
            await self.T_celsius.write(value=(new_value - 273.15))
            await ctrl.readback.write(value=new_value)

        self._T_val = value
        await ctrl.done.write(value=1)

        self.putter_lock.release()
        return value
