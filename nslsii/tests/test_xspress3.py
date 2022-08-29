import datetime
import re
import time

import pytest

from ophyd import Component, Kind, Signal
from ophyd.areadetector import ADBase, Xspress3Detector

from nslsii.areadetector.xspress3 import (
    Mca,
    McaSum,
    McaRoi,
    Sca,
    Xspress3Trigger,
    Xspress3HDF5Plugin,
    build_channel_class,
    build_xspress3_class,
    build_detector_class,
)


def test_mca_init():
    """
    Test initialization.
    """

    mca = Mca(prefix="MCA:", name="mca")
    assert mca.name == "mca"
    assert mca.prefix == "MCA:"
    assert mca.parent is None
    assert mca.array_data.pvname == "MCA:ArrayData"


def test_mca_sum_init():
    """
    Test initialization.
    """

    mca_sum = McaSum(prefix="MCASUM:", name="mcasum")
    assert mca_sum.name == "mcasum"
    assert mca_sum.prefix == "MCASUM:"
    assert mca_sum.parent is None
    assert mca_sum.array_data.pvname == "MCASUM:ArrayData"


def test_mca_roi_init():
    """
    Test initialization.
    """

    mcaroi = McaRoi(prefix="MCA1ROI:1:", name="mcaroi01")
    assert mcaroi.mcaroi_number == 1
    assert mcaroi.name == "mcaroi01"
    assert mcaroi.prefix == "MCA1ROI:1:"
    assert mcaroi.parent is None
    assert mcaroi.roi_name.pvname == "MCA1ROI:1:Name"
    assert mcaroi.min_x.pvname == "MCA1ROI:1:MinX"
    assert mcaroi.size_x.pvname == "MCA1ROI:1:SizeX"
    assert mcaroi.total_rbv.pvname == "MCA1ROI:1:Total_RBV"


def test_sca_init():
    """
    Test initialization.
    """

    sca = Sca(prefix="SCA:", name="sca")
    assert sca.name == "sca"
    assert sca.prefix == "SCA:"
    assert sca.parent is None
    assert sca.clock_ticks.pvname == "SCA:0:Value_RBV"
    assert sca.reset_ticks.pvname == "SCA:1:Value_RBV"
    assert sca.reset_counts.pvname == "SCA:2:Value_RBV"
    assert sca.all_event.pvname == "SCA:3:Value_RBV"
    assert sca.all_good.pvname == "SCA:4:Value_RBV"
    assert sca.window_1.pvname == "SCA:5:Value_RBV"
    assert sca.window_2.pvname == "SCA:6:Value_RBV"
    assert sca.pileup.pvname == "SCA:7:Value_RBV"
    assert sca.event_width.pvname == "SCA:8:Value_RBV"
    assert sca.dt_factor.pvname == "SCA:9:Value_RBV"
    assert sca.dt_percent.pvname == "SCA:10:Value_RBV"


def test_build_channel_class():
    """
    Try to verify all Component attributes are present.
    """
    channel_class = build_channel_class(
        channel_number=2, mcaroi_numbers=(1, 2, 3), image_data_key="image"
    )

    assert hasattr(channel_class, "image")

    assert hasattr(channel_class, "channel_number")
    assert channel_class.channel_number == 2

    assert hasattr(channel_class, "sca")
    assert hasattr(channel_class, "mca")
    assert hasattr(channel_class, "mca_sum")

    # there should be 3 MCAROI attributes: mcaroi01, mcaroi02, mcaroi3
    expected_mcaroi_attr_names = {
        f"mcaroi{mcaroi_i:02d}" for mcaroi_i in range(1, 3 + 1)
    }

    # there should be no other MCAROI attributes
    all_mcaroi_attr_names = {
        attr_name
        for attr_name in dir(channel_class)
        if re.match(r"mcaroi\d{2}", attr_name)
    }

    assert expected_mcaroi_attr_names == all_mcaroi_attr_names


def test_build_channel_class_with_parents():
    """
    Try to verify all Component attributes are present.
    """

    class AChannelParent(ADBase):
        pass

    channel_class = build_channel_class(
        channel_number=2,
        mcaroi_numbers=(1, 2, 3),
        image_data_key="image",
        channel_parent_classes=(AChannelParent,),
    )

    assert AChannelParent in channel_class.mro()


