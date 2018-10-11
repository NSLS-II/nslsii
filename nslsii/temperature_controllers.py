from ophyd import DeviceStatus, Device, Component as Cpt, EpicsSignal, Signal


class Eurotherm(Device):
    '''This class is used for integrating with Eurotherm controllers.

    Parameters
    ----------
    PV_prefix : str.
        The PV prefix that is common to the readback and setpoint PV's.
    tolerance : float, optional.
        The range of temperature within which it can be considered constant.
        Default is 1.
    EquilibriumTime : float, optional.
        The time (in seconds) that a temperature should be within `tolerance`
        for it to be considered at equilibrium. Default is 5 seconds.
    Timeout : float, optional.
        The maximum time (in seconds) to wait for the temperature to reach
        equilibrium before raising a TimeOutError. Default is 30 seconds.
    '''

    def __init__(self, PV_prefix, **kwargs):
        super().__init__(PV_prefix, **kwargs)

    # Setup some new signals required for the moving indicator logic
    equilibrium_time = Cpt(Signal, value=5)
    timeout = Cpt(Signal, value=500)
    tolerance = Cpt(Signal, value=1)

    # Add the readback and setpoint components
    setpoint = Cpt(EpicsSignal, 'SP')
    readback = Cpt(EpicsSignal, 'I')

    _set_lock = False

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
                    if ((timestamp - initial_timestamp) > equilibrium_time):
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
