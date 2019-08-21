import platform
import os
import uuid
import atexit
from ophyd import Device, Component as Cpt, EpicsSignal, EpicsSignalRO


class Baton(Device):
    """
    Ophyd object to wrap the "baton" IOC

    This object has the methods that the RE needs to
    install the baton and check it on every use, and update
    the state while running.

    Examples
    --------

    >>>>  b = Baton(PREFX, name='baton')
    >>>>  ip = get_ipython()
    >>>>  configure_base(ip.user_ns, 'temp', baton=b)

    """

    baton = Cpt(EpicsSignal, "baton", string=True)
    host = Cpt(EpicsSignal, "host", string=True)
    pid = Cpt(EpicsSignal, "pid")
    current_uid = Cpt(EpicsSignal, "current_uid", string=True)
    current_scanid = Cpt(EpicsSignal, "current_scanid")
    state = Cpt(EpicsSignal, "state", string=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._clear_baton = None
        self.tokens = []

    def acquire_baton(self, steal_baton=False):
        existing_baton = self.baton.get()
        if existing_baton and not steal_baton:
            old_host = self.host.get()
            old_pid = self.pid.get()
            raise RuntimeError(
                f"There is already a RE claiming the baton. "
                f"It was running on {old_host}:{old_pid}."
            )

        new_baton = str(uuid.uuid4())
        self.baton.put(new_baton)
        self.host.put(platform.node())
        self.pid.put(os.getpid())

        def check_baton():
            ioc_baton = self.baton.get()
            if ioc_baton != new_baton:
                ioc_host = self.host.get()
                ioc_pid = self.pid.get()
                raise RuntimeError(
                    f"This RE installed {new_baton} but the "
                    f"IOC has {ioc_baton}. "
                    f"The baton was intalled by {ioc_host}:{ioc_pid}"
                )

        self.install_clear_baton()
        return check_baton

    def install_clear_baton(self):
        if self._clear_baton is not None:
            return

        def clear_baton(baton):
            try:
                self.baton.put("")
                self.host.put("")
                self.pid.put(0)
            except Exception:
                # if we fail in tear down 🤷
                pass

        atexit.register(clear_baton, self)
        self._clear_baton = clear_baton

    def doc_callback(self, name, doc):
        if name == "start":
            self.current_uid.put(doc["uid"])
            self.current_scanid.put(doc.get("scan_id", -1))

    def state_callback(self, new, old):
        self.state.put(new)