def test_instantiate_channel_class():
    """
    Leave verification of Component attributes to the previous test,
    focus on PV names here.
    """
    channel_class = build_channel_class(
        channel_number=2, mcaroi_numbers=(46, 47, 48), image_data_key="image"
    )
    channel_2 = channel_class(prefix="Xsp3:", name="channel_2")

    assert channel_2.get_external_file_ref().name == "channel_2_image"

    assert channel_2.sca.clock_ticks.pvname == "Xsp3:C2SCA:0:Value_RBV"

    assert channel_2.mca.array_data.pvname == "Xsp3:MCA2:ArrayData"

    assert channel_2.mca_sum.array_data.pvname == "Xsp3:MCASUM2:ArrayData"

    assert channel_2.mcaroi.ts_control.pvname == "Xsp3:MCA2ROI:TSControl"
    assert channel_2.mcaroi.ts_num_points.pvname == "Xsp3:MCA2ROI:TSNumPoints"
    assert channel_2.mcaroi.ts_scan_rate.pvname == "Xsp3:MCA2ROI:TSRead.SCAN"

    assert channel_2.mcaroi46.total_rbv.pvname == "Xsp3:MCA2ROI:46:Total_RBV"
    assert channel_2.mcaroi47.total_rbv.pvname == "Xsp3:MCA2ROI:47:Total_RBV"
    assert channel_2.mcaroi48.total_rbv.pvname == "Xsp3:MCA2ROI:48:Total_RBV"

    assert (
        channel_2.__repr__()
        == "GeneratedXspress3Channel(channel_number=2, mcaroi_numbers=(46, 47, 48))"
    )


def test_get_mcaroi_count():
    detector_class = build_detector_class(
        channel_numbers=(3, 5), mcaroi_numbers=(4, 6), image_data_key="image"
    )
    detector = detector_class(prefix="Xsp3:", name="xs3")

    assert detector.get_channel(channel_number=3).get_mcaroi_count() == 2
    assert detector.get_channel(channel_number=5).get_mcaroi_count() == 2


def test_mcaroi_numbers():
    detector_class = build_detector_class(
        channel_numbers=(3, 5), mcaroi_numbers=(4, 6), image_data_key="image"
    )
    detector = detector_class(prefix="Xsp3:", name="xs3")

    assert detector.get_channel(channel_number=3).mcaroi_numbers == (4, 6)
    assert detector.get_channel(channel_number=5).mcaroi_numbers == (4, 6)


def test_get_mcaroi():
    channel_class = build_channel_class(
        channel_number=2, mcaroi_numbers=(1, 2), image_data_key="image"
    )
    channel02 = channel_class(prefix="Xsp3:", name="channel02")

    mcaroi01 = channel02.get_mcaroi(mcaroi_number=1)
    assert mcaroi01.total_rbv.pvname == "Xsp3:MCA2ROI:1:Total_RBV"

    mcaroi02 = channel02.get_mcaroi(mcaroi_number=2)
    assert mcaroi02.total_rbv.pvname == "Xsp3:MCA2ROI:2:Total_RBV"

    with pytest.raises(
        ValueError,
        match=re.escape("no MCAROI on channel 2 with prefix 'Xsp3:' has number 3"),
    ):
        channel02.get_mcaroi(mcaroi_number=3)

    with pytest.raises(
        ValueError,
        match=re.escape("MCAROI number '1.0' is not an integer"),
    ):
        channel02.get_mcaroi(mcaroi_number=1.0)

    with pytest.raises(
        ValueError,
        match=re.escape("MCAROI number '0' is outside the allowed interval [1,48]"),
    ):
        channel02.get_mcaroi(mcaroi_number=0)


def test_iterate_mcaroi_attr_names():
    channel_class = build_channel_class(
        channel_number=2, mcaroi_numbers=(1, 2), image_data_key="image"
    )
    channel_2 = channel_class(prefix="Xsp3:", name="channel_2")

    mcaroi_attr_name_list = list(channel_2.iterate_mcaroi_attr_names())
    assert mcaroi_attr_name_list == ["mcaroi01", "mcaroi02"]


def test_iterate_mcarois():
    channel_class = build_channel_class(
        channel_number=2, mcaroi_numbers=(1, 2), image_data_key="image"
    )
    channel_2 = channel_class(prefix="Xsp3:", name="channel_2")

    mcaroi_list = list(channel_2.iterate_mcarois())
    assert len(mcaroi_list) == 2


