from collections import OrderedDict
from ophyd import (Component, DynamicDeviceComponent, Device, EpicsSignal,
                   EpicsSignalRO, PVPositioner)


class Lakeshore336(Device):
    '''An ``ophyd.Device`` class to be used for Lakeshore336 temp controllers.

    This is a class for controlling Lakeshore model 336 temperature controllers
    The defaults are set to include four sensors (A, B, C and D) and four
    control loops (1,2,3 and 4) however this is customizable at initialization
    time via the kwargs ``temperatures`` and ``controls`` respectively. To
    instantiate the default settings use the command:
    ``my_controller = Lakeshore336(PVprefix, name='my_controller')``

    Parameters
    ----------
    *args: list
        The arguments that are passed to ``ophyd.Device``.
    temperatures: list
        A list of temperature sensor 'channels' to instantiate, the default is
        ['A','B','C','D'].
    controls: list
        A list of heater control 'channels' to instantiate, the default is
        [1,2,3,4].
    **kwargs: dict
        The keyword arguments passed to ``ophyd.Device``.
    '''

    def _set_fields(fields, cls, prefix, **kwargs):
        '''A function that allows for the components to be dynamically set.

        Parameters
        ----------
        fields: list
            A list of field identifiers to include, for ``_Temperature``
            components an example is ['A','B','C','D'] and for ``_Control``
            components an example is [1,2,3,4].
        cls: class
            An ``ophyd.Device`` or ``ophyd.Signal`` class that shold be used
            to create the ``ophyd.Component``s specifed in ``fields``.
        prefix: str
            The string to prefix to the field identifier in ``fields`` to
            create the ``ophyd.Component`` ``suffix``.
        **kwargs: dict
            The kwargs that are to be passed into the call to ``device``.
        '''
        out_dict = OrderedDict()
        for field in fields:
            suffix = f'{prefix}{field}'
            out_dict[f'{field}'] = (cls, suffix, kwargs)
        return out_dict

    class _Temperature(Device):
        '''A Device that is used to create the readback 'channel' components.

        Parameters
        ----------
        *args: list
            The arguments to pass down to ``ophyd.Device.__init__``
        **kwargs: dict
            The kwargs to be passed down to the ``ophyd.Device.__init__``
        '''

        T = Component(EpicsSignalRO, '}T-I')
        T_celsius = Component(EpicsSignalRO, '}T:C-I')
        V = Component(EpicsSignalRO, '}Val:Sens-I')
        status = Component(EpicsSignalRO, '}T-Sts')
        name = Component(EpicsSignal, '}T:Name-RB', write_pv='}T:Name-SP')
        alarm_dict = {'high': (EpicsSignalRO, '}Alrm:High-Sts'),
                      'low': (EpicsSignalRO, '}Alrm:Low-Sts')}
        alarm = DynamicDeviceComponent(alarm_dict)
        T_limit = Component(EpicsSignal, '}T:Lim-RB', write_pv='}T:Lim-SP')

    class _Control(PVPositioner):
        '''A sub-class used to define each of the temperature control channels.

        Parameters
        ----------
        *args: list
            The args to pass down to ``ophyd.PVPositioner.__init__``
        **kwargs: dict
            The kwargs to be passed down to the ``ophyd.PVPositioner.__init__``
        '''
        # PVPositioner required attributes
        setpoint = Component(EpicsSignal, '}T-SP')
        readback = Component(EpicsSignalRO, '}T-RB')
        done = Component(EpicsSignalRO, '}Sts:Ramp-Sts')
        # top level attributes
        heater_range = Component(EpicsSignal, '}Val:Range-Sel')
        heater_status = Component(EpicsSignalRO, '}Err:Htr-Sts')
        mode = Component(EpicsSignal, '}Mode-Sel')
        enable = Component(EpicsSignal, '}Enbl-Sel')
        target_channel = Component(EpicsSignal, '}Out-Sel')
        # ramp attributes
        ramp = DynamicDeviceComponent(
            {'enabled': (EpicsSignal, '}Enbl:Ramp-Sel'),
             'rate': (EpicsSignal, '}Val:Ramp-RB',
                      {'write_pv': '}Val:Ramp-SP'})})
        # PID loop parameters
        pid = DynamicDeviceComponent(
            {'proportional': (EpicsSignal, '}Gain:P-RB',
                              {'write_pv': '}Gain:P-SP'}),
             'integral': (EpicsSignal, '}Gain:I-RB',
                          {'write_pv': '}Gain:I-SP'}),
             'derivative': (EpicsSignal, '}Gain:D-RB',
                            {'write_pv': '}Gain:D-SP'})})

        # output parameters
        output = DynamicDeviceComponent(
            {'current': (EpicsSignal, '}Out-I'),
             'manual_current': (EpicsSignal, '}Out:Man-RB',
                                {'write_pv': '}Out:Man-SP'}),
             'max_current': (EpicsSignal, '}Out:MaxI-RB',
                             {'write_pv': '}Out:MaxI-SP'}),
             'resistance': (EpicsSignalRO, '}Out:R-RB',
                            {'write_pv': '}Out:R-SP'})})

    def __init__(self, *args, temperatures=['A', 'B', 'C', 'D'],
                 controls=[1, 2, 3, 4], **kwargs):
        super().__init__(*args, **kwargs)

        self.temperature = DynamicDeviceComponent(
            self._set_fields(temperatures, self._Temperature, '-Chan:'))

        self.control = DynamicDeviceComponent(
            self._set_fields(controls, self._Control, '-Out:'))
