from nslsii.EPS_devices.valves_and_shutters import (
    EPSTwoStateDevice, NSLSIIValvesAndShuttersEnableError)
from bluesky import RunEngine
from bluesky.plan_stubs import mv
from bluesky.utils import FailedStatus
from ophyd import Device, Component as Cpt, EpicsSignal
import os
import subprocess
import sys
import time
import pytest

RE=RunEngine()


def test_EPSTwoStateDevice():
    '''A test of the EPSTwoStateDevice class.

    This test covers 3 known failure modes which are modelled using the caproto
    IOC found at ``nslsii/iocs/eps_two_state_ioc_sim/EPSTwoStateIOC``. The 3
    failure modes are:
        1. Retry Activation Error.
            - Actuating the 'cmd_sig' PV does not always work on the first try.
        2. Hardware Activation Error.
            - In this case the hardware reports an error in the move which
              leaves the ``fail_to_cls`` attribute reading ``True``
        3. Activation disabled.
            - The Hardware is in a 'disabled' states as indicated by the
            ``enbl_sts`` attribute being false.
    '''

    class _IOC_control(Device):
        enbl_sts = Cpt(EpicsSignal, 'Enbl-Sts', string=True,
                       kind='omitted')

        hw_error = Cpt(EpicsSignal, 'HwError-Sts', string=True,
                           kind='omitted')

        sts_error = Cpt(EpicsSignal, 'StsError-Sts', string=True,
                            kind='omitted')

    stdout = subprocess.PIPE
    stdin = None

    ioc_process = subprocess.Popen([sys.executable, '-m',
                                    'caproto.tests.example_runner',
                                    'nslsii.iocs.eps_two_state_ioc_sim'],
                                   stdout=stdout, stdin=stdin,
                                   env=os.environ)

    time.sleep(1)  # allows the ioc to start properly
    print(f'nslsii.ioc.eps_two_state_ioc_sim is now running')

    # Wrap the rest in a try except to ensre that the ioc is killed.
    try:
        shutter = EPSTwoStateDevice(prefix='eps2state:', name='shutter')
        ioc_control = _IOC_control(prefix='eps2state:', name='ioc_control')

        time.sleep(1)

        # two quick tests to ensure the devices and IOC are running.
        assert(hasattr(shutter, 'read'))  # make sure that the device runs
        assert shutter.read()['shutter_status']['value'] in ['Open','Closed']

        # Retry activation error test by closing and opening succesfully
        RE(mv(shutter, 'close'))
        assert shutter.read()['shutter_status']['value'] == 'Closed'
        time.sleep(0.05)
        RE(mv(shutter, 'open'))
        assert shutter.read()['shutter_status']['value'] == 'Open'

        # Hardware failure test, should raise FailedStatus exception.
        RE(mv(ioc_control.hw_error, 'True'))  # enable the hardware error
        with pytest.raises(FailedStatus):
            RE(mv(shutter, 'close'))
        RE(mv(ioc_control.hw_error, 'False'))  # disable the hardware error

        # Activation disabled test, should raise EnableError exception
        RE(mv(ioc_control.enbl_sts, 'False'))
        with pytest.raises(NSLSIIValvesAndShuttersEnableError):
            RE(mv(shutter, 'open'))
        RE(mv(ioc_control.enbl_sts, 'True'))

    finally:
        ioc_process.terminate()
