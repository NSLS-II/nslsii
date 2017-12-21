from ._version import get_versions
__version__ = get_versions()['version']
del get_versions


def configure_base(user_ns, broker_name, *,
                   skip_bec=False, skip_context=False, skip_logging=False,
                   skip_magics=False, skip_mpl=False, skip_pbar=False):
    """
    Perform base setup and instantiation of important objects.

    This factory function instantiates the following and adds them to the
    namespace:

    * ``RE`` -- a RunEngine
    * ``db`` -- a Broker (from "databroker"), subscribe to ``RE``
    * ``bec`` -- a BestEffortCallback, subscribed to ``RE``
    * ``peaks`` -- an alias for ``bec.peaks``
    * ``sd`` -- a SupplementalData preprocessor, added to ``RE.preprocessors``
    * ``pbar_maanger`` -- a ProgressBarManager, set as the ``RE.waiting_hook``

    And it performs some low-level configuration:

    * creates a context in ophyd's control layer (``ophyd.setup_ophyd()``)
    * turns out interactive plotting (``matplotlib.pyplot.ion()``)
    * bridges the RunEngine and Qt event loops
      (``bluesky.utils.install_kicker()``)
    * logs ERROR-level log message from ophyd to the standard out

    Parameters
    ----------
    user_ns: dict
        a namespace --- for example, ``get_ipython().user_ns``
    broker_name : string
        Name of databroker configuration.
    skip_bec : boolean, optional
        False by default. Skips BestEffortCallback.
    skip_context : boolean, optional
        False by default. Skips ``setup_ophyd()``.
    skip_logging : boolean, optional
        False by default. Skips ERROR-level log configuration for ophyd.
    skip_magics : boolean, optional
        False by default. Skips registration of custom IPython magics.
    skip_mpl : boolean, optional
        False by default. Skips matplotlib ``ion()`` at event-loop bridging.
    skip_pbar : boolean, optional
        False by default. Skips ProgressBarManager.

    Returns
    -------
    names : list
        list of names added to the namespace
    
    Examples
    --------
    Configure IPython for CHX.

    >>>> configure_base(get_ipython().user_ns, 'chx');
    """
    ns = {}  # We will update user_ns with this at the end.

    # Set up a RunEngine and use metadata backed by a sqlite file.
    from bluesky import RunEngine
    from bluesky.utils import get_history
    RE = RunEngine(get_history())
    ns['RE'] = RE
    
    # Set up SupplementalData.
    # (This is a no-op until devices are added to it,
    # so there is no need to provide a 'skip_sd' switch.)
    from bluesky import SupplementalData
    sd = SupplementalData()
    RE.preprocessors.append(sd)
    ns['sd'] = sd

    if broker_name:
        # Set up a Broker.
        from databroker import Broker
        db = Broker.named(broker_name)
        ns['db'] = db
        RE.subscribe(db.insert)
    
    if not skip_pbar:
        # Add a progress bar.
        from bluesky.utils import ProgressBarManager
        pbar_manager = ProgressBarManager()
        RE.waiting_hook = pbar_manager
        ns['pbar_manager'] = pbar_manager
    
    if not skip_magics:
        # Register bluesky IPython magics.
        from bluesky.magics import BlueskyMagics
        get_ipython().register_magics(BlueskyMagics)
    
    if not skip_bec:
        # Set up the BestEffortCallback.
        from bluesky.callbacks.best_effort import BestEffortCallback
        bec = BestEffortCallback()
        RE.subscribe(bec)
        ns['bec'] = bec
        ns['peaks'] = bec.peaks  # just as alias for less typing
    
    if not skip_mpl:
        # Import matplotlib and put it in interactive mode.
        import matplotlib.pyplot as plt
        ns['plt'] = plt
        plt.ion()
        
        # Make plots update live while scans run.
        from bluesky.utils import install_kicker
        install_kicker()

    if not skip_context:
        # Create a context in the underlying EPICS client.
        from ophyd import setup_ophyd
        setup_ophyd()
    
    if not skip_logging:
        # Turn on error-level logging, particularly useful for knowing when
        # pyepics callbacks fail.
        import logging
        import ophyd.ophydobj
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        ophyd.ophydobj.logger.addHandler(ch)
    
    # convenience imports
    # some of the * imports are for 'back-compatibility' of a sort -- we have
    # taught BL staff to expect LiveTable and LivePlot etc. to be in their
    # namespace
    def import_star(module):
        public = lambda name: not name.startswith('_')
        ns.update({name: getattr(module, name)
                          for name in dir(module) if public(name)})

    import numpy as np
    ns['np'] = np

    import bluesky.callbacks
    ns['bc'] = bluesky.callbacks
    import_star(bluesky.callbacks)

    import bluesky.plans
    ns['bp'] = bluesky.plans
    import_star(bluesky.plans)

    import bluesky.plan_stubs
    ns['bps'] = bluesky.plan_stubs
    import_star(bluesky.plan_stubs)
    # special-case the commonly-used mv / mvr and its aliases mov / movr4
    ns['mv'] = bluesky.plan_stubs.mv
    ns['mvr'] = bluesky.plan_stubs.mvr
    ns['mov'] = bluesky.plan_stubs.mov
    ns['movr'] = bluesky.plan_stubs.movr

    import bluesky.preprocessors
    ns['bpp'] = bluesky.preprocessors

    import bluesky.callbacks.broker
    import_star(bluesky.callbacks.broker)

    import bluesky.simulators
    import_star(bluesky.simulators)

    import pyOlog.ophyd_tools
    import_star(pyOlog.ophyd_tools)

    user_ns.update(ns)
    return list(ns)


