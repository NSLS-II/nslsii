from ophyd import (Device, Component, EpicsMotor, PVPositioner, EpicsSignal,
                   EpicsSignalRO)


class BaffleSlit(Device):
    '''An ``ophyd.Device`` class to be used as a base for'slits' at NSLS-II

    This is the base class that should be a parent for the remaining slit
    classes at NSLS-II. Slits are defined as anything that has at least one
    settable 'opening' or 'aperture'. The default is a baffle slit with a
    horizontal gap and centre (hg and hc) and a vertical gap and centre (vg and
    vc). Other configurations can be created using the ``blades`` dict on
    initialization. For instance to define a horizontal only slit use the
    kwarg:
      ``slit=BaffleSlit(PV_prefix, name='slit',
                        components = {'hg': '-Ax:HG}Mtr', 'hc':'-Ax:HC}Mtr'})``

    Parameters
    ----------
    components, dict
        Maps the name for a motor attribute to the PVsuffix for the EpicsMotor
        group. The default, which defines a basic slit with horizontal(h) and
        vertical(v) gaps(g) and centres(c), is:
        {'hg': '-Ax:HG}Mtr', 'hc': '-Ax:HC}Mtr',
         'vg': '-Ax:VG}Mtr', 'vc': '-Ax:VC}Mtr'}
    *args
        The arguments that will be passed down to the ``Device`` ``__init__``
        call.
    **kwargs
        The keyword arguments that will be passed down to the ``Device``
        ``__init__`` call.
    '''

    def __init__(self, *args,
                 components={'hg': '-Ax:HG}Mtr', 'hc': '-Ax:HC}Mtr',
                             'vg': '-Ax:VG}Mtr', 'vc': '-Ax:VC}Mtr'},
                 **kwargs):
        super().__init__(*args, **kwargs)
        for name, PV_suffix in components.items():
            setattr(self, name, Component(EpicsMotor, PV_suffix, name=name))


class FourBladeBaffleSlit(BaffleSlit):
    '''An ``ophyd.Device`` class to be used for 4 blade baffle slits at NSLS-II

    This is a child of ``nslsii.motor_devices.BaffleSlit`` and adds the
    default components for a 4 blade baffle slit. In particular, in addition to
    the default components for horizontal and vertical gap and centres from
    ``nslsii.motor_devices.BaffleSlit`` it adds default components for the
    inboard (inb), outboard (out), top (top) and bottom (bot) blades.

    Parameters
    ----------
    components, dict
        Maps the name for a motor attribute to the PVsuffix for the EpicsMotor
        group. The default, which defines a basic slit with horizontal(h) and
        vertical(v) gaps(g) and centres(c), is:
        {'hg': '-Ax:HG}Mtr', 'hc': '-Ax:HC}Mtr',
         'vg': '-Ax:VG}Mtr', 'vc': '-Ax:VC}Mtr',
         'inb': '-Ax:I}Mtr', 'out': '-Ax:O}Mtr',
         'top': '-Ax:T}Mtr', 'bot': '-Ax:B}Mtr'}
    *args
        The arguments that will be passed down to the ``Device`` ``__init__``
        call.
    **kwargs
        The keyword arguments that will be passed down to the ``Device``
        ``__init__`` call.
    '''
    def __init__(self, *args,
                 components={'hg': '-Ax:HG}Mtr', 'hc': '-Ax:HC}Mtr',
                             'vg': '-Ax:VG}Mtr', 'vc': '-Ax:VC}Mtr',
                             'inb': '-Ax:I}Mtr', 'out': '-Ax:O}Mtr',
                             'top': '-Ax:T}Mtr', 'bot': '-Ax:B}Mtr'},
                 **kwargs):
        super().__init__(*args, components=components, **kwargs)


class ScanAndApertureBaffleSlit(BaffleSlit):
    '''An ``ophyd.Device`` class used for scan/aperture baffle slits at NSLS-II

    This is a child of ``nslsii.motor_devices.BaffleSlit`` and adds the
    default components for a baffle slit with 'scan' and 'aperture' motors. In
    particular, in addition to the default components for horizontal and
    vertical gap and centres from ``nslsii.motor_devices.BaffleSlit`` it adds
    default components for the horizontal scan (hs), horizontal aperture (ha),
    vertical scan (vs) and vertical aperture (va) motors.

    Parameters
    ----------
    components, dict
        Maps the name for a motor attribute to the PVsuffix for the EpicsMotor
        group. The default, which defines a basic slit with horizontal(h) and
        vertical(v) gaps(g) and centres(c), is:
        {'hg': '-Ax:HG}Mtr', 'hc': '-Ax:HC}Mtr',
         'vg': '-Ax:VG}Mtr', 'vc': '-Ax:VC}Mtr',
         'hs': '-Ax:HS}Mtr', 'ha': '-Ax:HA}Mtr',
         'vs': '-Ax:VS}Mtr', 'va': '-Ax:VA}Mtr'}
    *args
        The arguments that will be passed down to the ``Device`` ``__init__``
        call.
    **kwargs
        The keyword arguments that will be passed down to the ``Device``
        ``__init__`` call.
    '''
    def __init__(self, *args,
                 components={'hg': '-Ax:HG}Mtr', 'hc': '-Ax:HC}Mtr',
                             'vg': '-Ax:VG}Mtr', 'vc': '-Ax:VC}Mtr',
                             'hs': '-Ax:HS}Mtr', 'ha': '-Ax:HA}Mtr',
                             'vs': '-Ax:VS}Mtr', 'va': '-Ax:VA}Mtr'},
                 **kwargs):
        super().__init__(*args, components=components, **kwargs)


class FrontEndSlits(Device):
    '''An ``ophyd.Device`` class used for the front end slits at NSLS-II

    This is a child of ``ophyd.Device`` and adds the default in order to
    move the front-end slits, this differs from the
    ``nslsii.motor_devices.slits`` as the comonents are not EpicsMotor records.

    Parameters
    ----------
    *args
        The arguments that will be passed down to the ``Device`` ``__init__``
        call.
    **kwargs
        The keyword arguments that will be passed down to the ``Device``
        ``__init__`` call.
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class _VirtualGap(PVPositioner):
        readback = Component(EpicsSignalRO, 't2.C')
        setpoint = Component(EpicsSignal, 'size')
        done = Component(EpicsSignalRO, 'DMOV')
        done_value = 1

    class _VirtualCenter(PVPositioner):
        readback = Component(EpicsSignalRO, 't2.D')
        setpoint = Component(EpicsSignal, 'center')
        done = Component(EpicsSignalRO, 'DMOV')
        done_value = 1

    hc = Component(_VirtualCenter, '-Ax:X}')
    vc = Component(_VirtualCenter, '-Ax:Y}')
    hg = Component(_VirtualGap, '-Ax:X}')
    vg = Component(_VirtualGap, '-Ax:Y}')
