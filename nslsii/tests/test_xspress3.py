from collections import OrderedDict
from pathlib import Path
import re

import h5py
import pytest

from bluesky import RunEngine
from bluesky.plans import count
from ophyd import Component, Device, DynamicDeviceComponent, Signal
from ophyd.areadetector import Xspress3Detector
from ophyd.sim import SynSignal

from nslsii.areadetector.xspress3 import (
    Mca,
    McaSum,
    McaRoi,
    Sca,
    Xspress3HDF5Handler,
    Xspress3FileStore,
    build_channel_class,
    build_detector_class,
)


def test_xspress3_hdf5_handler(tmpdir):
    """
    Currently just testing instantiation.
    """

    h5_file_path = Path(tmpdir) / "test_xspress3_hdf5_handler.h5"
    with h5py.File(h5_file_path, "w"):
        Xspress3HDF5Handler(filename=h5_file_path)


@pytest.mark.skip()
def test_xspress3_filestore(tmpdir):
    """
    Skip this test because it is still under development.

    Parameters
    ----------
    tmpdir:

    Returns
    -------


    """

    class SimulatedXspress3McaRoi:
        total_rbv = Component(SynSignal, "Total_RBV")

        def __init__(self):
            self.total_rbv.sim_set_func(lambda: 0.1)

    class SimulatedXspress3Channel(Device):
        mcarois = DynamicDeviceComponent(
            defn=OrderedDict(
                {"mcaroi01": (SimulatedXspress3McaRoi, "MCA1ROI:1:", dict())}
            )
        )

    class SimulatedXspress3Detector(Device):
        hdf5plugin = Component(
            Xspress3FileStore,
            "HDF1:",
            read_path_template="/read/path/template/",
            write_path_template="/write/path/template/",
            root=tmpdir,
        )

        cam = None

        channels = DynamicDeviceComponent(
            defn=OrderedDict({"channel_1": (SimulatedXspress3Channel, "", dict())})
        )

        def trigger(self):
            return self.channels.channel_1.mcarois.mcaroi01.trigger()

    simulated_xspress3 = SimulatedXspress3Detector(name="simulated_xspress3")

    RE = RunEngine()
    RE(count([simulated_xspress3]))


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
    channel_class = build_channel_class(channel_number=2, mcaroi_numbers=(1, 2, 3))

    assert hasattr(channel_class, "channel_number")
    assert getattr(channel_class, "channel_number") == 2

    assert hasattr(channel_class, "sca")
    assert hasattr(channel_class, "mca")
    assert hasattr(channel_class, "mca_sum")
    assert hasattr(channel_class, "mcarois")

    # there should be 3 MCAROI attributes: mcaroi01, mcaroi02, mcaroi3
    expected_mcaroi_attr_names = {
        f"mcaroi{mcaroi_i:02d}" for mcaroi_i in range(1, 3 + 1)
    }

    # there should be no other MCAROI attributes
    all_mcaroi_attr_names = {
        attr_name
        for attr_name in channel_class.mcarois.__dir__()
        if attr_name.startswith("mcaroi")
    }

    assert expected_mcaroi_attr_names == all_mcaroi_attr_names


def test_instantiate_channel_class():
    """
    Leave verification of Component attributes to the previous test,
    focus on PV names here.
    """
    channel_class = build_channel_class(channel_number=2, mcaroi_numbers=(46, 47, 48))
    channel_2 = channel_class(prefix="Xsp3:", name="channel_2")

    assert channel_2.sca.clock_ticks.pvname == "Xsp3:C2SCA:0:Value_RBV"

    assert channel_2.mca.array_data.pvname == "Xsp3:MCA2:ArrayData"

    assert channel_2.mca_sum.array_data.pvname == "Xsp3:MCASUM2:ArrayData"

    assert channel_2.mcarois.mcaroi46.total_rbv.pvname == "Xsp3:MCA2ROI:46:Total_RBV"
    assert channel_2.mcarois.mcaroi47.total_rbv.pvname == "Xsp3:MCA2ROI:47:Total_RBV"
    assert channel_2.mcarois.mcaroi48.total_rbv.pvname == "Xsp3:MCA2ROI:48:Total_RBV"

    assert (
        channel_2.__repr__()
        == "GeneratedXspress3Channel(channel_number=2, mcaroi_numbers=(46, 47, 48))"
    )


def test_get_mcaroi_count():
    detector_class = build_detector_class(channel_numbers=(3, 5), mcaroi_numbers=(4, 6))
    detector = detector_class(prefix="Xsp3:", name="xs3")

    assert detector.get_channel(channel_number=3).get_mcaroi_count() == 2
    assert detector.get_channel(channel_number=5).get_mcaroi_count() == 2


def test_mcaroi_numbers():
    detector_class = build_detector_class(channel_numbers=(3, 5), mcaroi_numbers=(4, 6))
    detector = detector_class(prefix="Xsp3:", name="xs3")

    assert detector.get_channel(channel_number=3).mcaroi_numbers == (4, 6)
    assert detector.get_channel(channel_number=5).mcaroi_numbers == (4, 6)


def test_get_mcaroi():
    channel_class = build_channel_class(channel_number=2, mcaroi_numbers=(1, 2))
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
    channel_class = build_channel_class(channel_number=2, mcaroi_numbers=(1, 2))
    channel_2 = channel_class(prefix="Xsp3:", name="channel_2")

    mcaroi_attr_name_list = list(channel_2.iterate_mcaroi_attr_names())
    assert mcaroi_attr_name_list == ["mcaroi01", "mcaroi02"]


def test_iterate_mcarois():
    channel_class = build_channel_class(channel_number=2, mcaroi_numbers=(1, 2))
    channel_2 = channel_class(prefix="Xsp3:", name="channel_2")

    mcaroi_list = list(channel_2.iterate_mcarois())
    assert len(mcaroi_list) == 2


