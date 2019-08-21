import platform
import os
import uuid
import atexit
from ophyd import Device, Component as Cpt, EpicsSignal


class Baton(Device):
    """
    Ophyd object to wrap the "baton" IOC

    Examples
    --------

    >>>>  b = Baton(PREFX, name='baton')
    >>>>  ip = get_ipython()
    >>>>  configure_base(ip.user_ns, 'chx', acquire_baton=b.acquire_baton)

    """

    baton = Cpt(EpicsSignal, "baton", string=True)
    host = Cpt(EpicsSignal, "host", string=True)
    pid = Cpt(EpicsSignal, "pid")
    last_uid = Cpt(EpicsSignal, "last_uid", string=True)
    current_uid = Cpt(EpicsSignal, "current_uid", string=True)
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
        elif name == "stop":
            self.last_uid.put(doc["run_start"])

    def state_callback(self, new, old):
        self.state.put(new)
