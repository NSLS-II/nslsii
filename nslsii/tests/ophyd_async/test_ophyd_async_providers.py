from datetime import datetime
from enum import Enum
import pytest
import os
from ophyd_async.core import StaticFilenameProvider

from nslsii.ophyd_async import (
    ProposalNumYMDPathProvider,
    ProposalNumScanNumPathProvider,
    ShortUUIDFilenameProvider,
    DeviceNameFilenameProvider,
    YMDGranularity,
)
from nslsii.ophyd_async.providers import AcqModeFilenameProvider


class TomoFrameType(Enum):
    proj = "proj"
    flat = "flat"
    dark = "dark"


@pytest.fixture
def fp():
    return StaticFilenameProvider("test")


@pytest.fixture
def dummy_re_md_dict():
    md = {
        "data_session": "pass-000000",
        "cycle": "2024-3",
        "scan_id": 0,
    }
    return md


@pytest.mark.parametrize(
    ("ymd_granularity", "ymd_separator"),
    [
        (YMDGranularity.none, "_"),
        (YMDGranularity.year, os.path.sep),
        (YMDGranularity.month, "_"),
        (YMDGranularity.day, os.path.sep),
    ],
)
def test_proposal_num_ymd_path_provider(
    ymd_granularity, ymd_separator, dummy_re_md_dict, fp
):
    os.environ["BEAMLINE_ACRONYM"] = "tst"

    pp = ProposalNumYMDPathProvider(
        fp, dummy_re_md_dict, granularity=ymd_granularity, separator=ymd_separator
    )

    today = datetime.today()

    info = pp(device_name="test")
    dirpath = str(info.directory_path)

    assert dirpath.startswith(
        "/nsls2/data/tst/proposals/2024-3/pass-000000/assets/test"
    )

    if ymd_granularity == YMDGranularity.none:
        assert info.create_dir_depth == 0
        assert dirpath.endswith("test")
    elif ymd_granularity == YMDGranularity.year:
        assert info.create_dir_depth == -1
        assert dirpath.endswith(str(today.year))
    elif ymd_granularity == YMDGranularity.month:
        assert info.create_dir_depth == -2
        assert dirpath.endswith(str(f"{today.year}{ymd_separator}{today.month:02}"))
    elif ymd_granularity == YMDGranularity.day:
        assert info.create_dir_depth == -3
        assert dirpath.endswith(
            str(
                f"{today.year}{ymd_separator}{today.month:02}{ymd_separator}{today.day:02}"
            )
        )


def test_proposal_num_scan_num_path_provider(fp, dummy_re_md_dict):
    os.environ["BEAMLINE_ACRONYM"] = "tst"

    pp = ProposalNumScanNumPathProvider(fp, dummy_re_md_dict)

    info = pp(device_name="test")

    assert (
        str(info.directory_path)
        == "/nsls2/data/tst/proposals/2024-3/pass-000000/assets/test/scan_000000"
    )
    assert info.create_dir_depth == -1

    # Simulate scan id incrementing.
    pp._metadata_dict["scan_id"] += 1

    info_b = pp()

    assert (
        str(info_b.directory_path)
        == "/nsls2/data/tst/proposals/2024-3/pass-000000/assets/scan_000001"
    )
    assert info_b.create_dir_depth == -1


def test_device_name_filename_provider():
    dev_name_fp = DeviceNameFilenameProvider()
    assert "test" == dev_name_fp(device_name="test")

    # Device name filename provider must be called with device_name kwarg
    with pytest.raises(RuntimeError):
        dev_name_fp()


def test_short_uuid_filename_provider():
    sid_fp = ShortUUIDFilenameProvider()

    filename = sid_fp(device_name="test")
    assert filename.startswith("test")
    assert "_" in filename
    assert len(filename.split("_")[-1]) == 22


def test_acq_mode_filename_provider():
    am_fp = AcqModeFilenameProvider(TomoFrameType.proj)

    assert am_fp._mode_type == TomoFrameType
    assert am_fp._mode == TomoFrameType.proj

    assert am_fp().startswith("proj")

    am_fp.switch_mode(TomoFrameType.dark)

    assert am_fp().startswith("dark")

    with pytest.raises(RuntimeError):
        am_fp.switch_mode(20)

    with pytest.raises(TypeError):
        am_fp = AcqModeFilenameProvider(0)
