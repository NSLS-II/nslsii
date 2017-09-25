from ophyd.device import (Component as C, DynamicDeviceComponent as DDC)
from ophyd import (EpicsScaler, EpicsSignal, EpicsSignalRO, Device, SingleTrigger, HDF5Plugin,
                           ImagePlugin, StatsPlugin, ROIPlugin, TransformPlugin)
from ophyd.areadetector.cam import AreaDetectorCam
from ophyd.areadetector.detectors import DetectorBase
from ophyd.areadetector.filestore_mixins import FileStoreHDF5IterativeWrite
from ophyd.areadetector import ADComponent, EpicsSignalWithRBV
from ophyd.areadetector.plugins import PluginBase, ProcessPlugin
from ophyd import Component as Cpt
from ophyd import AreaDetector
from bluesky.examples import NullStatus
from collections import OrderedDict
import bluesky.plans as bp


def _setup_stats(cam_in):
    for k in (f'stats{j}' for j in range(1, 6)):
        cam_in.read_attrs.append(k)
        getattr(cam_in, k).read_attrs = ['total']


# Ring current

# TODO Make this a Device so it can be used by bluesky.
ring_curr = EpicsSignalRO('XF:23ID-SR{}I-I', name='ring_curr')

# TODO Make this a Device so it can be used by bluesky.
diag6_monitor = EpicsSignal('XF:23ID1-BI{Diag:6-Cam:1}Stats1:Total_RBV',
                            name='diag6_monitor')


diag6_pid_threshold = EpicsSignal('XF:23ID1-BI{Diag:6-Cam:1}Stats1:CentroidThreshold',name =  'diag6_pid_threshold')

#

# FCCD sensor temperature
fccd_temp = EpicsSignalRO('XF:23ID1-ES{TCtrl:2-Chan:A}T:C-I', name='fccd_temp')

# Utility water temperature after mixing valve
#uw_temp = EpicsSignal('UT:SB1-Cu:1{}T:Spply_Ld-I', name='uw_temp')


# Calculated BPMs for combined EPUs
angX = EpicsSignalRO('XF:23ID-ID{BPM}Val:AngleXS-I', name='angX')

angY = EpicsSignalRO('XF:23ID-ID{BPM}Val:AngleYS-I', name='angY')

# EPU1 positions for commissioning
epu1_x_off = EpicsSignalRO('SR:C31-{AI}23:FPGA:x_mm-I', name='epu1_x_off')

epu1_x_ang = EpicsSignalRO('SR:C31-{AI}23:FPGA:x_mrad-I', name='epu1_x_ang')

epu1_y_off = EpicsSignalRO('SR:C31-{AI}23:FPGA:y_mm-I', name='epu1_y_off')

epu1_y_ang = EpicsSignalRO('SR:C31-{AI}23:FPGA:y_mrad-I', name='epu1_y_ang')


# EPU2 positions for commissioning
epu2_x_off = EpicsSignalRO('SR:C31-{AI}23-2:FPGA:x_mm-I', name='epu2_x_off')

epu2_x_ang = EpicsSignalRO('SR:C31-{AI}23-2:FPGA:x_mrad-I', name='epu2_x_ang')

epu2_y_off = EpicsSignalRO('SR:C31-{AI}23-2:FPGA:y_mm-I', name='epu2_y_off')

epu2_y_ang = EpicsSignalRO('SR:C31-{AI}23-2:FPGA:y_mrad-I', name='epu2_y_ang')


