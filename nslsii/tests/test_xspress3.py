from nslsii.areadetector.xspress3 import Xspress3HDF5Handler, Xspress3Channel


def test_xspress3_hdf5_handler():
    Xspress3HDF5Handler(filename="test.")


def test_channel_names():
    channel = Xspress3Channel(prefix="CHAN{channel_num}:", name="CHAN{channel_num}:", channel_num=1)
    assert channel.name == "CHAN1:"
    #assert channel.mca.pv == "CHAN1:MCA1"
