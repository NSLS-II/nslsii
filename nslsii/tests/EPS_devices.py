
from nslsii.EPS_devices.valves_and_shutters import EPSTwoStateDevice


def test_EPSTwoStateDevice():
    '''A smoke test of the EPSTwoStateDevice class
    '''

    shutter = EPSTwoStateDevice(prefix='test', name='shutter')
    assert(hasattr(shutter, 'read'))