# CSX-1 Scalar

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
    count = C(EpicsSignal, '.CNT', trigger_value=1)
    count_mode = C(EpicsSignal, '.CONT', string=True)

    # delay from triggering to starting counting
    delay = C(EpicsSignal, '.DLY')
    auto_count_delay = C(EpicsSignal, '.DLY1')

    # the data
    channels = DDC(_scaler_fields('chan', '.S', range(1, 33)))
    names = DDC(_scaler_fields('name', '.NM', range(1, 33)))

    time = C(EpicsSignal, '.T')
    freq = C(EpicsSignal, '.FREQ')

    preset_time = C(EpicsSignal, '.TP')
    auto_count_time = C(EpicsSignal, '.TP1')

    presets = DDC(_scaler_fields('preset', '.PR', range(1, 33)))
    gates = DDC(_scaler_fields('gate', '.G', range(1, 33)))

    update_rate = C(EpicsSignal, '.RATE')
    auto_count_update_rate = C(EpicsSignal, '.RAT1')

    egu = C(EpicsSignal, '.EGU')

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


sclr = PrototypeEpicsScaler('XF:23ID1-ES{Sclr:1}', name='sclr')
for sig in sclr.channels.signal_names:
    getattr(sclr.channels, sig).name = 'sclr_' + sig.replace('an', '')


def sclr_to_monitor_mode(sclr, count_time):
    # remeber sclr.auto_count_delay
    yield from bp.mv(sclr.auto_count_time, count_time)
    yield from bp.mv(sclr.auto_count_update_rate, 0)
    yield from bp.mv(sclr.count_mode, 'AutoCount')


class Temperature(Device):
    a = Cpt(EpicsSignalRO, '-Chan:A}T-I')
    b = Cpt(EpicsSignalRO, '-Chan:B}T-I')


temp = Temperature('XF:23ID1-ES{TCtrl:1', name='temp')


class StandardCam(SingleTrigger, AreaDetector):
    stats1 = Cpt(StatsPlugin, 'Stats1:')
    stats2 = Cpt(StatsPlugin, 'Stats2:')
    stats3 = Cpt(StatsPlugin, 'Stats3:')
    stats4 = Cpt(StatsPlugin, 'Stats4:')
    stats5 = Cpt(StatsPlugin, 'Stats5:')
    roi1 = Cpt(ROIPlugin, 'ROI1:')
    roi2 = Cpt(ROIPlugin, 'ROI2:')
    roi3 = Cpt(ROIPlugin, 'ROI3:')
    roi4 = Cpt(ROIPlugin, 'ROI4:')

    proc1 = Cpt(ProcessPlugin, 'Proc1:')


class NoStatsCam(SingleTrigger, AreaDetector):
    pass


class HDF5PluginWithFileStore(HDF5Plugin, FileStoreHDF5IterativeWrite):
    # AD v2.2.0 (at least) does not have this. It is present in v1.9.1.
    file_number_sync = None

    def get_frames_per_point(self):
        return self.parent.cam.num_images.get()

class FCCDCam(AreaDetectorCam):
    sdk_version = Cpt(EpicsSignalRO, 'SDKVersion_RBV')
    firmware_version = Cpt(EpicsSignalRO, 'FirmwareVersion_RBV')
    overscan = Cpt(EpicsSignal, 'Overscan')
    fcric_gain = Cpt(EpicsSignal, 'FCRICGain')
    fcric_clamp = Cpt(EpicsSignal, 'FCRICClamp')



class ProductionCamBase(DetectorBase):
    # # Trying to add useful info..
    cam = Cpt(FCCDCam, "cam1:")
    stats1 = Cpt(StatsPlugin, 'Stats1:')
    stats2 = Cpt(StatsPlugin, 'Stats2:')
    stats3 = Cpt(StatsPlugin, 'Stats3:')
    stats4 = Cpt(StatsPlugin, 'Stats4:')
    stats5 = Cpt(StatsPlugin, 'Stats5:')
    roi1 = Cpt(ROIPlugin, 'ROI1:')
    roi2 = Cpt(ROIPlugin, 'ROI2:')
    roi3 = Cpt(ROIPlugin, 'ROI3:')
    roi4 = Cpt(ROIPlugin, 'ROI4:')
    trans1 = Cpt(TransformPlugin, 'Trans1:')

    proc1 = Cpt(ProcessPlugin, 'Proc1:')

    dg2 = DelayGenerator('XF:23ID1-ES{Dly:2')
    dg1 = DelayGenerator('XF:23ID1-ES{Dly:1')

    # This does nothing, but it's the right place to add code to be run
    # once at instantiation time.
    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)

    def pause(self):              #Dan Allen added to make bsui stop progress bar on ^C
        self.cam.acquire.put(0)
        super().pause()


