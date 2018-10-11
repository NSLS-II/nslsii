from ophyd import DeviceStatus, Device, Component as Cpt, EpicsSignal, Signal
from time import sleep


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

    #Add the readback and setpoint components
    setpoint = Cpt(EpicsSignal, 'SP')
    readback = Cpt(EpicsSignal, 'I')

    # define the new set method with the new moving indicator
    def set(self, value):
        #define some required values
        set_value = value
        status = DeviceStatus(self, timeout=self.timeout.get())

        initial_timestamp = None

        # set up the done moving indicator logic
        def status_indicator(value, timestamp, **kwargs):
            nonlocal initial_timestamp
            if abs(value - set_value) < self.tolerance.get():
                if initial_timestamp:
                    if ((timestamp - initial_timestamp) >
                                          self.equilibrium_time.get()):
                        status._finished()
                        self.readback.clear_sub(status_indicator)
                else:
                    initial_timestamp = timestamp
            else:
                inband = False
                initial_timestamp = None

        # Start the move.
        self.setpoint.put(set_value)

        # subscribe to the read value to indicate the set is done.
        self.readback.subscribe(status_indicator)

        # hand the status object back to the RE
        return status
