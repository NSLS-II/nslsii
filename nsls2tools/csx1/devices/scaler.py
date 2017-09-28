from ophyd import Device
from ophyd.device import Component as Cpt
from ophyd.device import DynamicDeviceComponent as DDCpt
from ophyd import EpicsSignal, EpicsSignalRO, OrderedDict

def _scaler_fields(attr_base, field_base, range_, **kwargs):
    defn = OrderedDict()
    for i in range_:
        attr = '{attr}{i}'.format(attr=attr_base, i=i)
        suffix = '{field}{i}'.format(field=field_base, i=i)
        defn[attr] = (EpicsSignalRO, suffix, kwargs)

    return defn

class PrototypeEpicsScaler(Device):
    '''SynApps Scaler Record interface'''

    # tigger + trigger mode
    count = Cpt(EpicsSignal, '.CNT', trigger_value=1)
    count_mode = Cpt(EpicsSignal, '.CONT', string=True)

    # delay from triggering to starting counting
    delay = Cpt(EpicsSignal, '.DLY')
    auto_count_delay = Cpt(EpicsSignal, '.DLY1')

    # the data
    channels = DDCpt(_scaler_fields('chan', '.S', range(1, 33)))
    names = DDCpt(_scaler_fields('name', '.NM', range(1, 33)))

    time = Cpt(EpicsSignal, '.T')
    freq = Cpt(EpicsSignal, '.FREQ')

    preset_time = Cpt(EpicsSignal, '.TP')
    auto_count_time = Cpt(EpicsSignal, '.TP1')

    presets = DDCpt(_scaler_fields('preset', '.PR', range(1, 33)))
    gates = DDCpt(_scaler_fields('gate', '.G', range(1, 33)))

    update_rate = Cpt(EpicsSignal, '.RATE')
    auto_count_update_rate = Cpt(EpicsSignal, '.RAT1')

    egu = Cpt(EpicsSignal, '.EGU')

    def __init__(self, prefix, *, read_attrs=None, configuration_attrs=None,
                 name=None, parent=None, **kwargs):
        if read_attrs is None:
            read_attrs = ['channels', 'time']

        if configuration_attrs is None:
            configuration_attrs = ['preset_time', 'presets', 'gates',
                                   'names', 'freq', 'auto_count_time',
                                   'count_mode', 'delay',
                                   'auto_count_delay', 'egu']

        super().__init__(prefix, read_attrs=read_attrs,
                         configuration_attrs=configuration_attrs,
                         name=name, parent=parent, **kwargs)

        self.stage_sigs.update([(self.count_mode, 0)])


def _mcs_fields(cls, attr_base, pv_base, nrange, field, **kwargs):
    defn = OrderedDict()
    for i in nrange:
        attr = '{}_{}'.format(attr_base, i)
        suffix = '{}{}{}'.format(pv_base, i, field)
        defn[attr] = (cls, suffix, kwargs)

    return defn


class StruckSIS3820MCS(Device):
    _default_configuration_attrs = ('input_mode', 'output_mode',
                                    'output_polarity', 'channel_advance',
                                    'count_on_start', 'max_channels')
    _default_read_attrs = ('wfrm',)

    erase_start = Cpt(EpicsSignal, 'EraseStart')
    erase_all = Cpt(EpicsSignal, 'EraseAll')
    start_all = Cpt(EpicsSignal, 'StartAll')
    stop_all = Cpt(EpicsSignal, 'StopAll', put_complete=True)
    acquiring = Cpt(EpicsSignalRO, 'Acquiring')

    input_mode = Cpt(EpicsSignal, 'InputMode')
    output_mode = Cpt(EpicsSignal, 'OutputMode')
    output_polarity = Cpt(EpicsSignal, 'OutputPolarity')

    channel_advance = Cpt(EpicsSignal, 'ChannelAdvance')
    soft_channel_advance = Cpt(EpicsSignal, 'SoftwareChannelAdvance',
                               put_complete=True)

    count_on_start = Cpt(EpicsSignal, 'CountOnStart')
    acquire_mode = Cpt(EpicsSignal, 'AcquireMode')

    max_channels = Cpt(EpicsSignalRO, 'MaxChannels')

    read_all = Cpt(EpicsSignal, 'ReadAll')
    n_use_all = Cpt(EpicsSignal, 'NUseAll')

    current_channel = Cpt(EpicsSignalRO, 'CurrentChannel')

    wfrm = DDCpt(_mcs_fields(EpicsSignalRO,
                           'wfrm', 'Wfrm:', range(1, 33), ''))
    wfrm_proc = DDCpt(_mcs_fields(EpicsSignal,
                                'wfrm_proc', 'Wfrm:', range(1, 33), '.PROC',
                                put_complete=True))

    def trigger(self):
        self.erase_start.put(1)
        return super().trigger()

    def read(self):
        # Here we stop and poke the proc fields
        self.soft_channel_advance.put(1, wait=True)
        self.stop_all.put(1, wait=True)

        for sn in self.wfrm_proc.signal_names:
            getattr(self.wfrm_proc, sn).put(1)

        return super().read()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs['input_mode'] = 3
        self.stage_sigs['acquire_mode'] = 0
        self.stage_sigs['count_on_start'] = 0
        self.stage_sigs['channel_advance'] = 1