class ProductionCamStandard(SingleTrigger, ProductionCamBase):

    hdf5 = Cpt(HDF5PluginWithFileStore,
               suffix='HDF1:',
               write_path_template='/GPFS/xf23id/xf23id1/fccd_data/%Y/%m/%d/',
               root='/GPFS/xf23id/xf23id1/',
               reg=db.reg)

    def stop(self):
        self.hdf5.capture.put(0)
        return super().stop()

    def pause(self):
        self.hdf5.capture.put(0)
        return super().pause()

    def resume(self):
        self.hdf5.capture.put(1)
        return super().resume()


class TestCam(SingleTrigger, AreaDetector):
    "writes data to test driectory"
    hdf5 = Cpt(HDF5PluginWithFileStore,
               suffix='HDF1:',
               write_path_template='/GPFS/xf23id/xf23id1/test_data/%Y/%m/%d/',
               root='/GPFS/xf23id/xf23id1/',
               reg=db.reg)
    # The trailing '/' is essential!!


diag3 = StandardCam('XF:23ID1-BI{Diag:3-Cam:1}', name='diag3')
# this is for the cube diag for now (es_diag_cam_2)
# diag5 = StandardCam('XF:23ID1-BI{Diag:5-Cam:1}', name='diag5')
diag6 = NoStatsCam('XF:23ID1-BI{Diag:6-Cam:1}', name='diag6')


# for aligning im MuR mode - TODO replace PV with better description
cube_beam = StandardCam('XF:23ID1-BI{Diag:5-Cam:1}', name='cube_beam')

_setup_stats(cube_beam)

dif_beam = StandardCam('XF:23ID1-ES{Dif-Cam:Beam}', name='dif_beam')
# fs1 = StandardCam('XF:23IDA-BI:1{FS:1-Cam:1}', name='fs1')

_setup_stats(dif_beam)

# Princeton CCD camera

# pimte = AreaDetectorFileStorePrinceton('XF:23ID1-ES{Dif-Cam:PIMTE}',
#                                        file_path='/GPFS/xf23id/xf23id1/pimte_data/',
#                                       ioc_file_path='x:/xf23id1/pimte_data/',
#                                       name='pimte')

class FastShutter(Device):
    shutter = Cpt(EpicsSignal, 'XF:23ID1-TS{EVR:1-Out:FP0}Src:Scale-RB',
                  write_pv='XF:23ID1-TS{EVR:1-Out:FP0}Src:Scale-SP')
    # TODO THIS POLARITY IS JUST A GUESS -- CHECK!!

    def open(self):
        self.shutter.put(1)

    def close(self):
        self.shutter.put(0)


fccd = ProductionCamStandard('XF:23ID1-ES{FCCD}', name='fccd')
fccd.read_attrs = ['hdf5']
fccd.hdf5.read_attrs = []
fccd.configuration_attrs = ['cam.acquire_time',
                            'cam.acquire_period',
                            'cam.image_mode',
                            'cam.num_images',
                            'cam.sdk_version',
                            'cam.firmware_version',
                            'cam.overscan',
                            'cam.fcric_gain',
                            'cam.fcric_clamp',
                            'dg2.A', 'dg2.B',
                            'dg2.C', 'dg2.D',
                            'dg2.E', 'dg2.F',
                            'dg2.G', 'dg2.H',
                            'dg1.A', 'dg1.B',
                            'dg1.C', 'dg1.D',
                            'dg1.E', 'dg1.F',
                            'dg1.G', 'dg1.H']

_setup_stats(fccd)

mcs = StruckSIS3820MCS('XF:23ID1-ES{Sclr:1}', name='mcs')

