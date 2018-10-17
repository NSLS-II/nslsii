from nslsii.temperature_controllers import Eurotherm
from bluesky.plan_stubs import mv
from bluesky import RunEngine
import subprocess
import os
import sys
import pytest


@pytest.fixture
def RE():
    return RunEngine()


def test_Eurotherm(RE):
    '''Tests the Eurotherm ophyd device.

    Parameters
    ----------
    RE : object
        Bluesky RunEngine for use in testing.
    '''

    stdout = subprocess.PIPE
    stdin = None

    # Start up an IOC based on the thermo_sim device in caproto.ioc_examples
    ioc_process = subprocess.Popen([sys.executable, '-m',
                                    'caproto.tests.example_runner',
                                    'caproto.ioc_examples.thermo_sim'] +
                                   list([]), stdout=stdout, stdin=stdin,
                                   env=os.environ)

    print(f'caproto.ioc_examples.thermo_sim is now running')

    # Wrap the rest in a try-except to ensure the ioc is killed before exiting
    try:
        euro = Eurotherm('thermo:', name='euro')
        print(f'euro object is defined')

        # move the Eurotherm.
        RE(mv(euro, 100))

        # check that the readback value is within euro.tolerance of 100
        assert abs(euro.readback.get() - 100) <= euro.tolerance.get()

    finally:
        # Ensure that for any exception the ioc sub-process is terminated
        # before raising.
        ioc_process.terminate()
