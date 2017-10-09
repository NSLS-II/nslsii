import numpy as np
from cycler import cycler
import bluesky.plans as bp

def EfixQapprox(detectors, E_start, E_end, npts, E_shift = 0, *, per_step=None, md=None):
    '''Approximated fixed Q energy scan based on delta, theta positions for CSX-1 mono (pgm.energy)

    Parameters
    ----------
    E_start : float
        starting energy [eV]
    E_stop : float
        stoping energy [eV]
    npts : integer
        number of points
    E_shift : float
        shift in energy calibration relative to orientation matrix (i.e, ) - not used currently
    per_step : callable, optional
        hook for cutomizing action of inner loop (messages per step)
        See docstring of bluesky.plans.one_nd_step (the default) for
        details.
    md : dict, optional
        metadata

    '''
    x_motor = pgm.energy # This is CSX-1's mono motor name for energy
    x_start = E_start
    pattern_args = dict(x_motor=x_motor,x_start = E_start, npts = npts)

    deltas = []
    thetas = []
    deltaCALC = 0
    thetaCALC = 0

    E_init = x_motor.readback.value
    lam_init =  12398/E_init
    delta_init = delta.user_readback.value
    theta_init = theta.user_readback.value
    dsp = lam_init/(2*sin(radians(delta_init/2)))
    theta_offset = delta_init/2 - theta_init


    E_vals = np.linspace(E_start, E_end, npts)  #
    lam_vals = np.linspace(12398/E_start,12398/E_end,npts)
    x_range = max(E_vals) - min(E_vals)

    for lam_val in lam_vals:
        deltaCALC = degrees(arcsin(lam_val/2/dsp))*2
        thetaCALC = deltaCALC/2 - theta_offset
        deltas.append(deltaCALC)
        thetas.append(thetaCALC)

    motor_pos = cycler(delta, deltas) + cycler(theta, thetas) + cycler(x_motor, E_vals)

    # TODO decide to include diffractometer motors below?
    # Before including pattern_args in metadata, replace objects with reprs.
    pattern_args['x_motor'] = repr(x_motor)
    _md = {'plan_args': {'detectors': list(map(repr, detectors)),
                         'x_motor': repr(x_motor), 'x_start': x_start,
                         'x_range': x_range,
                         'per_step': repr(per_step)},
           'extents': tuple([[x_start - x_range, x_start + x_range]]),
           'plan_name': 'EfixQapprox',
           'plan_pattern': 'scan',
           'plan_pattern_args': pattern_args,
           'plan_pattern_module': plan_patterns.__name__,
           'hints': {},
          }
    try:
        dimensions = [(x_motor.hints['fields'], 'primary')] #
        #print(dimensions)
    except (AttributeError, KeyError):
        pass
    else:
        _md['hints'].update({'dimensions': dimensions})
    _md.update(md or {})

    Escan_plan = scan_nd(detectors, motor_pos, per_step=per_step, md=_md)#this works without subs,

    reset_plan =  bp.mv(x_motor, E_init, delta, delta_init, theta, theta_init)

    # Check for suitable syntax..
    # yield from print('Starting an Escan fix Q at ({:.4f}, {:.4f}, {:.4f})'.format(h_init,k_init,l_init))

    def plan_steps():
        yield from Escan_plan
        print('/nMoving back to motor positions immediately before scan/n')
        yield from reset_plan

    try:
        return (yield from plan_steps())

    except Exception:
        print('/nMoving back to motor positions immediately before scan/n')
        yield from reset_plan
        raise


def EfixQ(detectors, E_start, E_end, steps, E_shift = 0, *, per_step=None, md=None):
    '''Fixed Q energy scan based on an orientation matrix for CSX-1 mono (pgm.energy)

    If using higher order harmonic of mono, adjust H K L, not energy.

    Parameters


    ----------
    E_start : float
        starting energy [eV]
    E_stop : float
        stoping energy [eV]
    steps : integer
        number of points
    E_shift : float
        shift in energy calibration relative to orientation matrix (i.e, )
    per_step : callable, optional
        hook for cutomizing action of inner loop (messages per step)
        See docstring of bluesky.plans.one_nd_step (the default) for
        details.
    md : dict, optional
        metadata

    '''
    x_motor = pgm.energy # This is CSX-1's mono motor name for energy
    x_start = E_start
    pattern_args = dict(x_motor=x_motor,x_start = E_start,steps = steps,E_shift = E_shift)

    E_init = x_motor.readback.value
    tardis.calc.energy = (x_motor.setpoint.value + E_shift)/10000
    h_init = tardis.position.h
    k_init = tardis.position.k
    l_init = tardis.position.l
    delta_init = delta.user_readback.value
    theta_init = theta.user_readback.value
    gamma_init = gamma.user_readback.value

    deltas = []
    thetas = []
    gammas = []

    E_vals = np.linspace(E_start, E_end, steps+1)  #TODO no plus one, use npts as arugument.
    x_range = max(E_vals) - min(E_vals)

    for E_val in E_vals:
        tardis.calc.energy = (E_val + E_shift)/10000
        angles = tardis.forward([h_init, k_init, l_init])
        deltas.append(angles.delta)
        thetas.append(angles.theta)
        gammas.append(angles.gamma)

    motor_pos = cycler(delta, deltas) + cycler(theta, thetas) + cycler(gamma, gammas) + cycler(x_motor, E_vals)

    # TODO decide to include diffractometer motors below?
    # Before including pattern_args in metadata, replace objects with reprs.
    pattern_args['x_motor'] = repr(x_motor)
    _md = {'plan_args': {'detectors': list(map(repr, detectors)),
                         'x_motor': repr(x_motor), 'x_start': x_start,
                         'x_range': x_range,
                         'per_step': repr(per_step)},
           'extents': tuple([[x_start - x_range, x_start + x_range]]),
           'plan_name': 'EfixQapprox',
           'plan_pattern': 'scan',
           'plan_pattern_args': pattern_args,
           'plan_pattern_module': plan_patterns.__name__,
           'hints': {},
          }
    try:
        dimensions = [(x_motor.hints['fields'], 'primary')] #
        #print(dimensions)
    except (AttributeError, KeyError):
        pass
    else:
        _md['hints'].update({'dimensions': dimensions})
    _md.update(md or {})


    Escan_plan = scan_nd(detectors, motor_pos, per_step=per_step, md=_md)#this works without subs,

    reset_plan =  bp.mv(x_motor, E_init, delta, delta_init, theta, theta_init, gamma, gamma_init)

    # yield from print('Starting an Escan fix Q at ({:.4f}, {:.4f}, {:.4f})'.format(h_init,k_init,l_init))

    def plan_steps():
        print('Starting fixed Q energy scan for ({:.4f}, {:.4f}, {:.4f}\n\n)'.format(tardis.h.position,
               tardis.k.position,tardis.l.position))
        yield from Escan_plan
        print('\nMoving back to motor positions immediately before scan\n')
        yield from reset_plan
        yield from bp.sleep(1)
        tardis.calc.energy = (pgm.energy.readback.value + E_shift)/10000
        print('Returned to Q at ({:.4f}, {:.4f}, {:.4f})'.format(tardis.h.position,
               tardis.k.position,tardis.l.position))


    try:
        return (yield from plan_steps())

    except Exception:
        print('\nMoving back to motor positions immediately before scan\n')
        yield from reset_plan
        yield from bp.sleep(1)
        tardis.calc.energy = (pgm.energy.readback.value + E_shift)/10000
        print('Returned to Q at ({:.4f}, {:.4f}, {:.4f})'.format(tardis.h.position,
               tardis.k.position,tardis.l.position))
        raise




