#!/usr/bin/env python3
from caproto.server import pvproperty, PVGroup
from caproto import ChannelType


class ControlRecord(PVGroup):

    def __init__(self, prefix, *, indx, ioc, **kwargs):
        super().__init__(prefix, **kwargs)
        self._indx = indx
        self.ioc = ioc

    _false_true_states = ['False', 'True']

    # PVPositioner required attributes

    _rb_val = 0.

    setpoint = pvproperty(value=_rb_val,
                          dtype=ChannelType.DOUBLE,
                          name='}}T-SP')
    readback = pvproperty(value=_rb_val,
                          read_only=True,
                          dtype=ChannelType.DOUBLE,
                          name='}}T-RB')

    _done_val = 0.

    done = pvproperty(value='False',
                      read_only=False,
                      enum_strings=_false_true_states,
                      dtype=ChannelType.ENUM,
                      name='}}Sts:Ramp-Sts')

    # top level attributes

    _heater_range_val = 0.
    _heater_status_val = 0.

    heater_range = pvproperty(value=_heater_range_val,
                              dtype=ChannelType.DOUBLE,
                              name='}}Val:Range-Sel')
    heater_status = pvproperty(value=_heater_status_val,
                               read_only=True,
                               dtype=ChannelType.DOUBLE,
                               name='}}Err:Htr-Sts')

    _mode_val = 0.
    _enable_val = 0.
    _target_channel_val = ''

    mode = pvproperty(value=_mode_val,
                      dtype=ChannelType.DOUBLE,
                      name='}}Mode-Sel')
    enable = pvproperty(value=_enable_val,
                        dtype=ChannelType.DOUBLE,
                        name='}}Enbl-Sel')
    target_channel = pvproperty(value=_target_channel_val,
                                dtype=ChannelType.STRING,
                                name='}}Out-Sel')

    # ramp attributes

    _ramp_enable_val = 0.
    _ramp_rate_val = 5.  # degree/s

    ramp_enable = pvproperty(value=_ramp_enable_val,
                             dtype=ChannelType.DOUBLE,
                             name='}}Enbl:Ramp-Sel')

    ramp_rate_rb = pvproperty(value=_ramp_rate_val,
                              dtype=ChannelType.DOUBLE,
                              name='}}Val:Ramp-RB')
    ramp_rate_sp = pvproperty(value=_ramp_rate_val,
                              dtype=ChannelType.DOUBLE,
                              name='}}Val:Ramp-SP')

    # PID loop parameters

    _pid_proportional_val = 0.
    _pid_integral_val = 0.
    _pid_derivative_val = 0.

    pid_proportional_rb = pvproperty(value=_pid_proportional_val,
                                     read_only=True,
                                     dtype=ChannelType.DOUBLE,
                                     name='}}Gain:P-RB')
    pid_proportional_sp = pvproperty(value=_pid_proportional_val,
                                     dtype=ChannelType.DOUBLE,
                                     name='}}Gain:P-SP')

    pid_integral_rb = pvproperty(value=_pid_integral_val,
                                 read_only=True,
                                 dtype=ChannelType.DOUBLE,
                                 name='}}Gain:I-RB')
    pid_integral_sp = pvproperty(value=_pid_integral_val,
                                 dtype=ChannelType.DOUBLE,
                                 name='}}Gain:I-SP')

    pid_derivative_rb = pvproperty(value=_pid_derivative_val,
                                   read_only=True,
                                   dtype=ChannelType.DOUBLE,
                                   name='}}Gain:D-RB')
    pid_derivative_sp = pvproperty(value=_pid_derivative_val,
                                   dtype=ChannelType.DOUBLE,
                                   name='}}Gain:D-SP')

    # output parameters

    _out_current_val = 0.
    _out_man_current_val = 0.
    _out_max_current_val = 0.
    _out_resistance_val = 0.

    out_current = pvproperty(value=_out_current_val,
                             dtype=ChannelType.DOUBLE,
                             name='}}Out-I')

    out_man_current_rb = pvproperty(value=_out_man_current_val,
                                    read_only=True,
                                    dtype=ChannelType.DOUBLE,
                                    name='}}Out:Man-RB')
    out_man_current_sp = pvproperty(value=_out_man_current_val,
                                    dtype=ChannelType.DOUBLE,
                                    name='}}Out:Man-SP')

    out_max_current_rb = pvproperty(value=_out_max_current_val,
                                    read_only=True,
                                    dtype=ChannelType.DOUBLE,
                                    name='}}Out:MaxI-RB')
    out_max_current_sp = pvproperty(value=_out_max_current_val,
                                    dtype=ChannelType.DOUBLE,
                                    name='}}Out:MaxI-SP')

    out_resistance_rb = pvproperty(value=_out_resistance_val,
                                   read_only=True,
                                   dtype=ChannelType.DOUBLE,
                                   name='}}Out:R-RB')
    out_resistance_sp = pvproperty(value=_out_resistance_val,
                                   dtype=ChannelType.DOUBLE,
                                   name='}}Out:R-SP')

    # Putter/Getter Methods

    @setpoint.putter
    async def setpoint(self, instance, value):

        # select channel
        prefix = self.ioc.prefix.replace('{', '{'*2)
        channel = self._target_channel_val
        t_k = f'{prefix}-Chan:{channel}'
        if t_k in self.ioc.groups:
            pass
        else:
            return instance.value
        t_v = self.ioc.groups[t_k]

        # apply cmd
        indx = self._indx
        cmd = f'{value},{indx}'
        await t_v.cmd.write(value=cmd)

        self._rb_val = value
        return value

    @done.getter
    async def done(self, instance):
        return self._done_val

    @target_channel.getter
    async def target_channel(self, instance):
        return self._target_channel_val

    @target_channel.putter
    async def target_channel(self, instance, value):
        self._target_channel_val = value
        return value

    @ramp_rate_rb.getter
    async def ramp_rate_rb(self, instance):
        return self._ramp_rate_val

    @ramp_rate_sp.putter
    async def ramp_rate_sp(self, instance, value):
        self._ramp_rate_val = value
        return value

    @pid_proportional_rb.getter
    async def pid_proportional_rb(self, instance):
        return self._pid_proportional_val

    @pid_proportional_sp.putter
    async def pid_proportional_sp(self, instance, value):
        self._pid_proportional_val = value
        return value

    @pid_integral_rb.getter
    async def pid_integral_rb(self, instance):
        return self._pid_integral_val

    @pid_integral_sp.putter
    async def pid_integral_sp(self, instance, value):
        self._pid_integral_val = value
        return value

    @pid_derivative_rb.getter
    async def pid_derivative_rb(self, instance):
        return self._pid_derivative_val

    @pid_derivative_sp.putter
    async def pid_derivative_sp(self, instance, value):
        self._pid_derivative_val = value
        return value

    @out_man_current_rb.getter
    async def out_man_current_rb(self, instance):
        return self._out_man_current_val

    @out_man_current_sp.putter
    async def out_man_current_sp(self, instance, value):
        self._out_man_current_val = value
        return value

    @out_max_current_rb.getter
    async def out_max_current_rb(self, instance):
        return self._out_max_current_val

    @out_max_current_sp.putter
    async def out_max_current_sp(self, instance, value):
        self._out_max_current_val = value
        return value

    @out_resistance_rb.getter
    async def out_resistance_rb(self, instance):
        return self._out_resistance_val

    @out_resistance_sp.putter
    async def out_resistance_sp(self, instance, value):
        self._out_resistance_val = value
        return value
