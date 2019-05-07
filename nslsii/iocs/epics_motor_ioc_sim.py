#!/usr/bin/env python3
from caproto.server import pvproperty, PVGroup
from caproto.server import ioc_arg_parser, run
from caproto import ChannelType
import contextvars
import functools
import math

internal_process = contextvars.ContextVar('internal_process',
                                          default=False)

def no_reentry(func):
    @functools.wraps(func)
    async def inner(*args, **kwargs):
        if internal_process.get():
            return
        try:
            internal_process.set(True)
            return (await func(*args, **kwargs))
        finally:
            internal_process.set(False)

    return inner


class EpicsMotorIOC(PVGroup):
    """
    Simulates ophyd.EpicsMotor.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    _dir_states = ['neg', 'pos']
    _false_true_states = ['False', 'True']

    # position

    _upper_alarm_limit = 10.0
    _lower_alarm_limit = -10.0

    _upper_warning_limit = 9.0
    _lower_warning_limit = -9.0

    _upper_ctrl_limit = 11.0
    _lower_ctrl_limit = -11.0

    _egu = 'mm'

    _precision = 3

    user_readback = pvproperty(value=0.0, read_only=True,
                               dtype=ChannelType.DOUBLE,
                               upper_alarm_limit=_upper_alarm_limit,
                               lower_alarm_limit=_lower_alarm_limit,
                               upper_warning_limit=_upper_warning_limit,
                               lower_warning_limit=_lower_warning_limit,
                               upper_ctrl_limit=_upper_ctrl_limit,
                               lower_ctrl_limit=_lower_ctrl_limit,
                               units=_egu,
                               precision=_precision,
                               name='.RBV')
    user_setpoint = pvproperty(value=0.0,
                               dtype=ChannelType.DOUBLE,
                               upper_alarm_limit=_upper_alarm_limit,
                               lower_alarm_limit=_lower_alarm_limit,
                               upper_warning_limit=_upper_warning_limit,
                               lower_warning_limit=_lower_warning_limit,
                               upper_ctrl_limit=_upper_ctrl_limit,
                               lower_ctrl_limit=_lower_ctrl_limit,
                               units=_egu,
                               precision=_precision,
                               name='.VAL')

    # calibration dial <--> user

    user_offset = pvproperty(value=0.0, read_only=True,
                             dtype=ChannelType.DOUBLE,
                             name='.OFF')

    user_offset_dir = pvproperty(value=_dir_states[1],
                                 enum_strings=_dir_states,
                                 dtype=ChannelType.ENUM,
                                 name='.DIR')

    offset_freeze_switch = pvproperty(value=_false_true_states[0],
                                      enum_strings=_false_true_states,
                                      dtype=ChannelType.ENUM,
                                      name='.FOFF')
    set_use_switch = pvproperty(value=_false_true_states[0],
                                enum_strings=_false_true_states,
                                dtype=ChannelType.ENUM,
                                name='.SET')

    # configuration

    _velocity = 1.
    _acceleration = 3.

    velocity = pvproperty(value=_velocity, read_only=True,
                          dtype=ChannelType.DOUBLE,
                          name='.VELO')
    acceleration = pvproperty(value=_acceleration, read_only=True,
                              dtype=ChannelType.DOUBLE,
                              name='.ACCL')
    motor_egu = pvproperty(value=_egu, read_only=True,
                           dtype=ChannelType.STRING,
                           name='.EGU')

    # motor status

    motor_is_moving = pvproperty(value='False', read_only=True,
                                 enum_strings=_false_true_states,
                                 dtype=ChannelType.ENUM,
                                 name='.MOVN')
    motor_done_move = pvproperty(value='False', read_only=False,
                                 enum_strings=_false_true_states,
                                 dtype=ChannelType.ENUM,
                                 name='.DMOV')

    high_limit_switch = pvproperty(value=0, read_only=True,
                                   dtype=ChannelType.INT,
                                   name='.HLS')
    low_limit_switch = pvproperty(value=0, read_only=True,
                                  dtype=ChannelType.INT,
                                  name='.LLS')

    direction_of_travel = pvproperty(value=_dir_states[1],
                                     enum_strings=_dir_states,
                                     dtype=ChannelType.ENUM,
                                     name='.TDIR')

    # commands

    _cmd_states = ['False', 'True']

    motor_stop = pvproperty(value=_cmd_states[0],
                            enum_strings=_cmd_states,
                            dtype=ChannelType.ENUM,
                            name='.STOP')
    home_forward = pvproperty(value=_cmd_states[0],
                              enum_strings=_cmd_states,
                              dtype=ChannelType.ENUM,
                              name='.HOMF')
    home_reverse = pvproperty(value=_cmd_states[0],
                              enum_strings=_cmd_states,
                              dtype=ChannelType.ENUM,
                              name='.HOMR')

    # Methods

    @user_setpoint.startup
    async def user_setpoint(self, instance, async_lib):
        instance.ev = async_lib.library.Event()
        instance.async_lib = async_lib

    @user_setpoint.putter
    @no_reentry
    async def user_setpoint(self, instance, value):
        disp = (value - instance.value)
        step_size = 0.1
        dwell = step_size/self._velocity
        N = max(1, int(disp / step_size))

        await self.motor_done_move.write(value='False')

        for j in range(N):
            new_value = instance.value + step_size
            await instance.write(new_value)
            await instance.async_lib.library.sleep(dwell)
            await self.user_readback.write(value=new_value)

        await self.motor_done_move.write(value='True')

        return value


if __name__ == '__main__':

    ioc_options, run_options = ioc_arg_parser(
        default_prefix='mtr:',
        desc='EpicsMotor IOC.')

    ioc = EpicsMotorIOC(**ioc_options)
    run(ioc.pvdb, **run_options)
