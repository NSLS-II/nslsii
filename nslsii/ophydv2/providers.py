from pathlib import Path
from typing import Optional
from ophyd_async.core import (
    FilenameProvider,
    YMDPathProvider,
    AutoIncrementingPathProvider,
    PathInfo,
)
import os
import shortuuid

def get_beamline_proposals_dir():
    beamline_tla = os.getenv(
        'ENDSTATION_ACRONYM', 
        os.getenv('BEAMLINE_ACRONYM', '')
    ).lower()
    beamline_proposals_dir = (
        Path(f"/nsls2/data/{beamline_tla}/proposals/")
    )

    return beamline_proposals_dir


class ProposalNumYMDPathProvider(YMDPathProvider):
    def __init__(
        self, filename_provider: FilenameProvider, metadata_dict: dict, **kwargs
    ):
        self._metadata_dict = metadata_dict
        self._beamline_proposals_dir = get_beamline_proposals_dir()
        super().__init__(
            filename_provider,
            self._beamline_proposals_dir,
            create_dir_depth=-4,
            **kwargs,
        )

    def __call__(self, device_name=None) -> PathInfo:
        self._base_directory_path = (
            self._beamline_proposals_dir
            / self._metadata_dict["cycle"]
            / self._metadata_dict["data_session"]
            / "assets"
        )
        return super().__call__(device_name=device_name)


class ProposalNumScanNumPathProvider(AutoIncrementingPathProvider):
    def __init__(
        self, filename_provider: FilenameProvider, metadata_dict: dict, **kwargs
    ):
        self._metadata_dict = metadata_dict
        self._beamline_proposals_dir = get_beamline_proposals_dir()

        super().__init__(
            filename_provider,
            self._beamline_proposals_dir,
            base_name="scan",
            create_dir_depth=-1,
            **kwargs,
        )

    def __call__(self, device_name: Optional[str] = None) -> PathInfo:
        self._base_directory_path = (
            self._beamline_proposals_dir
            / self._metadata_dict["cycle"]
            / self._metadata_dict["data_session"]
            / "assets"
        )
        return super().__call__(device_name=device_name)


class ShortUUIDFilenameProvider(FilenameProvider):
    def __init__(self, separator="_", **kwargs):
        self._separator = separator
        super().__init__(**kwargs)

    def __call__(self, device_name: Optional[str] = None) -> str:
        sid = shortuuid.uuid()
        if device_name is not None:
            return f"{device_name}{self._separator}{sid}"
        else:
            return sid


class DeviceNameFilenameProvider(FilenameProvider):
    def __call__(self, device_name: Optional[str] = None) -> str:
        if device_name is None:
            raise RuntimeError(
                "Device name must be passed in when calling DeviceNameFilenameProvider!"
            )
        return device_name


class NSLS2PathProvider(ProposalNumYMDPathProvider):
    """
    Default NSLS2 path provider
    
    Generates paths in the following format:

    /nsls2/data/{TLA}/proposals/{CYCLE}/{PROPOSAL}/assets/{DETECTOR}/{Y}/{M}/{D}

    Filenames will be {DETECTOR}_{SHORT_UID} followed by the appropriate
    extension as determined by your detector writer.

    Parameters
    ----------
    metadata_dict : dict
        Typically `RE.md`. Used for dynamic save path generation from sync-d experiment
    """

    def __init__(self, *args, **kwargs):
        default_filename_provider = ShortUUIDFilenameProvider()
        super().__init__(default_filename_provider, *args, **kwargs)