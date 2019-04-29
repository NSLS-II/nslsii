# import subprocess
# import os
# import sys

from ophyd import Device, EpicsSignal, EpicsSignalRO
from ophyd.device import (Component as Cpt,
                          FormattedComponent as FmtCpt)


class EPSTwoStateDevice(Device):

    def __init__(self, *, prefix, name, **kwargs):
        super().__init__(prefix=prefix, name=name, **kwargs)

    status = Cpt(EpicsSignalRO, 'Pos-Sts', string=True)

    opn_cmd = FmtCpt(EpicsSignal,
                     '{self.prefix}Cmd:Opn-Cmd',
                     string=True, kind='omitted')
    cls_cmd = FmtCpt(EpicsSignal,
                     '{self.prefix}Cmd:Cls-Cmd',
                     string=True, kind='omitted')


def test_epstwostate_ioc():

    '''
    stdout = subprocess.PIPE
    stdin = None

    ioc_process = subprocess.Popen([sys.executable, '-m',
                                    'caproto.tests.example_runner',
                                    'nslsii.iocs.eps_two_state_ioc_sim'],
                                   stdout=stdout, stdin=stdin,
                                   env=os.environ)

    print(f'nslsii.iocs.epc_two_state_ioc_sim is now running')
    '''

    # Wrap the rest in a try-except to ensure the ioc is killed before exiting
    try:

        eps = EPSTwoStateDevice(prefix='eps2state:', name='eps')

        # 1. check the ioc-device connection and initial values
        sts_val = eps.status.get()
        assert sts_val == 'Open'

        opn_cmd_val = eps.opn_cmd.get()
        assert opn_cmd_val == 'None'

        cls_cmd_val = eps.cls_cmd.get()
        assert cls_cmd_val == 'None'

        # 2. try to close with one attempt

        eps.cls_cmd.put(1)

        cls_cmd_val = eps.cls_cmd.get()
        assert cls_cmd_val == 'None'

        sts_val = eps.status.get()
        assert sts_val == 'Open'

        # 3. try to close with second attempt

        eps.cls_cmd.put(1)

        cls_cmd_val = eps.cls_cmd.get()
        assert cls_cmd_val == 'None'

        sts_val = eps.status.get()
        assert sts_val == 'Closed'

        # 4. try to open with one attempt

        eps.opn_cmd.put(1)

        opn_cmd_val = eps.opn_cmd.get()
        assert opn_cmd_val == 'None'

        sts_val = eps.status.get()
        assert sts_val == 'Closed'

        # 5. try to open with second attempt

        eps.opn_cmd.put(1)

        opn_cmd_val = eps.opn_cmd.get()
        assert opn_cmd_val == 'None'

        sts_val = eps.status.get()
        assert sts_val == 'Open'

    finally:
        # Ensure that for any exception the ioc sub-process is terminated
        # before raising.
        # ioc_process.terminate()
        pass
