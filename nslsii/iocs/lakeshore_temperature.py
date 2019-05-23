#!/usr/bin/env python3
from caproto.server import pvproperty, PVGroup
from caproto import ChannelType

from threading import Lock


class TemperatureRecord(PVGroup):

    def __init__(self, prefix, *, ioc, **kwargs):
        super().__init__(prefix, **kwargs)
        self.ioc = ioc

    _T_val = 0.
    _TC_val = 0.
    _V_val = 0.
    _status_val = 0.
    _display_name = 'Lakeshore T'
    _alarm_high_val = 5.0
    _alarm_low_val = 3.0

    putter_lock = Lock()

    T = pvproperty(value=_T_val,
                   read_only=True,
                   dtype=ChannelType.DOUBLE,
                   name='}}T-I')

    T_celsius = pvproperty(value=_TC_val,
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
    alarm_high = pvproperty(value=_alarm_high_val,
                            read_only=True,
                            dtype=ChannelType.DOUBLE,
                            name='}}Alrm:High-Sts')
    alarm_low = pvproperty(value=_alarm_low_val,
                           read_only=True,
                           dtype=ChannelType.DOUBLE,
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
    async def cmd(self, instance, value):

        if self.putter_lock.locked() is True:
            return instance.value
        else:
            self.putter_lock.acquire()

        p0 = instance.value
        dwell = self._step_size/self._velocity
        N = max(1, int((value - p0) / self._step_size))

        for j in range(N):
            new_value = p0 + self._step_size*(j+1)
            await instance.async_lib.library.sleep(dwell)
            await self.T.write(value=new_value)

        self.putter_lock.release()

        return value