def test_validate_mcaroi_numbers():
    # channel number is too low
    with pytest.raises(
        ValueError,
        match=re.escape("channel number '0' is outside the allowed interval [1,16]"),
    ):
        build_channel_class(channel_number=0, mcaroi_numbers=(), image_data_key="image")

    # channel number is too high
    with pytest.raises(
        ValueError,
        match=re.escape("channel number '17' is outside the allowed interval [1,16]"),
    ):
        build_channel_class(
            channel_number=17, mcaroi_numbers=(), image_data_key="image"
        )

    # channel number is not an integer
    with pytest.raises(
        ValueError,
        match=re.escape("channel number '1.0' is not an integer"),
    ):
        build_channel_class(
            channel_number=1.0, mcaroi_numbers=(), image_data_key="image"
        )


def test_build_detector_class():
    """
    Verify all channel Components are present.
    """
    detector_class = build_detector_class(
        channel_numbers=(1, 2, 3), mcaroi_numbers=(4, 5), image_data_key="image"
    )
    assert Xspress3Detector in detector_class.__mro__

    # there should be 3 channel attributes: channel01, channel02, channel03
    expected_channel_attr_names = {f"channel{channel_i:02d}" for channel_i in (1, 2, 3)}

    channel_attr_name_re = re.compile(r"channel\d{2}")
    # there should be no other channel_n attributes
    all_channel_attr_names = {
        attr_name
        for attr_name in dir(detector_class)
        if channel_attr_name_re.match(attr_name)
    }

    assert expected_channel_attr_names == all_channel_attr_names


def test_instantiate_detector_class():
    """
    Leave the verification of channel attributes to the previous test,
    focus on PV names here.
    """

    # use this to test xspress3_parent_classes
    class AnotherParentClass:
        pass

    detector_class = build_detector_class(
        channel_numbers=(14, 15, 16),
        mcaroi_numbers=(47, 48),
        image_data_key="image",
        detector_parent_classes=(
            Xspress3Detector,
            AnotherParentClass,
        ),
    )
    assert Xspress3Detector in detector_class.__mro__
    assert AnotherParentClass in detector_class.__mro__

    detector = detector_class(prefix="Xsp3:", name="xs3")

    assert (
        detector.__repr__() == "GeneratedXspress3Detector(channels=("
        "GeneratedXspress3Channel(channel_number=14, mcaroi_numbers=(47, 48)),"
        "GeneratedXspress3Channel(channel_number=15, mcaroi_numbers=(47, 48)),"
        "GeneratedXspress3Channel(channel_number=16, mcaroi_numbers=(47, 48))))"
    )

    for channel_number in (14, 15, 16):
        channel = detector.get_channel(channel_number=channel_number)

        assert hasattr(channel, "image")
        assert (
            channel.mcaroi.ts_control.pvname == f"Xsp3:MCA{channel_number}ROI:TSControl"
        )
        assert (
            channel.mcaroi.ts_num_points.pvname
            == f"Xsp3:MCA{channel_number}ROI:TSNumPoints"
        )
        assert (
            channel.mcaroi.ts_scan_rate.pvname
            == f"Xsp3:MCA{channel_number}ROI:TSRead.SCAN"
        )
        assert (
            channel.sca.clock_ticks.pvname == f"Xsp3:C{channel_number}SCA:0:Value_RBV"
        )
        assert (
            channel.mca_sum.array_data.pvname
            == f"Xsp3:MCASUM{channel_number}:ArrayData"
        )

        for mcaroi_number in (47, 48):
            mcaroi = channel.get_mcaroi(mcaroi_number=mcaroi_number)
            assert (
                mcaroi.total_rbv.pvname
                == f"Xsp3:MCA{channel_number}ROI:{mcaroi_number}:Total_RBV"
            )


def test_extra_class_members():
    detector_class = build_detector_class(
        channel_numbers=(3, 5),
        mcaroi_numbers=(4, 6),
        image_data_key="image",
        extra_class_members={"ten": 10, "a_signal": Component(Signal, value=0)},
    )

    assert detector_class.ten == 10
    assert isinstance(detector_class.a_signal, Component)

    detector = detector_class(prefix="Xsp3:", name="xs3")

    assert detector.ten == 10
    assert isinstance(detector.a_signal, Signal)
    assert detector.a_signal.get() == 0


