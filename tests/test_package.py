from __future__ import annotations

import importlib.metadata

import nslsii as m


def test_version():
    assert importlib.metadata.version("nslsii") == m.__version__
