from nslsii.motor_devices.slits import FourBladeSlits, FrontEndSlits


def test_FourBladeSlits():
    '''smoke test of the FourBladeSlits class
    '''

    slits = FourBladeSlits('test', name='slits')
    assert(hasattr(slits, 'hc'))


def test_FEslits():
    '''smoke test of the FEslits class
    '''

    FEslits = FrontEndSlits('test', name='FEslits')
    assert(hasattr(FEslits, 'hc'))
