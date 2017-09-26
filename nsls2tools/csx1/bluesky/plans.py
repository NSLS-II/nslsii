from collections import deque
import bluesky.plans as bp

@bp.planify
def fccd_aware_trigger_and_read(devices, name='primary'):
    """
    Variant of `bluesky.plans.triger_and_read` customized for CSX

    Normal behavior is to trigger, wait for triggering to finish, and then
    read. For SLOW_DEVICES, defined in the body of this function,
    this plan triggers, reads, and *then* waits for triggering to finish.

    Trigger and read a list of detectors and bundle readings into one Event.

    Parameters
    ----------
    devices : iterable
        devices to trigger (if they have a trigger method) and then read
    name : string, optional
        event stream name, a convenient human-friendly identifier; default
        name is 'primary'

    Yields
    ------
    msg : Msg
        messages to 'trigger', 'wait' and 'read'
    """
    SLOW_DEVICES = ['fccd']
    slow_device_seen = False
    devices = bp.separate_devices(devices)  # remove redundant entries
    normal_grp = bp._short_uid('trigger')
    slow_grp = bp._short_uid('slow-trigger')
    plan_stack = deque()
    for obj in devices:
        if obj.name in SLOW_DEVICES:
            slow_device_seen = True
            grp = slow_grp
        else:
            grp = normal_grp
        if hasattr(obj, 'trigger'):
            plan_stack.append(trigger(obj, group=grp))
    if plan_stack:
        plan_stack.append(bp.wait(group=normal_grp))
    with event_context(plan_stack, name=name):
        for obj in devices:
            plan_stack.append(bp.read(obj))
    if plan_stack and slow_device_seen:
        plan_stack.append(bp.wait(group=slow_grp))
    return plan_stack

#base_tar = bp.trigger_and_read
# If this customization of triggering behavior causes unforeseen
# trouble, just comment out the following line. The definition
# above can stay.
#def paranoid_trigger_and_read(*args, **kwargs):
#    yield from paranoid_checking_and_waiting_plan()
#    return (yield from base_tar(*args, **kwargs))

# THIS IS MONKEY PATCHING PLANS
# bp.trigger_and_read = paranoid_trigger_and_read

#bp.trigger_and_read = fccd_aware_trigger_and_read

# BASELINE
# ['theta',
#  'delta',
#  'gamma',
#  'sx',
#  'say',
#  'saz',
#  'cryoangle',
#  'sy',
#  'sz',
#  'temp',
#  'uw_temp',
#  'pgm_en',
#  'epu1',
#  'epu2',
#  'slt1',
#  'slt2',
#  'slt3',
#  'm1a',
#  'm3a',
#  'mono_tempa',
#  'mono_tempb',
#  'grt1_temp',
#  'grt2_temp',
#  'nanop',

# MONITOR
#  'ring_curr',
#  'diag6_monitor',
#  'sclr',
#  the vortex ROIS

#  'fccd']



#the below will allow you to quit a scan and still access the data.  because count() and not ct() was used, the monitor stream will not be appended automatically

def xpcs_ct(num=1, delay=None, *, md=None):
    """
    NOTE THAT THIS WILL NOT AUTO-APPEND THE MONITOR STREAM

    Take one or more readings from detectors.
    Parameters
    ----------
    num : integer, optional
        number of readings to take; default is 1
        If None, capture data until canceled
    delay : iterable or scalar, optional
        time delay between successive readings; default is 0
    md : dict, optional
        metadata
    Note
    ----
    If ``delay`` is an iterable, it must have at least ``num - 1`` entries or
    the plan will raise a ``ValueError`` during iteration.
    """
    detectors = [fccd]
    _md = {'detectors': [det.name for det in detectors],
           'num_steps': num,
           'plan_args': {'detectors': list(map(repr, detectors)), 'num': num},
           'plan_name': 'xpcs_ct'}
    _md.update(md or {})

    # If delay is a scalar, repeat it forever. If it is an iterable, leave it.
    if not isinstance(delay, Iterable):
        delay = itertools.repeat(delay)
    else:
        try:
            num_delays = len(delay)
        except TypeError:
            # No way to tell in advance if we have enough delays.
            pass
        else:
            if num - 1 > num_delays:
                raise ValueError("num=%r but delays only provides %r "
                                 "entries" % (num, num_delays))
        delay = iter(delay)

    @stage_decorator(detectors)
    @run_decorator(md=_md)
    def finite_plan():
        for i in range(num):
            now = time.time() # Intercept the flow in its earliest moment.
            yield Msg('checkpoint')
            yield from fccd_aware_trigger_and_read(detectors)
            try:
                d = next(delay)
            except StopIteration:
                if i + 1 == num:
                    break
                else:
                    # num specifies a number of iterations less than delay
                    raise ValueError("num=%r but delays only provides %r "
                                     "entries" % (num, i))
            if d is not None:
                d = d - (time.time() - now)
                if d > 0:  # Sleep if and only if time is left to do it.
                    yield Msg('sleep', None, d)

    @stage_decorator(detectors)
    @run_decorator(md=_md)
    def infinite_plan():
        while True:
            yield Msg('checkpoint')
            yield from fccd_aware_trigger_and_read(detectors)
            try:
                d = next(delay)
            except StopIteration:
                break
            if d is not None:
                yield Msg('sleep', None, d)

    if num is None:
        return (yield from infinite_plan())
    else:
        return (yield from finite_plan())
