"""Classes to help with supporting AreaDetector 33 (and the
wait_for_plugins functionality)


This is actually adding a mix of functionality from AD 2-2 to 3-3 and
all of these names may change in the future.

"""

from ophyd import Device, Component as Cpt
from ophyd.areadetector.base import (ADComponent as C, ad_group,
                                     EpicsSignalWithRBV as SignalWithRBV)
from ophyd.areadetector.plugins import PluginBase
from ophyd.areadetector.trigger_mixins import TriggerBase, ADTriggerStatus
from ophyd.device import DynamicDeviceComponent as DDC, Staged
from ophyd.signal import (EpicsSignalRO, EpicsSignal, Signal)

from ophyd import (Kind, kind_context)
from ophyd.areadetector import (ADComponent as ADCpt, EpicsSignalWithRBV,
                                ImagePlugin, StatsPlugin, DetectorBase,
                                SingleTrigger, ADBase)
from ophyd.status import DeviceStatus
from ophyd import QuadEMPort, _current_fields

import time as ttime


class V22Mixin(Device):
    ...


class V26Mixin(V22Mixin):
    adcore_version = Cpt(EpicsSignalRO, 'ADCoreVersion_RBV',
                         string=True, kind='config')
    driver_version = Cpt(EpicsSignalRO, 'DriverVersion_RBV',
                         string=True, kind='config')


class V33Mixin(V26Mixin):
    ...


class CamV33Mixin(V33Mixin):
    wait_for_plugins = Cpt(EpicsSignal, 'WaitForPlugins',
                           string=True, kind='config')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs['wait_for_plugins'] = 'Yes'

    def ensure_nonblocking(self):
        self.stage_sigs['wait_for_plugins'] = 'Yes'
        for c in self.parent.component_names:
            cpt = getattr(self.parent, c)
            if cpt is self:
                continue
            if hasattr(cpt, 'ensure_nonblocking'):
                cpt.ensure_nonblocking()


class FilePluginV22Mixin(V22Mixin):
    create_directories = Cpt(EpicsSignal,
                             'CreateDirectory', kind='config')


