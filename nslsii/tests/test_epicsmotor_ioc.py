import os
import pytest
import subprocess
import sys
import time

from ophyd.epics_motor import EpicsMotor


@pytest.fixture(scope='class')
def ioc_sim(request):

    # setup code

    stdout = subprocess.PIPE
    stdin = None

    ioc_process = subprocess.Popen([sys.executable, '-m',
                                    'nslsii.iocs.epics_motor_ioc_sim'],
                                   stdout=stdout, stdin=stdin,
                                   env=os.environ)

    print(f'nslsii.iocs.epics_motor_ioc_sim is now running')

    time.sleep(5)

    mtr = EpicsMotor(prefix='mtr:', name='mtr')

    time.sleep(5)

    request.cls.mtr = mtr

    yield

    # teardown code

    ioc_process.terminate()


@pytest.mark.usefixtures('ioc_sim')
class TestIOC:

    def test_initial_values(self):

        assert self.mtr.egu == 'mm'

        velocity_val = self.mtr.velocity.get()
        assert velocity_val == 1

        assert self.mtr.low_limit == -11.0
        assert self.mtr.high_limit == 11.0

    def test_set_current_position(self):

        target_val = 5
        readback_val = self.mtr.user_readback.get()
        velocity_val = self.mtr.velocity.get()
        mvtime = (target_val - readback_val)/velocity_val

        self.mtr.set_current_position(target_val)

        time.sleep(mvtime)

        setpoint_val = self.mtr.user_setpoint.get()
        readback_val = self.mtr.user_readback.get()
        assert round(setpoint_val, 3) == target_val
        assert round(readback_val, 3) == target_val

    def test_move_with_timeout_gt_moving_time(self):

        target_val = 7
        readback_val = self.mtr.user_readback.get()
        velocity_val = self.mtr.velocity.get()
        mvtime = (target_val - readback_val)/velocity_val

        move_status = self.mtr.move(target_val, timeout=mvtime+1)
        assert move_status.success is True

    def test_move_with_timeout_lt_moving_time(self):

        target_val = 9
        readback_val = self.mtr.user_readback.get()
        velocity_val = self.mtr.velocity.get()
        mvtime = (target_val - readback_val)/velocity_val

        with pytest.raises(RuntimeError):
            self.mtr.move(target_val, timeout=mvtime-1)
