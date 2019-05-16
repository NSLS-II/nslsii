import os
import pytest
import subprocess
import sys
import time

from ophyd import Device, EpicsMotor
from ophyd import Component as Cpt
from ophyd.device import create_device_from_components

from caproto.sync.client import read


def slit(name, axes=None, *, docstring=None, default_read_attrs=None,
         default_configuration_attrs=None):

    components = {}
    for name, PV_suffix in axes.items():
        components[name] = Cpt(EpicsMotor, PV_suffix, name=name)

    new_class = create_device_from_components(
        name, docstring=docstring, default_read_attrs=default_read_attrs,
        default_configuration_attrs=default_configuration_attrs,
        base_class=Device, **components)

    return new_class


@pytest.fixture(scope='class')
def ioc_sim(request):

    # setup code

    stdout = subprocess.PIPE
    stdin = None

    ioc_process = subprocess.Popen([sys.executable, '-m',
                                   'nslsii.iocs.motor_group_ioc_sim'],
                                   stdout=stdout, stdin=stdin,
                                   env=os.environ)

    print(f'nslsii.iocs.motor_group_ioc_sim is now running')

    time.sleep(5)

    FourBladeSlits = slit(name='FourBladeSlits',
                          axes={'hg': '-Ax:HGMtr', 'hc': '-Ax:HCMtr',
                                'vg': '-Ax:VGMtr', 'vc': '-Ax:VCMtr',
                                'inb': '-Ax:IMtr', 'out': '-Ax:OMtr',
                                'top': '-Ax:TMtr', 'bot': '-Ax:BMtr'},
                          docstring='Four Blades Slits')

    slits = FourBladeSlits('test', name='slits')

    time.sleep(5)

    request.cls.slits = slits

    yield

    # teardown code

    ioc_process.terminate()


@pytest.mark.usefixtures('ioc_sim')
class TestIOC:

    def test_caproto_level(self):

        res = read('test-Ax:HCMtr.VELO')
        velocity_val = res.data[0]
        assert velocity_val == 1.0

    def test_device_level(self):

        assert(hasattr(self.slits, 'hc'))

        velocity_val = self.slits.hc.velocity.get()
        assert velocity_val == 1
