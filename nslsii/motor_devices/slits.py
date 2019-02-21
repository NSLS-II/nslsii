from ophyd import (Device, Component, EpicsMotor, PVPositioner, EpicsSignal,
                   EpicsSignalRO)
from ophyd.device import create_device_from_components


def slit(name='', axes={'hg': '-Ax:HG}Mtr', 'hc': '-Ax:HC}Mtr',
                        'vg': '-Ax:VG}Mtr', 'vc': '-Ax:VC}Mtr'}, *,
         docstring=None, default_read_attrs=None,
         default_configuration_attrs=None):
    '''Returns an ``ophyd.Device`` class for 'slits' at NSLS-II

    This function generates ``ophyd.Device`` classes that should used to make
    slit classes at NSLS-II. Slits are defined as anything that has at least
    one settable 'opening' or 'aperture'. The default is a baffle slit with a
    horizontal gap and centre (hg and hc) and a vertical gap and centre (vg and
    vc). Other configurations can be created using the ``blades`` dict on
    initialization. For instance to define a horizontal only slit use the
    kwarg:

    ..code ::

        HorizSlit=BaffleSlit(name='Horiz_Slit',
                             axes={'hg': '-Ax:HG}Mtr', 'hc':'-Ax:HC}Mtr'})
        my_slit=HorizSlit(PV_prefix, name='my_slit')

    Parameters
    ----------
    name: str
        The name of the new ``ophyd.Device`` class.
    components : dict
        Maps the name for a motor attribute to the PVsuffix for the EpicsMotor
        group. The default, which defines a basic slit with horizontal(h) and
        vertical(v) gaps(g) and centres(c), is:
        {'hg': '-Ax:HG}Mtr', 'hc': '-Ax:HC}Mtr',
         'vg': '-Ax:VG}Mtr', 'vc': '-Ax:VC}Mtr'}
    docstring : str, optional
        Docstring to attach to the class
    default_read_attrs : list, optional
        Outside of Kind, control the default read_attrs list. Defaults to all
        'component_names'.
    default_configuration_attrs : list, optional
        Outside of Kind, control the default configuration_attrs list.
        Defaults to []
    '''

    components = {}
    for name, PV_suffix in axes.items():
        components[name] = Component(EpicsMotor, PV_suffix, name=name)

    new_class = create_device_from_components(
        name, docstring=docstring, default_read_attrs=default_read_attrs,
        default_configuration_attrs=default_configuration_attrs,
        base_class=Device, **components)

    return new_class


# Below we define a few common examples of classes

# FourBladeSlit class
_fourblade_docstring = (
    '''An ``ophyd.Device`` class to be used for 4 blade baffle slits at NSLS-II

    This is generated using ``nslsii.motor_devices.slit`` and adds the default
    components for a 4 blade slit. In particular, in addition to the components
    for horizontal and vertical gap and centres it adds components for the
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
        The arguments that will be passed down to the ``ophyd.Device``
        ``__init__`` call.
    **kwargs
        The keyword arguments that will be passed down to the ``ophyd.Device``
        ``__init__`` call.
    ''')

FourBladeSlit = slit(name='FourBladeSlit',
                     axes={'hg': '-Ax:HG}Mtr', 'hc': '-Ax:HC}Mtr',
                           'vg': '-Ax:VG}Mtr', 'vc': '-Ax:VC}Mtr',
                           'inb': '-Ax:I}Mtr', 'out': '-Ax:O}Mtr',
                           'top': '-Ax:T}Mtr', 'bot': '-Ax:B}Mtr'},
                     docstring=_fourblade_docstring)

# ScanAndApertureSlit class
_scanaperture_docstring = (
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
    ''')
ScanAndApertureSlit = slit(name='ScanAndApertureSlit',
                           axes={'hg': '-Ax:HG}Mtr', 'hc': '-Ax:HC}Mtr',
                                 'vg': '-Ax:VG}Mtr', 'vc': '-Ax:VC}Mtr',
                                 'hs': '-Ax:HS}Mtr', 'ha': '-Ax:HA}Mtr',
                                 'vs': '-Ax:VS}Mtr', 'va': '-Ax:VA}Mtr'},
                           docstring=_scanaperture_docstring)


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
