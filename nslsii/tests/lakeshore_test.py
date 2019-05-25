import os
import pytest
import subprocess
import sys
import time

from collections import OrderedDict
from ophyd import (Component, DynamicDeviceComponent, Device,
                   EpicsSignal, EpicsSignalRO, PVPositioner)

from caproto.sync.client import read


def create_device_from_components(name, *, docstring=None,
                                  default_read_attrs=None,
                                  default_configuration_attrs=None,
                                  base_class=Device, class_kwargs=None,
                                  **components):

    if docstring is None:
        docstring = f'{name} Device'

    if not isinstance(base_class, tuple):
        base_class = (base_class, )

    if class_kwargs is None:
        class_kwargs = {}

    clsdict = OrderedDict(
        __doc__=docstring,
        _default_read_attrs=default_read_attrs,
        _default_configuration_attrs=default_configuration_attrs
    )

    for attr, component in components.items():
        if not isinstance(component, Component):
            raise ValueError(f'Attribute {attr} is not a Component. '
                             f'It is of type {type(component).__name__}')

        clsdict[attr] = component

    return type(name, base_class, clsdict, **class_kwargs)


def lakeshore336(name='Lakeshore336', temperatures=['A', 'B', 'C', 'D'],
                 controls=[1, 2], docstring=None,
                 default_read_attrs=None, default_configuration_attrs=None):

    def _set_fields(fields, cls, prefix, field_prefix='', **kwargs):
        '''A function that generates the component dictionaries for fields.'''
        out_dict = OrderedDict()
        for field in fields:
            suffix = f'{prefix}{field}'
            out_dict[f'{field_prefix}{field}'] = Component(cls, suffix,
                                                           **kwargs)
        return out_dict

    class _Temperature(Device):

        T = Component(EpicsSignalRO, '}T-I')
        T_celsius = Component(EpicsSignalRO, '}T:C-I')
        V = Component(EpicsSignalRO, '}Val:Sens-I')
        status = Component(EpicsSignalRO, '}T-Sts', kind='config')
        display_name = Component(EpicsSignal, '}T:Name-RB',
                                 write_pv='}T:Name-SP', kind='omitted')

        alarm = DynamicDeviceComponent(
            {'high': (EpicsSignalRO, '}Alrm:High-Sts', {'kind': 'config'}),
             'low': (EpicsSignalRO, '}Alrm:Low-Sts', {'kind': 'config'})},
            kind='config')

        T_limit = Component(EpicsSignal, '}T:Lim-RB', write_pv='}T:Lim-SP',
                            kind='omitted')

    class _Control(PVPositioner):

        # PVPositioner required attributes
        setpoint = Component(EpicsSignal, '}T-SP')
        readback = Component(EpicsSignalRO, '}T-RB')

        done = Component(EpicsSignalRO, '}Sts:Ramp-Sts', kind='omitted')

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
        'temp': Component(create_device_from_components('temp',
                                                        **temp_components),
                          ''),
        'ctrl': Component(create_device_from_components('ctrl',
                                                        **output_components),
                          '')}

    new_class = create_device_from_components(
        name, docstring=docstring, default_read_attrs=default_read_attrs,
        default_configuration_attrs=default_configuration_attrs,
        base_class=Device, **components)

    return new_class


@pytest.fixture(scope='class')
def ioc_sim(request):

    # setup code

    stdout = subprocess.PIPE
    stdin = None

    ioc_process = subprocess.Popen([sys.executable, '-m',
                                    'nslsii.iocs.lakeshore_ioc_sim'],
                                   stdout=stdout, stdin=stdin,
                                   env=os.environ)

    print(f'nslsii.iocs.lakeshore_ioc_sim is now running')

    time.sleep(5)

    MyLakeshore336 = lakeshore336()
    tc = MyLakeshore336('test:{', name='temp_controller')

    time.sleep(5)

    request.cls.tc = tc

    yield

    # teardown code

    ioc_process.terminate()


@pytest.mark.usefixtures('ioc_sim')
class TestIOC:

    def test_caproto_level(self):

        t_rb = read('test:{-Chan:A}T:C-I')
        assert t_rb.data[0] == 0.0

        c_sp = read('test:{-Out:1}T-SP')
        assert c_sp.data[0] == 0.0

        c_rb = read('test:{-Out:1}T-RB')
        assert c_rb.data[0] == 0.0

    def test_device_level(self):

        res = self.tc.temp.A.T_celsius.get()
        assert res == 0.0

        res = self.tc.ctrl.out1.setpoint.get()
        assert res == 0.0

        res = self.tc.ctrl.out1.target_channel.get()
        assert res == ''

    def test_target_channel(self):

        self.tc.ctrl.out1.target_channel.put('A')
        res = self.tc.ctrl.out1.target_channel.get()
        assert res == 'A'

    def test_alarm_low(self):

        new_value = 150.0

        res = self.tc.temp.A.alarm.low.get()
        assert res == 0

        self.tc.ctrl.out1.target_channel.put('A')
        self.tc.ctrl.out1.setpoint.put(new_value)

        res = self.tc.temp.A.alarm.low.get()
        assert res == 1

    def test_alarm_high(self):

        new_value = 450.0

        res = self.tc.temp.A.alarm.high.get()
        assert res == 0

        self.tc.ctrl.out1.target_channel.put('A')
        self.tc.ctrl.out1.setpoint.put(new_value)

        res = self.tc.temp.A.alarm.high.get()
        assert res == 1

    def test_1_A(self):

        value = self.tc.temp.A.T.get()
        new_value = value + 10

        rate = self.tc.ctrl.out1.ramp.rate.get()
        t = (new_value-value)/rate

        self.tc.ctrl.out1.target_channel.put('A')
        self.tc.ctrl.out1.setpoint.put(new_value)

        time.sleep(t+1)

        res = self.tc.ctrl.out1.done.get()
        assert res == 1

        res = self.tc.temp.A.T.get()
        assert res == new_value

    def test_2_B(self):

        value = self.tc.temp.B.T.get()
        new_value = value + 10

        rate = self.tc.ctrl.out2.ramp.rate.get()
        t = (new_value-value)/rate

        self.tc.ctrl.out2.target_channel.put('B')
        self.tc.ctrl.out2.setpoint.put(new_value)

        time.sleep(t+1)

        res = self.tc.ctrl.out2.done.get()
        assert res == 1

        res = self.tc.temp.B.T.get()
        assert res == new_value
