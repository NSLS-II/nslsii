import datetime
import os
import re
import time

import pytest

from area_detector_handlers.handlers import Xspress3HDF5Handler
from bluesky import RunEngine
from bluesky.plans import count
from event_model import Filler
from ophyd import Component, Kind
from ophyd.areadetector import Xspress3Detector

from nslsii.areadetector.xspress3 import (
    Xspress3Trigger,
    Xspress3HDF5Plugin,
    build_xspress3_class,
)


# in the presence of spoof-beamline ...
# don't forget
#   export EPICS_CA_ADDR_LIST=localhost
#   export EPICS_CA_AUTO_ADDR_LIST="no"
@pytest.mark.skip("this test hangs")
def test_hdf5plugin(xs3_pv_prefix):
    """
    Test some HDF5Plugin behavior without saving a file.
    """

    if xs3_pv_prefix is None:
        pytest.skip("xspress3 PV prefix was not specified")

    xspress3_class = build_xspress3_class(
        channel_numbers=(1, 2),
        mcaroi_numbers=(3, 4),
        extra_class_members={
            "hdf5plugin": Component(
                Xspress3HDF5Plugin,
                name="h5p",
                prefix=f"{xs3_pv_prefix}HDF1:",
                root_path="/a/b/c",
                path_template="/a/b/c/%Y/%m/%d",
                resource_kwargs={},
            )
        },
    )
    xspress3 = xspress3_class(prefix=xs3_pv_prefix, name="xs3")

    xspress3.hdf5plugin.stage()

    assert re.match(
        r"\/a\/b\/c\/\d{4}\/\d{2}\/\d{2}", xspress3.hdf5plugin.file_path.get()
    )
    assert re.match(r"\w{8}\-\w{4}\-\w{4}\-\w{4}", xspress3.hdf5plugin.file_name.get())
    assert xspress3.hdf5plugin.file_number.get() == 0

    assert xspress3.hdf5plugin._resource["root"] == "/a/b/c"
    # expect resource path to look like YYYY/MM/DD/aaaaaaaa-bbbb-cccc-dddd_000000.h5
    assert re.match(
        r"\d{4}\/\d{2}\/\d{2}\/\w{8}\-\w{4}\-\w{4}\-\w{4}_000000\.h5",
        xspress3.hdf5plugin._resource["resource_path"],
    )

    xspress3.hdf5plugin.generate_datum(
        key=None, timestamp=datetime.datetime.now(), datum_kwargs={}
    )

    # expect one resource document and
    #   one datum document for each channel
    xspress3_asset_docs = list(xspress3.collect_asset_docs())
    assert len(xspress3_asset_docs) == 1 + xspress3.get_channel_count()

    xspress3.hdf5plugin.unstage()


def test_trigger(xs3_pv_prefix, xs3_data_dir):
    if xs3_data_dir is None or not os.path.exists(xs3_data_dir):
        pytest.skip("xspress3 data directory was not specified")
    if xs3_pv_prefix is None:
        pytest.skip("xspress3 PV prefix was not specified")

    xspress3_class = build_xspress3_class(
        channel_numbers=(1, 2, 4),
        mcaroi_numbers=(3, 5),
        image_data_key="image",
        # important to put Xspress3Trigger first or we get the wrong dispatch method?
        xspress3_parent_classes=(Xspress3Detector, Xspress3Trigger),
        extra_class_members={
            "hdf5plugin": Component(
                Xspress3HDF5Plugin,
                name="h5p",
                prefix=f"{xs3_pv_prefix}HDF1:",
                root_path=xs3_data_dir,
                #prefix="HDF1:",
                #root_path=xs3_data_dir,
                path_template=xs3_data_dir,
                resource_kwargs={},
            )
        },
    )
    xspress3 = xspress3_class(prefix=xs3_pv_prefix, name="xs3")

    # omit one channel to verify no datum document will be generated in this case
    xspress3.channel02.kind = Kind.omitted

    xspress3.stage()

    trigger_status = xspress3.trigger()
    assert not trigger_status.done

    xspress3.cam.acquire.set(0)
    time.sleep(1)
    assert trigger_status.done

    # expect one resource document and
    #   one datum document for each channel
    xspress3_asset_docs = list(xspress3.collect_asset_docs())
    assert len(xspress3_asset_docs) == 1 + xspress3.get_channel_count()

    xspress3.unstage()


def test_document_stream(xs3_pv_prefix, xs3_data_dir):
    """
    This test requires --xs3-pv-prefix and --xs3-data-dir command line
    parameters be specified to pytest, for example:
        $ python -m pytest \
            nslsii/tests/test_xspress3.py \
            --xs3-pv-prefix XF:05IDD-ES{Xsp:1}: \
            --xs3-data-dir "/nsls2/data/staff/jlynch/data"
    """
    if xs3_data_dir is None or not os.path.exists(xs3_data_dir):
        pytest.skip("xspress3 data directory was not specified")
    if xs3_pv_prefix is None:
        pytest.skip("xspress3 PV prefix was not specified")

    document_list = []

    def append_document(name, document):
        document_list.append((name, document))

    RE = RunEngine()
    RE.subscribe(append_document)

    xspress3_class = build_xspress3_class(
        channel_numbers=(1, 2, 4),
        mcaroi_numbers=(3, 5),
        image_data_key="image",
        xspress3_parent_classes=(Xspress3Detector, Xspress3Trigger),
        extra_class_members={
            "hdf5plugin": Component(
                Xspress3HDF5Plugin,
                name="h5p",
                prefix=f"{xs3_pv_prefix}HDF1:",
                root_path=xs3_data_dir,
                path_template=xs3_data_dir,
                resource_kwargs={},
            )
        },
    )
    xspress3 = xspress3_class(prefix=xs3_pv_prefix, name="xs3")

    RE(count([xspress3]))

    with Filler({Xspress3HDF5Handler.HANDLER_NAME: Xspress3HDF5Handler}, inplace=True) as filler:
        for name, document in document_list:
            filler(name, document)
