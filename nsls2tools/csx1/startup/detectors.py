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

fccd_temp = EpicsSignalRO('XF:23ID1-ES{TCtrl:2-Chan:A}T:C-I', name='fccd_temp')

# Utility water temperature after mixing valve
#uw_temp = EpicsSignal('UT:SB1-Cu:1{}T:Spply_Ld-I', name='uw_temp')


# Calculated BPMs for combined EPUs
#angX = EpicsSignalRO('XF:23ID-ID{BPM}Val:AngleXS-I', name='angX')
#angY = EpicsSignalRO('XF:23ID-ID{BPM}Val:AngleYS-I', name='angY')

# CSX-1 Scalar

def _scaler_fields(attr_base, field_base, range_, **kwargs):
    defn = OrderedDict()
    for i in range_:
        attr = '{attr}{i}'.format(attr=attr_base, i=i)
        suffix = '{field}{i}'.format(field=field_base, i=i)
        defn[attr] = (EpicsSignalRO, suffix, kwargs)

    return defn


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

diag3 = StandardCam('XF:23ID1-BI{Diag:3-Cam:1}', name='diag3')
_setup_stats(diag3)

diag6 = NoStatsCam('XF:23ID1-BI{Diag:6-Cam:1}', name='diag6')

cube_beam = StandardCam('XF:23ID1-BI{Diag:5-Cam:1}', name='cube_beam')
_setup_stats(cube_beam)

dif_beam = StandardCam('XF:23ID1-ES{Dif-Cam:Beam}', name='dif_beam')
_setup_stats(dif_beam)

# Princeton CCD camera

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

