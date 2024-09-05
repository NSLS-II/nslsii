import pytest
import os
from ophyd_async.core import StaticFilenameProvider

from nslsii.ophydv2 import ProposalNumYMDPathProvider, ProposalNumScanNumPathProvider, ShortUUIDFilenameProvider, DeviceNameFilenameProvider

@pytest.fixture
def fp():
    return StaticFilenameProvider("test")

@pytest.fixture
def dummy_re_md_dict():
    md = {
        "data_session": "pass-000000",
        "cycle": "2024-3",
    }
    return md


@pytest.mark.parametrize(
    ("dev_name_base", "use_dev_name", "expected_devname_pos"),
    [
        (True, True, -1),
        (False, True, -4),
        (False, False, None),
    ],
)
def test_proposal_num_ymd_path_provider(dev_name_base, use_dev_name, expected_devname_pos, fp, dummy_re_md_dict):
    os.environ["BEAMLINE_ACRONYM"] = "tst"

    pp = ProposalNumYMDPathProvider(fp, dummy_re_md_dict, device_name_as_base_dir=dev_name_base)

    if use_dev_name:
        info = pp(device_name="test")
    else:
        info = pp()

    assert str(info.directory_path).startswith("/nsls2/data/tst/proposals/2024-3/pass-000000/assets")
    assert info.create_dir_depth == -4

    if use_dev_name:
        str(info.directory_path).split('/')[expected_devname_pos] == "test"
    else:
        assert "test" not in str(info.directory_path)

def test_proposal_num_scan_num_path_provider(fp, dummy_re_md_dict):
    os.environ["BEAMLINE_ACRONYM"] = "tst"

    pp = ProposalNumScanNumPathProvider(fp, dummy_re_md_dict)

    info = pp()

    assert str(info.directory_path) == "/nsls2/data/tst/proposals/2024-3/pass-000000/assets/scan_00000"
    assert info.create_dir_depth == -1

    info_b = pp()

    assert str(info_b.directory_path) == "/nsls2/data/tst/proposals/2024-3/pass-000000/assets/scan_00001"
    assert info_b.create_dir_depth == -1