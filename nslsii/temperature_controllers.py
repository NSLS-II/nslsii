from ophyd import DeviceStatus, Device, Component as Cpt, EpicsSignal, Signal


class Eurotherm(Device):
    '''This class is used for integrating with Eurotherm controllers.

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
    '''

    def __init__(self, pv_prefix, **kwargs):
        super().__init__(pv_prefix, **kwargs)
        self._set_lock = False

    # Setup some new signals required for the moving indicator logic
    equilibrium_time = Cpt(Signal, value=5)
    timeout = Cpt(Signal, value=500)
    tolerance = Cpt(Signal, value=1)

    # Add the readback and setpoint components
    setpoint = Cpt(EpicsSignal, 'SP')
    readback = Cpt(EpicsSignal, 'I')

    # define the new set method with the new moving indicator
    def set(self, value):
        # check that a set is not in progress, and if not set the lock.
        if self._set_lock:
            raise Exception('attempting to set {}'.format(self.name) +
                            'while a set is in progress'.format(self.name))
        self._set_lock = True

        # define some required values
        set_value = value
        status = DeviceStatus(self, timeout=self.timeout.get())

        initial_timestamp = None

        # grab these values here to avoidmutliple calls.
        equilibrium_time = self.equilibrium_time.get()
        tolerance = self.tolerance.get()

        # set up the done moving indicator logic
        def status_indicator(value, timestamp, **kwargs):
            nonlocal initial_timestamp
            if abs(value - set_value) < tolerance:
                if initial_timestamp:
                    if (timestamp - initial_timestamp) > equilibrium_time:
                        status._finished()
                        self._set_lock = False
                        self.readback.clear_sub(status_indicator)
                else:
                    initial_timestamp = timestamp
            else:
                initial_timestamp = None

        # Start the move.
        self.setpoint.put(set_value)

        # subscribe to the read value to indicate the set is done.
        self.readback.subscribe(status_indicator)

        # hand the status object back to the RE
        return status

    def stop(self):
        # overide the lock on any in progress sets
        self._set_lock = False
        # set the controller to the current value (best option we came up with)
        self.set(self.readback.get())
