import os
import subprocess
import sys
import time

from ophyd.epics_motor import EpicsMotor


def test_epicsmotor_ioc():

    stdout = subprocess.PIPE
    stdin = None

    '''
    ioc_process = subprocess.Popen([sys.executable, '-m',
                                    'caproto.tests.example_runner',
                                    'nslsii.iocs.epics_motor_ioc_sim'],
                                   stdout=stdout, stdin=stdin,
                                   env=os.environ)
    '''
    ioc_process = subprocess.Popen([sys.executable, '-m',
                                    'nslsii.iocs.epics_motor_ioc_sim'],
                                   stdout=stdout, stdin=stdin,
                                   env=os.environ)

    print(f'nslsii.iocs.epc_two_state_ioc_sim is now running')

    time.sleep(5)

    # Wrap the rest in a try-except to ensure the ioc is killed before exiting
    try:

        mtr = EpicsMotor(prefix='mtr:', name='mtr')

        time.sleep(5)

        # 1. check the ioc-device connection and initial values

        assert mtr.egu == 'mm'

        assert mtr.low_limit == -110.0
        assert mtr.high_limit == 110.0

        # 2. set_current_position

        mtr.set_current_position(50)
        setpoint_val = mtr.user_setpoint.get()
        readback_val = mtr.user_readback.get()
        assert setpoint_val == 50
        assert readback_val == 50

        # 3. move

        mtr.move(80, timeout=2)
        setpoint_val = mtr.user_setpoint.get()
        readback_val = mtr.user_readback.get()
        assert setpoint_val == 80
        assert readback_val == 80

    finally:
        # Ensure that for any exception the ioc sub-process is terminated
        # before raising.
        # pass
        ioc_process.terminate()