def test_extra_class_members_failure():
    """
    Do not specify an extra class member with the same
    name as one of the detector class members.
    """
    with pytest.raises(TypeError):
        detector_class = build_detector_class(
            channel_numbers=(3, 5),
            mcaroi_numbers=(4, 6),
            image_data_key="image",
            extra_class_members={
                "get_channel_count": 10,
            },
        )


def test_channel_numbers():
    detector_class = build_detector_class(
        channel_numbers=(3, 5), mcaroi_numbers=(4, 6), image_data_key="image"
    )
    detector = detector_class(prefix="Xsp3:", name="xs3")

    assert detector.channel_numbers == (3, 5)


def test_get_channel_count():
    detector_class = build_detector_class(
        channel_numbers=(3, 5), mcaroi_numbers=(4, 6), image_data_key="image"
    )
    detector = detector_class(prefix="Xsp3:", name="xs3")

    assert detector.get_channel_count() == 2


def test_get_channel():
    detector_class = build_detector_class(
        channel_numbers=(3, 5), mcaroi_numbers=(4, 6), image_data_key="image"
    )
    detector = detector_class(prefix="Xsp3:", name="xs3")

    channel03 = detector.get_channel(channel_number=3)
    print(channel03)
    assert channel03.mcaroi04.total_rbv.pvname == "Xsp3:MCA3ROI:4:Total_RBV"

    channel05 = detector.get_channel(channel_number=5)
    assert channel05.mcaroi06.total_rbv.pvname == "Xsp3:MCA5ROI:6:Total_RBV"

    with pytest.raises(
        ValueError,
        match=re.escape("no channel on detector with prefix 'Xsp3:' has number 2"),
    ):
        detector.get_channel(channel_number=2)

    with pytest.raises(
        ValueError,
        match=re.escape("channel number '4.0' is not an integer"),
    ):
        detector.get_channel(channel_number=4.0)

    with pytest.raises(
        ValueError,
        match=re.escape("channel number '0' is outside the allowed interval [1,16]"),
    ):
        detector.get_channel(channel_number=0)


def test_iterate_channels():
    detector_class = build_detector_class(
        channel_numbers=(3, 5), mcaroi_numbers=(4, 6), image_data_key="image"
    )
    detector = detector_class(prefix="Xsp3:", name="xs3")

    channel_list = list(detector.iterate_channels())
    assert len(channel_list) == 2


def test_xspress3_read_attrs():
    xspress3_class = build_xspress3_class(
        channel_numbers=(1, 2), mcaroi_numbers=(3, 4), image_data_key="image"
    )
    detector = xspress3_class(prefix="Xsp3:", name="xs3")

    assert detector.read_attrs == []

    detector.read_attrs = ["channel01.mcaroi04"]
    assert detector.read_attrs == ["channel01", "channel01.mcaroi04"]


# in the presence of spoof-beamline ...
# don't forget
#   export EPICS_CA_ADDR_LIST=localhost
#   export EPICS_CA_AUTO_ADDR_LIST="no"
@pytest.mark.xfail()
def test_hdf5plugin():

    xspress3_class = build_xspress3_class(
        channel_numbers=(1, 2),
        mcaroi_numbers=(3, 4),
        extra_class_members={
            "hdf5plugin": Component(
                Xspress3HDF5Plugin,
                name="h5p",
                prefix="HDF1:",
                root_path="/a/b/c",
                path_template="/a/b/c/%Y/%m/%d",
                resource_kwargs={},
            )
        },
    )
    xspress3 = xspress3_class(prefix="Xsp3:", name="xs3")

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


@pytest.mark.xfail()
def test_trigger():
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
                prefix="HDF1:",
                root_path="/a/b/c",
                path_template="/a/b/c/%Y/%m/%d",
                resource_kwargs={},
            )
        },
    )
    xspress3 = xspress3_class(prefix="Xsp3:", name="xs3")

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


import os
from bluesky import RunEngine
from bluesky.plans import count
from event_model import Filler
from area_detector_handlers.handlers import Xspress3HDF5Handler


def test_document_stream(xs3_data_dir, xs3_pv_prefix):
    """
    This test requires command line parameters be specified to pytest as follows,
    for example:
        pytest \
            --xs3-data-dir /nsls2/data/lob1/legacy/data \
            --xs3-pv-prefix XF:05IDD-ES{Xsp:1}:
    """
    if xs3_data_dir is None or not os.path.exists(xs3_data_dir):
        pytest.skip("xspress3 hardware is not available")

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
