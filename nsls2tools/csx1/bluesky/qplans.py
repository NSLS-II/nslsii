
def EfixQapprox(detectors, E_start, E_end, steps, E_shift = 0, *, per_step=None, md=None):
    '''Fixed Q energy scan based on an orientation matrix

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
    pattern_args = dict(x_motor=x_motor,x_start = E_start,steps = steps)

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


    E_vals = np.linspace(E_start, E_end, steps)
    lam_vals = np.linspace(12398/E_start,12398/E_end,steps)
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
        dimensions = [(x_motor.hints['fields'], 'primary')]
    except (AttributeError, KeyError):
        pass
    else:
        _md['hints'].update({'dimensions': dimensions})
    _md.update(md or {})


    #fig = plt.figure('Escan_approx_fixQ')
    #ax = fig.gca()

    #Escan_plan =
    Escan_plan = PlanND(detectors, motor_pos)
    #Escan_plan.detectors = detectors
    reset_plan =  bp.mv(x_motor, E_init, delta, delta_init, theta, theta_init)

    # Check for suitable syntax..
    # yield from print('Starting an Escan fix Q at ({:.4f}, {:.4f}, {:.4f})'.format(h_init,k_init,l_init))

    def plan_steps():
        yield from Escan_plan
        print('Moving back to energy immediately before scan')
        yield from reset_plan

    try:
        return (yield from plan_steps())

    except Exception:
        print('Moving back to energy immediately before scan')
        yield from reset_plan
        raise
