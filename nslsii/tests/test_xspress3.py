from pathlib import Path

import h5py

from nslsii.areadetector.xspress3 import (
    Mca,
    McaSum,
    McaRoi,
    Sca,
    Xspress3HDF5Handler,
    Xspress3ChannelBase,
    Xspress3Detector,
    build_channel_class,
    build_detector_class
)


def test_xspress3_hdf5_handler(tmpdir):
    """
    Currently just testing instantiation.
    """

    h5_file_path = Path(tmpdir) / "test_xspress3_hdf5_handler.h5"
    with h5py.File(h5_file_path, "w"):
        Xspress3HDF5Handler(filename=h5_file_path)


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
    channel_class = build_channel_class(channel_num=2, roi_count=3)

    assert hasattr(channel_class, "channel_num")
    assert getattr(channel_class, "channel_num") == 2

    assert hasattr(channel_class, "sca")
    assert hasattr(channel_class, "mca")
    assert hasattr(channel_class, "mca_sum")
    assert hasattr(channel_class, "mcarois")

    # there should be 3 MCAROI attributes: mcaroi01, mcaroi02, mcaroi3
    expected_mcaroi_attr_names = {
        f"mcaroi{mcaroi_i:02d}"
        for mcaroi_i
        in range(1, 3+1)
    }

    # there should be no other MCAROI attributes
    all_mcaroi_attr_names = {
        attr_name
        for attr_name
        in channel_class.mcarois.__dir__()
        if attr_name.startswith("mcaroi")
    }

    assert expected_mcaroi_attr_names == all_mcaroi_attr_names


def test_instantiate_channel_class():
    """
    Leave verification of Component attributes to the previous test,
    focus on PV names here.
    """
    channel_class = build_channel_class(channel_num=2, roi_count=3)
    channel_2 = channel_class(prefix="Xsp3:", name="channel_2")

    assert channel_2.sca.clock_ticks.pvname == "Xsp3:C2SCA:0:Value_RBV"

    assert channel_2.mca.array_data.pvname == "Xsp3:MCA2:ArrayData"

    assert channel_2.mca_sum.array_data.pvname == "Xsp3:MCA2SUM:ArrayData"

    assert channel_2.mcarois.mcaroi01.total_rbv.pvname == "Xsp3:MCA2ROI:1:Total_RBV"
    assert channel_2.mcarois.mcaroi02.total_rbv.pvname == "Xsp3:MCA2ROI:2:Total_RBV"
    assert channel_2.mcarois.mcaroi03.total_rbv.pvname == "Xsp3:MCA2ROI:3:Total_RBV"


def test_build_detector_class():
    """
    Try to verify all channel Components are present.
    """
    detector_class = build_detector_class(channel_count=3, roi_count=2)
    assert hasattr(detector_class, "channels")

    # there should be 3 channel attributes: channel_1, channel_2, channel_3
    expected_channel_attr_names = {
        f"channel_{channel_i}"
        for channel_i
        in range(1, 3+1)
    }

    # there should be no other channel_n attributes
    all_channel_attr_names = {
        attr_name
        for attr_name
        in detector_class.channels.__dir__()
        if attr_name.startswith("channel_")
    }

    assert expected_channel_attr_names == all_channel_attr_names


def test_instantiate_detector_class():
    """
    Leave the verification of channel attributes to the previous test,
    focus on PV names here.
    """
    detector_class = build_detector_class(channel_count=3, roi_count=2)

    detector = detector_class(prefix="Xsp3:", name="xs3")

    assert detector.channels.channel_1.sca.clock_ticks.pvname == "Xsp3:C1SCA:0:Value_RBV"
    assert detector.channels.channel_1.mca_sum.array_data.pvname == "Xsp3:MCA1SUM:ArrayData"
    assert detector.channels.channel_1.mca.array_data.pvname == "Xsp3:MCA1:ArrayData"
    assert detector.channels.channel_1.mcarois.mcaroi01.total_rbv.pvname == "Xsp3:MCA1ROI:1:Total_RBV"
    assert detector.channels.channel_1.mcarois.mcaroi02.total_rbv.pvname == "Xsp3:MCA1ROI:2:Total_RBV"

    assert detector.channels.channel_2.sca.clock_ticks.pvname == "Xsp3:C2SCA:0:Value_RBV"
    assert detector.channels.channel_2.mca_sum.array_data.pvname == "Xsp3:MCA2SUM:ArrayData"
    assert detector.channels.channel_2.mca.array_data.pvname == "Xsp3:MCA2:ArrayData"
    assert detector.channels.channel_2.mcarois.mcaroi01.total_rbv.pvname == "Xsp3:MCA2ROI:1:Total_RBV"
    assert detector.channels.channel_2.mcarois.mcaroi02.total_rbv.pvname == "Xsp3:MCA2ROI:2:Total_RBV"

    assert detector.channels.channel_3.sca.clock_ticks.pvname == "Xsp3:C3SCA:0:Value_RBV"
    assert detector.channels.channel_3.mca_sum.array_data.pvname == "Xsp3:MCA3SUM:ArrayData"
    assert detector.channels.channel_3.mca.array_data.pvname == "Xsp3:MCA3:ArrayData"
    assert detector.channels.channel_3.mcarois.mcaroi01.total_rbv.pvname == "Xsp3:MCA3ROI:1:Total_RBV"
    assert detector.channels.channel_3.mcarois.mcaroi02.total_rbv.pvname == "Xsp3:MCA3ROI:2:Total_RBV"
