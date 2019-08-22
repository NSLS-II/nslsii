import uuid
import asyncio
from bluesky import RunEngine
from bluesky import plans as bps
from nslsii.baton import Baton
from nslsii import configure_base
import pytest
import subprocess
import os


@pytest.fixture(scope="function")
def baton_ioc(request):
    stdout = subprocess.PIPE
    stdin = None
    prefix = f"{str(uuid.uuid4())[:6]}:"
    # Start up an IOC based on the thermo_sim device in caproto.ioc_examples
    ioc_process = subprocess.Popen(
        ["baton-ioc", "--prefix", prefix, "--list-pvs"],
        stdout=stdout,
        stdin=stdin,
        env=os.environ,
    )

    def kill_ioc():
        ioc_process.terminate()

    request.addfinalizer(kill_ioc)
    return prefix


def test_baton(baton_ioc):
    b = Baton(baton_ioc, name="b")
    b.wait_for_connection(timeout=5)
    b.read()

    assert b.baton.get() == ""
    cb = b.acquire_baton()
    assert b.baton.get() != ""
    cb()
    cb()

    with pytest.raises(RuntimeError):
        b.acquire_baton()

    cb2 = b.acquire_baton(steal_baton=True)
    with pytest.raises(RuntimeError):
        cb()

    cb2()


def _inner_test(RE, b):
    assert b.baton.get() != ""
    for _ in range(5):
        uid, = RE(bps.count([]))
        assert b.current_uid.get() == uid
        assert b.current_scanid.get() == RE.md["scan_id"]

    b.baton.put("")
    with pytest.raises(RuntimeError):
        RE([])


def test_baton_RE(baton_ioc):
    b = Baton(baton_ioc, name="b")
    b.wait_for_connection(timeout=5)
    assert b.baton.get() == ""
    loop = asyncio.new_event_loop()
    loop.set_debug(True)
    RE = RunEngine({}, loop=loop, acquire_baton=b.acquire_baton)
    RE.subscribe(b.doc_callback, "start")
    RE.state_hook = b.state_callback
    _inner_test(RE, b)


def test_configure_base(baton_ioc):
    out = {}
    b = Baton(baton_ioc, name="b")
    b.wait_for_connection(timeout=5)
    configure_base(out, "temp", baton=b, magics=False)
    RE = out["RE"]

    _inner_test(RE, b)
