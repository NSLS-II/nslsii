from __future__ import annotations

import threading

from ophyd import Component as Cpt
from ophyd import Device, DeviceStatus, EpicsSignal, Signal


class Eurotherm(Device):
    """This class is used for integrating with Eurotherm controllers.

    This is used for Eurotherm controllers and is designed to ensure that the
    set returns 'done' status only after the temperature has reached
    equilibrium at the required value not when it first reaches the required
    value. This is done via the attributes `self.equilibrium_time` and
    `self.tolerance`. It only returns `done` if `self.readback` remains within
    `self.tolerance` of `self.setpoint` over `self.equilibrium_time`. A third
    attribute, `self.timeout`, is used to determeine the maximum time to wait
    for equilibrium. If it takes longer than this it raises a TimeoutError.

    Parameters
    ----------
    pv_prefix : str.
        The PV prefix that is common to the readback and setpoint PV's.
    """

    def __init__(self, pv_prefix, **kwargs):
        super().__init__(pv_prefix, **kwargs)
        self._set_lock = threading.Lock()

        # defining these here so that they can be used by `set` and `start`
        self._cb_timer = None
        self._cid = None

    # Setup some new signals required for the moving indicator logic
    equilibrium_time = Cpt(Signal, value=5, kind="config")
    timeout = Cpt(Signal, value=500, kind="config")
    tolerance = Cpt(Signal, value=1, kind="config")

    # Add the readback and setpoint components
    setpoint = Cpt(EpicsSignal, "T-SP", kind="normal")
    readback = Cpt(EpicsSignal, "T-RB", kind="hinted")

    # define the new set method with the new moving indicator
    def set(self, value):
        # check that a set is not in progress, and if not set the lock.
        if not self._set_lock.acquire(blocking=False):
            raise SetInProgress(
                f"attempting to set {self.name} " + "while a set is in progress"
            )

        # define some required values
        set_value = value
        status = DeviceStatus(self)

        initial_timestamp = None

        # grab these values here to avoidmutliple calls.
        equilibrium_time = self.equilibrium_time.get()
        tolerance = self.tolerance.get()

        # setup a cleanup function for the timer, this matches including
        # timeout in `status` but also ensures that the callback is removed.
        def timer_cleanup():
            print(f"Set of {self.name} timed out after {self.timeout.get()} s")
            self._set_lock.release()
            self.readback.clear_sub(status_indicator)
            status._finished(success=False)

        self._cb_timer = threading.Timer(self.timeout.get(), timer_cleanup)

        # set up the done moving indicator logic
        def status_indicator(value, timestamp, **kwargs):
            # add a Timer to ensure that timeout occurs.
            if not self._cb_timer.is_alive():
                self._cb_timer.start()

            nonlocal initial_timestamp
            if abs(value - set_value) < tolerance:
                if initial_timestamp:
                    if (timestamp - initial_timestamp) > equilibrium_time:
                        status._finished()
                        self._cb_timer.cancel()
                        self._set_lock.release()
                        self.readback.clear_sub(status_indicator)
                else:
                    initial_timestamp = timestamp
            else:
                initial_timestamp = None

        # Start the move.
        self.setpoint.put(set_value)

        # subscribe to the read value to indicate the set is done.
        self._cid = self.readback.subscribe(status_indicator)

        # hand the status object back to the RE
        return status

    def stop(self, success=False):
        # override the lock, cancel the timer and remove the subscription on any
        # in progress sets
        self._set_lock.release()
        self._cb_timer.cancel()
        self.readback.unsubscribe(self._cid)
        # set the controller to the current value (best option we came up with)
        self.set(self.readback.get())


class SetInProgress(RuntimeError): ...
