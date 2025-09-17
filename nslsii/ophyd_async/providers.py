from datetime import date
from enum import Enum
from pathlib import PurePath, PurePosixPath, PureWindowsPath
from typing import Optional
from urllib.parse import urlunparse
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
        windows_drive_letter: str | None = None,
        extra_dir_levels_fmt: str | None = None,
        **kwargs,
    ):
        self._filename_provider = filename_provider
        self._metadata_dict = metadata_dict
        self._granularity = granularity
        self._base_read_directory = self.get_beamline_proposals_dir()
        self._base_write_directory = self.get_write_directory_path(windows_drive_letter)
        self._extra_dir_levels_fmt = extra_dir_levels_fmt

        super().__init__(filename_provider, **kwargs)

    @property
    def filename_provider(self):
        return self._filename_provider

    def get_write_directory_path(self, windows_drive_letter: str | None) -> PurePath:
        if windows_drive_letter is None:
            return self.get_beamline_proposals_dir()
        else:
            return PureWindowsPath(f"{windows_drive_letter}:\\proposals")

    def get_beamline_proposals_dir(self):
        """
        Function that computes path to the proposals directory based on TLA env vars
        """

        beamline_tla = os.getenv(
            "ENDSTATION_ACRONYM", os.getenv("BEAMLINE_ACRONYM", "")
        ).lower()
        beamline_proposals_dir = PurePosixPath(f"/nsls2/data/{beamline_tla}/proposals/")

        return beamline_proposals_dir

    def generate_directory_path(self, base_path: PurePath, device_name: Optional[str] = None):
        """Helper function that generates ymd path structure"""

        path_semantics = type(base_path)

        if self._granularity >= YMDGranularity.day:
            current_date_template = "%Y/%m/%d"
        elif self._granularity == YMDGranularity.month:
            current_date_template = "%Y/%m"
        elif self._granularity == YMDGranularity.year:
            current_date_template = "%Y/"

        current_date = path_semantics(date.today().strftime(current_date_template))

        if device_name is None:
            ymd_dir_path = current_date
        else:
            ymd_dir_path = path_semantics(device_name) / current_date

        directory_path = (
            base_path
            / str(self._metadata_dict["cycle"])
            / str(self._metadata_dict["data_session"])
            / "assets"
            / ymd_dir_path
        )

        if self._extra_dir_levels_fmt is not None:
            directory_path = directory_path / self._extra_dir_levels_fmt.format(**self._metadata_dict)

        return directory_path

    def __call__(self, device_name: str = None) -> PathInfo:
        full_write_path = self.generate_directory_path(self._base_write_directory, device_name=device_name)
        full_read_path = self.generate_directory_path(self._base_read_directory, device_name=device_name)

        return PathInfo(
            directory_path=full_write_path,
            directory_uri=urlunparse(
                (
                    "file",
                    "localhost",
                    f"{full_read_path.as_posix()}/",
                    "",
                    "",
                    None,
                )
            ),
            filename=self._filename_provider(),
            create_dir_depth=-self._granularity,
        )


class ProposalNumScanNumPathProvider(ProposalNumYMDPathProvider):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            extra_dir_levels_fmt = "scan_{scan_id:05d}"
            **kwargs,
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