def configure_olog(user_ns, callback=None):
    """
    Setup a callback that publishes some metadata from the RunEngine to Olog.

    The is expected to be run after :func:`configure_base`. It expects to find
    an instance of RunEngine named ``RE`` in the user namespace.

    Parameters
    ----------
    user_ns: dict
        a namespace --- for example, ``get_ipython().user_ns``
    callback : callable, optional
        a hook for customizing the logbook_cb_factory; if None a default is
        used

    Returns
    -------
    names : list
        list of names added to the namespace

    Examples
    --------
    Configure the Olog.

    >>>> configure_olog(get_ipython().user_ns);
    """
    # Conceptually our task is simple: add a subscription to the RunEngine that
    # publishes to the Olog using the Python wrapper of its REST API, pyOlog.
    # In practice this is messy because we have deal with the many-layered API
    # of pyOlog and, more importantly, ensure that slowness or errors from the
    # Olog do not affect the run. Historically the Olog deployment has not been
    # reliable, so it is important to be robust against these issues. Of
    # course, by ignoring Olog errors, we leave gaps in the log, which is not
    # great, but since all data is saved to a databroker anyway, we can always
    # re-generate them later.

    ns = {}  # We will update user_ns with this at the end.

    from bluesky.callbacks.olog import logbook_cb_factory
    from functools import partial
    from pyOlog import SimpleOlogClient
    import queue
    import threading
    from warnings import warn
    
    if callback is None:
        LOGBOOKS = ['Data Acquisition']  # list of logbook names to publish to
        simple_olog_client = SimpleOlogClient()
        generic_logbook_func = simple_olog_client.log
        configured_logbook_func = partial(generic_logbook_func,
                                          logbooks=LOGBOOKS)
        callback = logbook_cb_factory(configured_logbook_func)
    
    def submit_to_olog(queue, cb):
        while True:
            name, doc = queue.get()  # waits until document is available
            try:
                cb(name, doc)
            except Exception as exc:
                warn('This olog is giving errors. This will not be logged.'
                        'Error:' + str(exc))
    
    olog_queue = queue.Queue(maxsize=100)
    olog_thread = threading.Thread(target=submit_to_olog,
                                   args=(olog_queue, callback),
                                   daemon=True)
    olog_thread.start()
    
    def send_to_olog_queue(name, doc):
        try:
            olog_queue.put((name, doc), block=False)
        except queue.Full:
            warn('The olog queue is full. This will not be logged.')
    
    RE = user_ns['RE']
    RE.subscribe(send_to_olog_queue, 'start')
    # This is for pyOlog.ophyd_tools.get_logbook, which simply looks for
    # a variable called 'logbook' in the global IPython namespace.
    ns['logbook'] = simple_olog_client

    user_ns.update(ns)
    return list(ns)
