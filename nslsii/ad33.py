"""Classes to help with supporting AreaDetector 33 (and the
wait_for_plugins functionality)


This is actually adding a mix of functionality from AD 2-2 to 3-3 and
all of these names may change in the future.

"""
from ophyd import Device, Component as Cpt
from ophyd.device import Staged
from ophyd.signal import EpicsSignalRO, EpicsSignal
from ophyd.areadetector.trigger_mixins import TriggerBase, ADTriggerStatus
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
        self.ensure_nonblocking()

    def ensure_nonblocking(self):
        self.stage_sigs['wait_for_plugins'] = 'Yes'
        for c in self.parent.component_names:
            cpt = getattr(self, c)
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
