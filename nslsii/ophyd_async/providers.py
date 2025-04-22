from datetime import date
from enum import Enum
from pathlib import Path
from typing import Optional
from ophyd_async.core import (
    FilenameProvider,
    PathProvider,
    PathInfo,
)
import os
import shortuuid


class YMDGranularity(int, Enum):
    none = 0
    year = 1
    month = 2
    day = 3


class ProposalNumYMDPathProvider(PathProvider):
    def __init__(
        self,
        filename_provider: FilenameProvider,
        metadata_dict: dict,
        granularity: YMDGranularity = YMDGranularity.day,
        separator=os.path.sep,
        **kwargs,
    ):
        self._filename_provider = filename_provider
        self._metadata_dict = metadata_dict
        self._granularity = granularity
        self._ymd_separator = separator
        self._beamline_proposals_dir = self.get_beamline_proposals_dir()
        super().__init__(filename_provider, **kwargs)

    @property
    def filename_provider(self):
        return self._filename_provider

    def get_beamline_proposals_dir(self):
        """
        Function that computes path to the proposals directory based on TLA env vars
        """

        beamline_tla = os.getenv(
            "ENDSTATION_ACRONYM", os.getenv("BEAMLINE_ACRONYM", "")
        ).lower()
        beamline_proposals_dir = Path(f"/nsls2/data/{beamline_tla}/proposals/")

        return beamline_proposals_dir

    def generate_directory_path(self, device_name: Optional[str] = None):
        """Helper function that generates ymd path structure"""

        current_date_template = ""
        if self._granularity >= YMDGranularity.day:
            current_date_template = f"%Y{self._ymd_separator}%m{self._ymd_separator}%d"
        elif self._granularity == YMDGranularity.month:
            current_date_template = f"%Y{self._ymd_separator}%m"
        elif self._granularity == YMDGranularity.year:
            current_date_template = f"%Y{self._ymd_separator}"

        current_date = date.today().strftime(current_date_template)

        if device_name is None:
            ymd_dir_path = current_date
        else:
            ymd_dir_path = os.path.join(
                device_name,
                current_date,
            )

        directory_path = (
            self._beamline_proposals_dir
            / self._metadata_dict["cycle"]
            / self._metadata_dict["data_session"]
            / "assets"
            / ymd_dir_path
        )

        return directory_path

    def __call__(self, device_name: str = None) -> PathInfo:
        directory_path = self.generate_directory_path(device_name=device_name)

        return PathInfo(
            directory_path=directory_path,
            filename=self._filename_provider(),
            create_dir_depth=-self._granularity,
        )


class ProposalNumScanNumPathProvider(ProposalNumYMDPathProvider):
    def __init__(
        self,
        filename_provider: FilenameProvider,
        metadata_dict: dict,
        base_name: str = "scan",
        granularity: YMDGranularity = YMDGranularity.none,
        ymd_separator=os.path.sep,
        **kwargs,
    ):
        self._base_name = base_name
        super().__init__(
            filename_provider,
            metadata_dict,
            granularity=granularity,
            ymd_separator=ymd_separator,
            **kwargs,
        )

    def __call__(self, device_name: Optional[str] = None) -> PathInfo:
        directory_path = self.generate_directory_path(device_name=device_name)

        final_dir_path = (
            directory_path / f"{self._base_name}_{self._metadata_dict['scan_id']:06}"
        )

        return PathInfo(
            directory_path=final_dir_path,
            filename=self._filename_provider(),
            # Add one to dir depth creation level to account for scan dir
            create_dir_depth=-self._granularity - 1,
        )


class ShortUUIDFilenameProvider(FilenameProvider):
    """Generates short uuid filenames with device name as prefix"""

    def __init__(self, separator="_", **kwargs):
        self._separator = separator
        super().__init__(**kwargs)

    def __call__(self, device_name: Optional[str] = None) -> str:
        sid = shortuuid.uuid()
        if device_name is not None:
            return f"{device_name}{self._separator}{sid}"
        else:
            return sid


class AcqModeFilenameProvider(ShortUUIDFilenameProvider):
    def __init__(self, initial_mode, **kwargs):
        if not isinstance(initial_mode, Enum) or not isinstance(
            initial_mode.value, str
        ):
            raise TypeError("Initial acquisition mode type must be a string enum!")

        self._mode = initial_mode
        self._mode_type = type(initial_mode)
        super().__init__(**kwargs)

    def switch_mode(self, new_mode):
        if not isinstance(new_mode, self._mode_type):
            raise RuntimeError(
                f"{new_mode} is not a valid option for {self._mode_type}!"
            )
        else:
            self._mode = new_mode

    def __call__(self, **kwargs):
        return super().__call__(device_name=self._mode.value)


class DeviceNameFilenameProvider(FilenameProvider):
    """Filename provider that uses device name as filename"""

    def __call__(self, device_name: Optional[str] = None) -> str:
        if device_name is None:
            raise RuntimeError(
                f"Device name must be passed in when calling {type(self).__name__}!"
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
        super().__init__(ShortUUIDFilenameProvider(), *args, **kwargs)
