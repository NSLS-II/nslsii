import numpy as np
from cycler import cycler
import bluesky.plans as bp

### additional generic scans for nanopositioners.
### ZP suffix in plan name is indicative of 4 motor parameters until the epics pseudo motor is made, then the generic non-ZP scan should be used.

def spiral_continuous(detectors, x_motor, y_motor, x_start, y_start, npts, probe_size, overlap=0.8 , *, tilt=0.0, per_step=None, md=None):
    '''Continuously increasing radius spiral scan, centered around (x_start, y_start)
    which is generic regarding motors and detectors.

    Parameters
    ----------
    x_motor : object
        any 'setable' object (motor, etc.)
    y_motor : object
        any 'setable' object (motor, etc.)
    x_start : float
        x center
    y_start : float
        y center
    npts : integer
        number of points
    probe_size : float
        radius of probe in units of motors
    overlap : float
        fraction of probe overlap
    ----------------------------------------------------------------
    Not implemented yet:
    tilt : float, optional (not yet enabled)
        Tilt angle in radians, default = 0.0
    per_step : callable, optional
        hook for cutomizing action of inner loop (messages per step)
        See docstring of bluesky.plans.one_nd_step (the default) for
        details.
    ----------------------------------------------------------------
    md : dict, optional
        metadata

    '''


    ##TODO clean up pattern args and _md.  Do not remove motors from _md.
    pattern_args = dict(x_motor=x_motor, y_motor=y_motor, x_start=x_start, y_start=y_start,
                        npts = npts, probe_size=probe_size, overlap=overlap, tilt=tilt)
    #cyc = plan_patterns.spiral(**pattern_args)# - leftover from spiral.

    bxs = []
    bzs = []

    bx_init = x_start
    bz_init = y_start

    for i in range(0,npts):
        R = np.sqrt(i/np.pi)
        T = 2*i/(R+0.0000001) #this is to get the first point to be the center
        bx = (overlap*probe_size*R * np.cos(T))  + bx_init
        bz = (overlap*probe_size*R * np.sin(T))  + bz_init
        bxs.append(bx)
        bzs.append(bz)

    motor_vals = [bxs, bzs]
    x_range = max(motor_vals[0]) - min(motor_vals[0])
    y_range = max(motor_vals[1]) - min(motor_vals[1])
    motor_pos = cycler(x_motor, bxs) + cycler(y_motor, bzs)


    # Before including pattern_args in metadata, replace objects with reprs.
    pattern_args['x_motor'] = repr(x_motor)
    pattern_args['y_motor'] = repr(y_motor)
    _md = {'plan_args': {'detectors': list(map(repr, detectors)),
                         'x_motor': repr(x_motor), 'y_motor': repr(y_motor),
                         'x_start': x_start, 'y_start': y_start,
                         'overlap': overlap, #'nth': nth,
                         'tilt': tilt,
                         'per_step': repr(per_step)},
           'extents': tuple([[x_start - x_range, x_start + x_range],
                             [y_start - y_range, y_start + y_range]]),
           'plan_name': 'spiral_continuous',
           'plan_pattern': 'spiral_continuous',
           'plan_pattern_args': pattern_args,
           #'plan_pattern_module': plan_patterns.__name__,  # - leftover from spiral.
           'hints': {},
          }
    try:
        dimensions = [(x_motor.hints['fields'], 'primary'),
                      (y_motor.hints['fields'], 'primary')]
    except (AttributeError, KeyError):
        pass
    else:
        _md['hints'].update({'dimensions': dimensions})
    _md.update(md or {})

    cont_sp_plan = bp.scan_nd(detectors, motor_pos, per_step=per_step, md=_md)

    reset_plan = bp.mv(x_motor, x_start, y_motor, y_start)


    def plan_steps():
        yield from cont_sp_plan
        print('Moving back to first point position.')
        yield from reset_plan

    try:
        return (yield from plan_steps())

    except Exception:
       # Catch the exception long enough to clean up.
        print('Moving back to first point position.')
        yield from reset_plan
        raise



