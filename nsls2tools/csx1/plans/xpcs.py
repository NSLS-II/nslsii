from collections import deque
import bluesky.plans as bp

# The below will allow you to quit a scan and still access the data.
# Because count() and not ct() was used, the monitor stream will not be appended automatically

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
