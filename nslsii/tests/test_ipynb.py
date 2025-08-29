from __future__ import annotations

import os


def test_ipynb():
    from nslsii.common import ipynb  # noqa: PLC0415

    obj = ipynb.get_sys_info()
    obj.data  # noqa: B018
    obj.filename  # noqa: B018
    obj.metadata  # noqa: B018
    obj.url  # noqa: B018
    obj.reload()


def test_touchbl():
    from nslsii.common import if_touch_beamline  # noqa: PLC0415

    if "TOUCHBEAMLINE" in os.environ:
        del os.environ["TOUCHBEAMLINE"]

    assert not if_touch_beamline()

    os.environ["TOUCHBEAMLINE"] = "1"

    assert if_touch_beamline()
