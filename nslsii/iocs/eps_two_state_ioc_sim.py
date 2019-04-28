#!/usr/bin/env python3
from caproto.server import pvproperty, PVGroup
from caproto.server import template_arg_parser, run
from caproto import ChannelType


class EPSTwoStateIOC(PVGroup):
    """
    Simulates multiple-attempt issue for two-state device.
    Parameters
    ----------
    retries : int, optional
        Number of attempts required for changing state,
        default is 2
    enbl_sts_val: str, optional
        Enumerated string that enables the state change,
        default is True
    hw_error_val: str, optional
        Enumerated string that activates the hardware error,
        default is False
    sts_error_val: str, optional
        Enumerated string that activates the Pos-Sts error,
        default is False
    """

    def __init__(self, retries=2, enbl_sts_val='True',
                 hw_error_val='False', sts_error_val='False',
                 **kwargs):

        super().__init__(**kwargs)

        self._max_retries = retries
        self._num_retries = 0

        self._enbl_sts_val = enbl_sts_val

        self._hw_error_val = hw_error_val
        self._sts_error_val = sts_error_val

    # Pos-Sts two-state PV

    _pos_states = ['Open', 'Closed']  # two position states
    _pos_sts_val = _pos_states[0]

    pos_sts = pvproperty(value=_pos_sts_val,
                         enum_strings=_pos_states,
                         dtype=ChannelType.ENUM,
                         read_only=True,
                         name='Pos-Sts')

    # Opn-Cmd and Cls-Cmd PVs used by client for changing state

    _cmd_states = ['None', 'Done']  # two command states

    state1_cmd = pvproperty(value=_cmd_states[0],
                            enum_strings=_cmd_states,
                            dtype=ChannelType.ENUM,
                            name='Cmd:Opn-Cmd')
    state2_cmd = pvproperty(value=_cmd_states[0],
                            enum_strings=_cmd_states,
                            dtype=ChannelType.ENUM,
                            name='Cmd:Cls-Cmd')

    _fail_states = ['False', 'True']

    fail_to_state1 = pvproperty(value=_fail_states[0],
                                enum_strings=_fail_states,
                                dtype=ChannelType.ENUM,
                                read_only=True,
                                name='Sts:FailOpn-Sts')
    fail_to_state2 = pvproperty(value=_fail_states[0],
                                enum_strings=_fail_states,
                                dtype=ChannelType.ENUM,
                                read_only=True,
                                name='Sts:FailCls-Sts')

    # Enbl-Sts PV that enables/disables the state change

    _enbl_states = ['True', 'False']

    enbl_sts = pvproperty(value='',
                          enum_strings=_enbl_states,
                          dtype=ChannelType.ENUM,
                          read_only=True,
                          name='Enbl-Sts')

    # PV Startup/Putter Methods

    @enbl_sts.startup
    async def enbl_sts(self, instance, async_lib):
        await instance.write(value=self._enbl_sts_val)

    @state1_cmd.putter
    async def state1_cmd(self, instance, value):
        rv = await self._state_cmd_put(instance, value,
                                       self._pos_states[0],
                                       self.fail_to_state1)
        return rv

    @state2_cmd.putter
    async def state2_cmd(self, instance, value):
        rv = await self._state_cmd_put(instance, value,
                                       self._pos_states[1],
                                       self.fail_to_state2)
        return rv

    # Internal Methods

    async def _state_cmd_put(self, instance, value, state_val, fail_to_state):
        if(value == self._cmd_states[0]):  # if None -> do nothing
            return self._cmd_states[0]
        if(self._pos_sts_val == state_val):  # if in state -> do nothing
            return self._cmd_states[0]
        if(self._enbl_sts_val == 'False'):  # if changes not enabled -> fail
            await fail_to_state.write(value='True')
            return self._cmd_states[0]
        self._num_retries += 1
        if(self._num_retries < self._max_retries):
            return self._cmd_states[0]
        else:
            self._num_retries = 0
        if(self._hw_error_val == 'True'):  # if hw error -> fail
            await fail_to_state.write(value='True')
            return self._cmd_states[1]
        if(self._sts_error_val == 'True'):  # if sts error -> don't change sts
            return self._cmd_states[1]
        await self.pos_sts.write(value=state_val)
        self._pos_sts_val = state_val
        return self._cmd_states[0]


if __name__ == '__main__':

    parser, split_args = template_arg_parser(
        default_prefix='eps2state:',
        desc='EPS Two State IOC.')

    retries_help = 'Number of attempts required for changing state'
    enable_help = 'State change is enabled'
    hwerror_help = 'HW error is activated'
    stserror_help = 'Pos-Sts error is activated'

    parser.add_argument('--retries', help=retries_help,
                        required=False, default=2, type=int)
    parser.add_argument('--enable', help=enable_help,
                        required=False, default='True', type=str)
    parser.add_argument('--hwerror', help=hwerror_help,
                        required=False, default='False', type=str)
    parser.add_argument('--stserror', help=stserror_help,
                        required=False, default='False', type=str)

    args = parser.parse_args()
    ioc_options, run_options = split_args(args)

    ioc = EPSTwoStateIOC(retries=args.retries,
                         enbl_sts_val=args.enable,
                         hw_error_val=args.hwerror,
                         sts_error_val=args.stserror,
                         **ioc_options)

    run(ioc.pvdb, **run_options)
