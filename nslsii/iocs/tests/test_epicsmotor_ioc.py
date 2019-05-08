import os
import subprocess
import sys
import time

from ophyd.epics_motor import EpicsMotor
from ophyd.status import MoveStatus


def test_epicsmotor_ioc():

    stdout = subprocess.PIPE
    stdin = None

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
    '''

    print(f'nslsii.iocs.epc_two_state_ioc_sim is now running')

    time.sleep(5)

    # Wrap the rest in a try-except to ensure the ioc is killed before exiting
    try:

        mtr = EpicsMotor(prefix='mtr:', name='mtr')

        time.sleep(5)

        # 1. check the ioc-device connection and initial values

        assert mtr.egu == 'mm'

        velocity_val = mtr.velocity.get()
        assert velocity_val == 1

        assert mtr.low_limit == -11.0
        assert mtr.high_limit == 11.0

        # 2. set_current_position

        target_val = 5

        readback_val = mtr.user_readback.get()
        mvtime = (target_val - readback_val)/velocity_val

        mtr.set_current_position(target_val)

        time.sleep(mvtime)

        setpoint_val = mtr.user_setpoint.get()
        readback_val = mtr.user_readback.get()
        assert round(setpoint_val, 3) == target_val
        assert round(readback_val, 3) == target_val

        # 3. move (timeout > moving time)

        target_val = 7
        mvtime = (target_val - readback_val)/velocity_val

        move_status = MoveStatus(mtr, target_val)

        try:
            move_status = mtr.move(target_val, timeout=mvtime+1)
        except RuntimeError:
            pass

        assert move_status.success is True

        time.sleep(mvtime)

        setpoint_val = mtr.user_setpoint.get()
        readback_val = mtr.user_readback.get()
        assert round(setpoint_val, 3) == target_val
        assert round(readback_val, 3) == target_val

        # 4. move (timeout < moving time)

        target_val = 9
        mvtime = (target_val - readback_val)/velocity_val

        move_status = MoveStatus(mtr, target_val)

        try:
            move_status = mtr.move(target_val, timeout=mvtime-1)
        except RuntimeError:
            pass

        assert move_status.success is False

    finally:
        # Ensure that for any exception the ioc sub-process is terminated
        # before raising.
        ioc_process.terminate()
