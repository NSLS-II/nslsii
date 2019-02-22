from collections import OrderedDict
from ophyd import (Component, DynamicDeviceComponent, Device, EpicsSignal,
                   EpicsSignalRO, PVPositioner)
from ophyd.device import create_device_from_components


def lakeshore336(name='Lakeshore336', temperatures=['A', 'B', 'C', 'D'],
                 controls=[1, 2, 3, 4], docstring=None,
                 default_read_attrs=None, default_configuration_attrs=None):
    '''Returns a Lakeshore 336 class with the provided sensors and controls,

    This is a function for generating a class for controlling Lakeshore model
    336 temperature controllers. The defaults are set to include four sensors
    (A, B, C and D) and four control loops (1,2,3 and 4) however this is
    customizable via the kwargs ``temperatures`` and ``controls`` respectively.
    To instantiate a controller with the default settings use the commands:
    ``MyLakeshore336 = lakeshore336()``
    ``my_controller = MyLakeshore336(PVprefix, name='my_controller')``

    Parameters
    ----------
    temperatures: list
        A list of temperature sensor 'channels' to instantiate, the default is
        ['A','B','C','D'].
    controls: list
        A list of heater control 'channels' to instantiate, the default is
        [1,2,3,4].
    docstring : str, optional
        Docstring to attach to the class
    default_read_attrs : list, optional
        Outside of Kind, control the default read_attrs list. Defaults to all
        'component_names'.
    default_configuration_attrs : list, optional
        Outside of Kind, control the default configuration_attrs list.
        Defaults to []
    '''

    def _set_fields(fields, cls, prefix, field_prefix='', **kwargs):
        '''A function that generates the component dictionaries for fields.

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
        field_prefix: str, optional
            An optional prefix to the field name (required as numbers are not
            valid attribute names).
        **kwargs: dict, optional
            The kwargs that are to be passed into the call to ``device``.
        '''
        out_dict = OrderedDict()
        for field in fields:
            suffix = f'{prefix}{field}'
            out_dict[f'{field_prefix}{field}'] = Component(cls, suffix,
                                                           **kwargs)
        return out_dict

    class _Temperature(Device):
        '''A sub-class for the readback 'channel' components.

        This class provides the temperature sensor ``ophyd.Components`` on a
        Lakeshore model 336 temperature controller ``ophyd.Device``.

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
        status = Component(EpicsSignalRO, '}T-Sts', kind='config')
        display_name = Component(EpicsSignal, '}T:Name-RB',
                                 write_pv='}T:Name-SP', kind='omitted')
        alarm = DynamicDeviceComponent(
            {'high': (EpicsSignalRO, '}Alrm:High-Sts', {'kind':'config'}),
             'low': (EpicsSignalRO, '}Alrm:Low-Sts', {'kind':'config'})},
            kind='config')
        T_limit = Component(EpicsSignal, '}T:Lim-RB', write_pv='}T:Lim-SP',
                            kind='omitted')

    class _Control(PVPositioner):
        '''A sub-class for the temperature control channels.

        This class provides the temperature control ``ophyd.Components`` on a
        Lakeshore model 336 temperature controller ``ophyd.Device``.

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
        done = Component(EpicsSignalRO, '}Sts:Ramp-Sts',kind='omitted')
        # top level attributes
        heater_range = Component(EpicsSignal, '}Val:Range-Sel', kind='config')
        heater_status = Component(EpicsSignalRO, '}Err:Htr-Sts',
                                  kind='omitted')
        mode = Component(EpicsSignal, '}Mode-Sel', kind='config')
        enable = Component(EpicsSignal, '}Enbl-Sel', kind='config')
        target_channel = Component(EpicsSignal, '}Out-Sel', kind='config')
        # ramp attributes
        ramp = DynamicDeviceComponent(
            {'enabled': (EpicsSignal, '}Enbl:Ramp-Sel', {'kind': 'config'}),
             'rate': (EpicsSignal, '}Val:Ramp-RB',
                      {'write_pv': '}Val:Ramp-SP', 'kind': 'config'})},
            kind='config')
        # PID loop parameters
        pid = DynamicDeviceComponent(
            {'proportional': (EpicsSignal, '}Gain:P-RB',
                              {'write_pv': '}Gain:P-SP', 'kind': 'config'}),
             'integral': (EpicsSignal, '}Gain:I-RB',
                          {'write_pv': '}Gain:I-SP', 'kind': 'config'}),
             'derivative': (EpicsSignal, '}Gain:D-RB',
                            {'write_pv': '}Gain:D-SP', 'kind': 'config'})},
             kind='config')
        # output parameters

        output = DynamicDeviceComponent(
            {'current': (EpicsSignal, '}Out-I', {}),
             'manual_current': (EpicsSignal, '}Out:Man-RB',
                                {'write_pv': '}Out:Man-SP'}),
             'max_current': (EpicsSignal, '}Out:MaxI-RB',
                             {'write_pv': '}Out:MaxI-SP', 'kind': 'config'}),
             'resistance': (EpicsSignal, '}Out:R-RB',
                            {'write_pv': '}Out:R-SP', 'kind': 'config'})})

    temp_components = _set_fields(temperatures, _Temperature, '-Chan:')
    output_components = _set_fields(controls, _Control, '-Out:',
                                    field_prefix='out')

    components = {
        'temp': Component(
            create_device_from_components('temp',**temp_components),''),
        'ctrl': Component(
            create_device_from_components('ctrl',**output_components),'')}

    new_class = create_device_from_components(
        name, docstring=docstring, default_read_attrs=default_read_attrs,
        default_configuration_attrs=default_configuration_attrs,
        base_class=Device, **components)

    return new_class
