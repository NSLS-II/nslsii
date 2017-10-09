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

from ..devices.scaler import PrototypeEpicsScaler, StruckSIS3820MCS
from ..devices.areadetector import (StandardCam, NoStatsCam,
                                  ProductionCamStandard,
                                  ProductionCamTriggered)
from ..startup import db

def _setup_stats(cam_in):
    for k in (f'stats{j}' for j in range(1, 6)):
        cam_in.read_attrs.append(k)
        getattr(cam_in, k).read_attrs = ['total']

# TODO add to plugin
diag6_pid_threshold = EpicsSignal('XF:23ID1-BI{Diag:6-Cam:1}Stats1:CentroidThreshold',
        name = 'diag6_pid_threshold')

#
# Scalers both MCS and Standard
#

sclr = PrototypeEpicsScaler('XF:23ID1-ES{Sclr:1}', name='sclr')

for sig in sclr.channels.signal_names:
    getattr(sclr.channels, sig).name = 'sclr_' + sig.replace('an', '')

mcs = StruckSIS3820MCS('XF:23ID1-ES{Sclr:1}', name='mcs')

#
# Diagnostic Prosilica Cameras
#

slt1_cam = StandardCam('XF:23ID1-BI{Slt:1-Cam:1}', name='slt1_cam')

diag3 = StandardCam('XF:23ID1-BI{Diag:3-Cam:1}', name='diag3')
_setup_stats(diag3)

diag6 = NoStatsCam('XF:23ID1-BI{Diag:6-Cam:1}', name='diag6')

cube_beam = StandardCam('XF:23ID1-BI{Diag:5-Cam:1}', name='cube_beam')
_setup_stats(cube_beam)

dif_beam = StandardCam('XF:23ID1-ES{Dif-Cam:Beam}', name='dif_beam')
_setup_stats(dif_beam)

#
# FastCCD
#

fccd = ProductionCamTriggered('XF:23ID1-ES{FCCD}',
                              dg1_prefix='XF:23ID1-ES{Dly:1',
                              dg2_prefix='XF:23ID1-ES{Dly:2',
                              mcs_prefix='XF:23ID1-ES{Sclr:1}',
                              name='fccd')
fccd.read_attrs = ['hdf5','mcs.wfrm']
fccd.hdf5.read_attrs = []
fccd.hdf5._reg = db.reg
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


