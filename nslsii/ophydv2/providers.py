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


class ProposalNumYMDPathProvider(YMDPathProvider):
    def __init__(
        self, filename_provider: FilenameProvider, metadata_dict: dict, **kwargs
    ):
        self._metadata_dict = metadata_dict
        self._beamline_proposals_dir = (
            Path(f"/nsls2/data/{os.environ['BEAMLINE_ACRONYM'].lower()}/proposals/")
        )
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
        self._beamline_proposals_dir = (
            Path(f"/nsls2/data/{os.environ['BEAMLINE_ACRONYM'].lower()}/proposals/")
        )
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
