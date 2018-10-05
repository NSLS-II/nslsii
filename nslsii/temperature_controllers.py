from ophyd import DeviceStatus
from ophyd.mixins import EpicsSignalPositioner
from time import sleep


class Eurotherm(EpicsSignalPositioner):
    '''This class is used for integrating with Eurotherm controllers.

    Parameters
    ----------
    PV_prefix : str.
        The PV prefix that is common to the readback and setpoint PV's.
    tolerance : float, optional.
        The range of temperature within which it can be considered constant.
        Default is 1.
    equilibrium_time : float, optional.
        The time (in seconds) that a temperature should be within `tolerance`
        for it to be considered at equilibrium. Default is 5 seconds.
    timeout : float, optional.
        The maximum time (in seconds) to wait for the temperature to reach
        equilibrium before raising a TimeOutError. Default is 30 seconds.
    PV_read_suffix, PV_write_suffix : str, optional
        The suffix for the readback and setpoint PV's respectively. Defaults
        are `'-I'` and `'-SP'` respectively.
    '''

    def __init__(self, PV_prefix, tolerance=1, equilibrium_time=5,
                 timeout=30, PV_read_suffix='-I', PV_write_suffix='-SP',
                 **kwargs):
        self.read_pv = PV_prefix+PV_read_suffix
        self.write_pv = PV_prefix+PV_write_suffix
        super().__init__(read_pv=self.read_pv, write_pv=self.write_pv,
                         tolerance=tolerance, **kwargs)
        self._equilibrium_time = equilibrium_time
        self._timeout = timeout

    # Setup some new signals required for the moving indicator logic
    # This approach mirrors that used for tolerance in ophyd/signal/Signal
    @property
    def equilibrium_time(self):
        '''The time that a temperature should be within `tolerance` for it to
        be considered at equilibrium.
        '''
        return self._equilibrium_time

    @equilibrium_time.setter
    def equilibrium_time(self, equilibrium_time):
        '''The setter for equilibrium_time
        '''
        self._equilibrium_time = equilibrium_time

    @property
    def timeout(self):
        '''The maximum time to wait for the temperature to reach equilibrium
        before raising an TimeOutError.
        '''
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        '''The setter for timeout
        '''
        self._timeout = timeout

    # define the new set method with the new moving indicator logic
    def set(self, value):
        # define some required values
        set_value = value
        status = DeviceStatus(self, timeout=self.timeout)

        # set up the done moving indicator logic
        def status_indicator(value):
            if abs(value - set_value) < self.tolerance:
                sleep(self.equilibrium_time)
                if abs(self.position - set_value) < self.tolerance:
                    status._finished()
                    self.position.clear_sub(status_indicator)

        # Start the move.
        self.put(set_value)

        # subscribe to the read value to indicate the set is done.
        self.position.subscribe(status_indicator)

        # hand the status object back to the RE
        return status
