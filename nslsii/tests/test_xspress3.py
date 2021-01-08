from pathlib import Path

import h5py

from nslsii.areadetector.xspress3 import (
    McaRoi,
    Xspress3HDF5Handler,
    Xspress3Channel,
    Xspress3Detector,
)


def test_xspress3_hdf5_handler(tmpdir):
    """
    Currently just testing instantiation.
    """

    h5_file_path = Path(tmpdir) / "test_xspress3_hdf5_handler.h5"
    with h5py.File(h5_file_path, "w"):
        Xspress3HDF5Handler(filename=h5_file_path)


def test_mca_roi():
    """
    Testing only for correct PV name at the moment.
    """

    mcaroi = McaRoi(prefix="CHAN1:1:", name="mcaroi", parent=None)
    assert mcaroi.roi_name.pvname == "CHAN1:1:Name"


def test_channel_names():
    """
    Testing instantiation.
    """

    channel = Xspress3Channel(prefix="CHAN1:", name="channel_1", channel_num=1)
    assert channel.name == "channel_1"


def test_xspress3_channel_names():
    """
    """

    xspress3 = Xspress3Detector(prefix="Xsp3:", name="xs3")
    assert xspress3.channels.channel_1.mca.array_data.pvname == "Xsp3:MCA1:ArrayData"