class SingleTriggerV33(TriggerBase):
    _status_type = ADTriggerStatus

    def __init__(self, *args, image_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        if image_name is None:
            image_name = '_'.join([self.name, 'image'])
        self._image_name = image_name

    def trigger(self):
        "Trigger one acquisition."
        if self._staged != Staged.yes:
            raise RuntimeError("This detector is not ready to trigger."
                               "Call the stage() method before triggering.")

        self._status = self._status_type(self)

        def _acq_done(*args, **kwargs):
            # TODO sort out if anything useful in here
            self._status._finished()

        self._acquisition_signal.put(1, use_complete=True, callback=_acq_done)
        self.dispatch(self._image_name, ttime.time())
        return self._status


class StatsPluginV33(PluginBase):
    """This supports changes to time series PV names in AD 3-3

    Due to https://github.com/areaDetector/ADCore/pull/333
    """
    _default_suffix = 'Stats1:'
    _suffix_re = 'Stats\d:'
    _html_docs = ['NDPluginStats.html']
    _plugin_type = 'NDPluginStats'

    _default_configuration_attrs = (PluginBase._default_configuration_attrs + (
        'centroid_threshold', 'compute_centroid', 'compute_histogram',
        'compute_profiles', 'compute_statistics', 'bgd_width',
        'hist_size', 'hist_min', 'hist_max', 'ts_num_points', 'profile_size',
        'profile_cursor')
    )

    bgd_width = C(SignalWithRBV, 'BgdWidth')
    centroid_threshold = C(SignalWithRBV, 'CentroidThreshold')

    centroid = DDC(ad_group(EpicsSignalRO,
                            (('x', 'CentroidX_RBV'),
                             ('y', 'CentroidY_RBV'))),
                   doc='The centroid XY',
                   default_read_attrs=('x', 'y'))

    compute_centroid = C(SignalWithRBV, 'ComputeCentroid', string=True)
    compute_histogram = C(SignalWithRBV, 'ComputeHistogram', string=True)
    compute_profiles = C(SignalWithRBV, 'ComputeProfiles', string=True)
    compute_statistics = C(SignalWithRBV, 'ComputeStatistics', string=True)

    cursor = DDC(ad_group(SignalWithRBV,
                          (('x', 'CursorX'),
                           ('y', 'CursorY'))),
                 doc='The cursor XY',
                 default_read_attrs=('x', 'y'))

    hist_entropy = C(EpicsSignalRO, 'HistEntropy_RBV')
    hist_max = C(SignalWithRBV, 'HistMax')
    hist_min = C(SignalWithRBV, 'HistMin')
    hist_size = C(SignalWithRBV, 'HistSize')
    histogram = C(EpicsSignalRO, 'Histogram_RBV')

    max_size = DDC(ad_group(EpicsSignal,
                            (('x', 'MaxSizeX'),
                             ('y', 'MaxSizeY'))),
                   doc='The maximum size in XY',
                   default_read_attrs=('x', 'y'))

    max_value = C(EpicsSignalRO, 'MaxValue_RBV')
    max_xy = DDC(ad_group(EpicsSignalRO,
                          (('x', 'MaxX_RBV'),
                           ('y', 'MaxY_RBV'))),
                 doc='Maximum in XY',
                 default_read_attrs=('x', 'y'))

    mean_value = C(EpicsSignalRO, 'MeanValue_RBV')
    min_value = C(EpicsSignalRO, 'MinValue_RBV')

    min_xy = DDC(ad_group(EpicsSignalRO,
                          (('x', 'MinX_RBV'),
                           ('y', 'MinY_RBV'))),
                 doc='Minimum in XY',
                 default_read_attrs=('x', 'y'))

    net = C(EpicsSignalRO, 'Net_RBV')
    profile_average = DDC(ad_group(EpicsSignalRO,
                                   (('x', 'ProfileAverageX_RBV'),
                                    ('y', 'ProfileAverageY_RBV'))),
                          doc='Profile average in XY',
                          default_read_attrs=('x', 'y'))

    profile_centroid = DDC(ad_group(EpicsSignalRO,
                                    (('x', 'ProfileCentroidX_RBV'),
                                     ('y', 'ProfileCentroidY_RBV'))),
                           doc='Profile centroid in XY',
                           default_read_attrs=('x', 'y'))

    profile_cursor = DDC(ad_group(EpicsSignalRO,
                                  (('x', 'ProfileCursorX_RBV'),
                                   ('y', 'ProfileCursorY_RBV'))),
                         doc='Profile cursor in XY',
                         default_read_attrs=('x', 'y'))

    profile_size = DDC(ad_group(EpicsSignalRO,
                                (('x', 'ProfileSizeX_RBV'),
                                 ('y', 'ProfileSizeY_RBV'))),
                       doc='Profile size in XY',
                       default_read_attrs=('x', 'y'))

    profile_threshold = DDC(ad_group(EpicsSignalRO,
                                     (('x', 'ProfileThresholdX_RBV'),
                                      ('y', 'ProfileThresholdY_RBV'))),
                            doc='Profile threshold in XY',
                            default_read_attrs=('x', 'y'))

    set_xhopr = C(EpicsSignal, 'SetXHOPR')
    set_yhopr = C(EpicsSignal, 'SetYHOPR')
    sigma_xy = C(EpicsSignalRO, 'SigmaXY_RBV')
    sigma_x = C(EpicsSignalRO, 'SigmaX_RBV')
    sigma_y = C(EpicsSignalRO, 'SigmaY_RBV')
    sigma = C(EpicsSignalRO, 'Sigma_RBV')
    ts_acquiring = C(EpicsSignal, 'TS:TSAcquiring')

    ts_centroid = DDC(ad_group(EpicsSignal,
                               (('x', 'TS:TSCentroidX'),
                                ('y', 'TS:TSCentroidY'))),
                      doc='Time series centroid in XY',
                      default_read_attrs=('x', 'y'))

    # ts_control = C(EpicsSignal, 'TS:TSControl', string=True)
    ts_current_point = C(EpicsSignal, 'TS:TSCurrentPoint')
    ts_max_value = C(EpicsSignal, 'TS:TSMaxValue')

    ts_max = DDC(ad_group(EpicsSignal,
                          (('x', 'TS:TSMaxX'),
                           ('y', 'TS:TSMaxY'))),
                 doc='Time series maximum in XY',
                 default_read_attrs=('x', 'y'))

    ts_mean_value = C(EpicsSignal, 'TS:TSMeanValue')
    ts_min_value = C(EpicsSignal, 'TS:TSMinValue')

    ts_min = DDC(ad_group(EpicsSignal,
                          (('x', 'TS:TSMinX'),
                           ('y', 'TS:TSMinY'))),
                 doc='Time series minimum in XY',
                 default_read_attrs=('x', 'y'))

    ts_net = C(EpicsSignal, 'TS:TSNet')
    ts_num_points = C(EpicsSignal, 'TS:TSNumPoints')
    ts_read = C(EpicsSignal, 'TS:TSRead')
    ts_sigma = C(EpicsSignal, 'TS:TSSigma')
    ts_sigma_x = C(EpicsSignal, 'TS:TSSigmaX')
    ts_sigma_xy = C(EpicsSignal, 'TS:TSSigmaXY')
    ts_sigma_y = C(EpicsSignal, 'TS:TSSigmaY')
    ts_total = C(EpicsSignal, 'TS:TSTotal')
    total = C(EpicsSignalRO, 'Total_RBV')


class QuadEMV33(SingleTrigger, DetectorBase):
    # These settings intentionally shadow the settings inherited from
    # DetectorBase.
    _default_read_attrs = None
    _default_configuration_attrs = None

    _status_type = DeviceStatus  # overrriding the default in SingleTrigger

    # This is needed because ophyd verifies that it can see all
    # of the nodes in the asyn pipeline, however these IOCs do not
    # expose their port name via a PV, but nevertheless server as the
    # root node for the plugins.
    # Leaving this port_name here for compatibility
    integration_time = Cpt(EpicsSignalWithRBV, 'IntegrationTime',
                           kind='config')
    averaging_time = Cpt(EpicsSignalWithRBV, 'AveragingTime', kind='config')
    with kind_context('omitted') as OCpt:
        conf = Cpt(QuadEMPort, port_name='NSLS_EM')
        model = OCpt(EpicsSignalRO, 'Model')
        firmware = OCpt(EpicsSignalRO, 'Firmware')

        acquire_mode = OCpt(EpicsSignalWithRBV, 'AcquireMode')
        acquire = OCpt(EpicsSignal, 'Acquire')

        read_format = OCpt(EpicsSignalWithRBV, 'ReadFormat')
        em_range = OCpt(EpicsSignalWithRBV, 'Range')
        ping_pong = OCpt(EpicsSignalWithRBV, 'PingPong')

        num_channels = OCpt(EpicsSignalWithRBV, 'NumChannels')
        geometry = OCpt(EpicsSignalWithRBV, 'Geometry')
        resolution = OCpt(EpicsSignalWithRBV, 'Resolution')

        bias_state = OCpt(EpicsSignalWithRBV, 'BiasState')
        bias_interlock = OCpt(EpicsSignalWithRBV, 'BiasInterlock')
        bias_voltage = OCpt(EpicsSignalWithRBV, 'BiasVoltage')
        hvs_readback = OCpt(EpicsSignalRO, 'HVSReadback')
        hvv_readback = OCpt(EpicsSignalRO, 'HVVReadback')
        hvi_readback = OCpt(EpicsSignalRO, 'HVIReadback')

        values_per_read = OCpt(EpicsSignalWithRBV, 'ValuesPerRead')
        sample_time = OCpt(EpicsSignalRO, 'SampleTime_RBV')  # yay consistency
        num_average = OCpt(EpicsSignalRO, 'NumAverage_RBV')
        num_averaged = OCpt(EpicsSignalRO, 'NumAveraged_RBV')
        num_acquire = OCpt(EpicsSignalWithRBV, 'NumAcquire')
        num_acquired = OCpt(EpicsSignalRO, 'NumAcquired')
        read_data = OCpt(EpicsSignalRO, 'ReadData')
        ring_overflows = OCpt(EpicsSignalRO, 'RingOverflows')
        trigger_mode = OCpt(EpicsSignal, 'TriggerMode')
        reset = OCpt(EpicsSignal, 'Reset')

    current_names = DDCpt(_current_fields('ch', 'CurrentName', range(1, 5),
                                          string=True))
    current_offsets = DDCpt(_current_fields('ch', 'CurrentOffset',
                                            range(1, 5)))
    current_offset_calcs = DDCpt(_current_fields('ch', 'ComputeCurrentOffset',
                                                 range(1, 5)))
    current_scales = DDCpt(_current_fields('ch', 'CurrentScale', range(1, 5)))

    position_offset_x = Cpt(EpicsSignal, 'PositionOffsetX')
    position_offset_y = Cpt(EpicsSignal, 'PositionOffsetY')

    position_offset_calc_x = Cpt(EpicsSignal, 'ComputePosOffsetX')
    position_offset_calc_y = Cpt(EpicsSignal, 'ComputePosOffsetY')

    position_scale_x = Cpt(EpicsSignal, 'PositionScaleX')
    position_scale_Y = Cpt(EpicsSignal, 'PositionScaleY')

    image = ADCpt(ImagePlugin, 'image1:')
    current1 = ADCpt(StatsPluginV33, 'Current1:')
    current2 = ADCpt(StatsPluginV33, 'Current2:')
    current3 = ADCpt(StatsPluginV33, 'Current3:')
    current4 = ADCpt(StatsPluginV33, 'Current4:')

    sum_all = ADCpt(StatsPluginV33, 'SumAll:')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.stage_sigs.update([('acquire', 0),  # if acquiring, stop
                                ('acquire_mode', 2)  # single mode
                                ])
        self._acquisition_signal = self.acquire

        for i in range(1, 5):
            current = getattr(self, 'current{}'.format(i))
            current.mean_value.kind = Kind.hinted