def test_validate_mcaroi_numbers():
    # channel number is too low
    with pytest.raises(
        ValueError,
        match=re.escape("channel number '0' is outside the allowed interval [1,16]"),
    ):
        build_channel_class(channel_number=0, mcaroi_numbers=())

    # channel number is too high
    with pytest.raises(
        ValueError,
        match=re.escape("channel number '17' is outside the allowed interval [1,16]"),
    ):
        build_channel_class(channel_number=17, mcaroi_numbers=())

    # channel number is not an integer
    with pytest.raises(
        ValueError,
        match=re.escape("channel number '1.0' is not an integer"),
    ):
        build_channel_class(channel_number=1.0, mcaroi_numbers=())


def test_build_detector_class():
    """
    Verify all channel Components are present.
    """
    detector_class = build_detector_class(
        channel_numbers=(1, 2, 3), mcaroi_numbers=(4, 5)
    )
    assert Xspress3Detector in detector_class.__mro__
    assert hasattr(detector_class, "channels")

    # there should be 3 channel attributes: channel01, channel02, channel03
    expected_channel_attr_names = {f"channel{channel_i:02d}" for channel_i in (1, 2, 3)}

    channel_attr_name_re = re.compile(r"channel\d{2}")
    # there should be no other channel_n attributes
    all_channel_attr_names = {
        attr_name
        for attr_name in detector_class.channels.__dir__()
        if channel_attr_name_re.match(attr_name)
    }

    assert expected_channel_attr_names == all_channel_attr_names


def test_instantiate_detector_class():
    """
    Leave the verification of channel attributes to the previous test,
    focus on PV names here.
    """

    # use this to test detector_parent_classes
    class AnotherParentClass:
        pass

    detector_class = build_detector_class(
        channel_numbers=(14, 15, 16),
        mcaroi_numbers=(47, 48),
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

    assert (
        detector.channels.channel14.sca.clock_ticks.pvname == "Xsp3:C14SCA:0:Value_RBV"
    )
    assert (
        detector.channels.channel14.mca_sum.array_data.pvname
        == "Xsp3:MCASUM14:ArrayData"
    )
    assert detector.channels.channel14.mca.array_data.pvname == "Xsp3:MCA14:ArrayData"
    assert (
        detector.channels.channel14.mcarois.mcaroi47.total_rbv.pvname
        == "Xsp3:MCA14ROI:47:Total_RBV"
    )
    assert (
        detector.channels.channel14.mcarois.mcaroi48.total_rbv.pvname
        == "Xsp3:MCA14ROI:48:Total_RBV"
    )

    assert (
        detector.channels.channel15.sca.clock_ticks.pvname == "Xsp3:C15SCA:0:Value_RBV"
    )
    assert (
        detector.channels.channel15.mca_sum.array_data.pvname
        == "Xsp3:MCASUM15:ArrayData"
    )
    assert detector.channels.channel15.mca.array_data.pvname == "Xsp3:MCA15:ArrayData"
    assert (
        detector.channels.channel15.mcarois.mcaroi47.total_rbv.pvname
        == "Xsp3:MCA15ROI:47:Total_RBV"
    )
    assert (
        detector.channels.channel15.mcarois.mcaroi48.total_rbv.pvname
        == "Xsp3:MCA15ROI:48:Total_RBV"
    )

    assert (
        detector.channels.channel16.sca.clock_ticks.pvname == "Xsp3:C16SCA:0:Value_RBV"
    )
    assert (
        detector.channels.channel16.mca_sum.array_data.pvname
        == "Xsp3:MCASUM16:ArrayData"
    )
    assert detector.channels.channel16.mca.array_data.pvname == "Xsp3:MCA16:ArrayData"
    assert (
        detector.channels.channel16.mcarois.mcaroi47.total_rbv.pvname
        == "Xsp3:MCA16ROI:47:Total_RBV"
    )
    assert (
        detector.channels.channel16.mcarois.mcaroi48.total_rbv.pvname
        == "Xsp3:MCA16ROI:48:Total_RBV"
    )


def test_extra_class_members():
    detector_class = build_detector_class(
        channel_numbers=(3, 5),
        mcaroi_numbers=(4, 6),
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
            extra_class_members={
                "get_channel_count": 10,
            },
        )


def test_channel_numbers():
    detector_class = build_detector_class(channel_numbers=(3, 5), mcaroi_numbers=(4, 6))
    detector = detector_class(prefix="Xsp3:", name="xs3")

    assert detector.channel_numbers == (3, 5)


def test_get_channel_count():
    detector_class = build_detector_class(channel_numbers=(3, 5), mcaroi_numbers=(4, 6))
    detector = detector_class(prefix="Xsp3:", name="xs3")

    assert detector.get_channel_count() == 2


def test_get_channel():
    detector_class = build_detector_class(channel_numbers=(3, 5), mcaroi_numbers=(4, 6))
    detector = detector_class(prefix="Xsp3:", name="xs3")

    channel03 = detector.get_channel(channel_number=3)
    assert channel03.mcarois.mcaroi04.total_rbv.pvname == "Xsp3:MCA3ROI:4:Total_RBV"

    channel05 = detector.get_channel(channel_number=5)
    assert channel05.mcarois.mcaroi06.total_rbv.pvname == "Xsp3:MCA5ROI:6:Total_RBV"

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
    detector_class = build_detector_class(channel_numbers=(3, 5), mcaroi_numbers=(4, 6))
    detector = detector_class(prefix="Xsp3:", name="xs3")

    channel_list = list(detector.iterate_channels())
    assert len(channel_list) == 2
