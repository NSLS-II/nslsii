from __future__ import annotations

import re
import textwrap
import threading
import time as ttime
import uuid
from enum import Enum
from pathlib import Path

import skimage.data
from caproto import ChannelType
from caproto.ioc_examples.mini_beamline import no_reentry
from caproto.server import PVGroup, pvproperty, run, template_arg_parser
from ophyd import Component as Cpt
from ophyd import Device, EpicsSignal, EpicsSignalRO
from ophyd.status import SubscriptionStatus

from .utils import now, save_hdf5_nd


class AcqStatuses(Enum):
    """Enum class for acquisition statuses."""

    IDLE = "idle"
    ACQUIRING = "acquiring"


class StageStates(Enum):
    """Enum class for stage states."""

    UNSTAGED = "unstaged"
    STAGED = "staged"


class CaprotoSaveIOC(PVGroup):
    """Generic Caproto Save IOC"""

    write_dir = pvproperty(
        value="/tmp",
        doc="The directory to write data to. It support datetime formatting, e.g. '/tmp/det/%Y/%m/%d/'",
        string_encoding="utf-8",
        dtype=ChannelType.CHAR,
        max_length=255,
    )
    file_name = pvproperty(
        value="test.h5",
        doc="The file name of the file to write to. It support <str>.format() based formatting, e.g. 'scan_{num:06d}.h5'",
        string_encoding="utf-8",
        dtype=ChannelType.CHAR,
        max_length=255,
    )
    full_file_path = pvproperty(
        value="",
        doc="Full path to the data file",
        dtype=str,
        read_only=True,
        max_length=255,
    )

    # TODO: check non-negative value in @frame_num.putter.
    frame_num = pvproperty(value=0, doc="Frame counter", dtype=int)

    stage = pvproperty(
        value=StageStates.UNSTAGED.value,
        enum_strings=[x.value for x in StageStates],
        dtype=ChannelType.ENUM,
        doc="Stage/unstage the device",
    )

    acquire = pvproperty(
        value=AcqStatuses.IDLE.value,
        enum_strings=[x.value for x in AcqStatuses],
        dtype=ChannelType.ENUM,
        doc="Acquire signal to save a dataset.",
    )

    def __init__(self, *args, update_rate=10.0, **kwargs):
        super().__init__(*args, **kwargs)

        self._update_rate = update_rate
        self._update_period = 1.0 / update_rate

        self._request_queue = None
        self._response_queue = None

    queue = pvproperty(value=0, doc="A PV to facilitate threading-based queue")

    @queue.startup
    async def queue(self, instance, async_lib):
        """The startup behavior of the count property to set up threading queues."""
        # pylint: disable=unused-argument
        self._request_queue = async_lib.ThreadsafeQueue(maxsize=1)
        self._response_queue = async_lib.ThreadsafeQueue(maxsize=1)

        # Start a separate thread that consumes requests and sends responses.
        thread = threading.Thread(
            target=self.saver,
            daemon=True,
            kwargs={
                "request_queue": self._request_queue,
                "response_queue": self._response_queue,
            },
        )
        thread.start()

    async def _stage(self, instance, value):
        """The stage method to perform preparation of a dataset to save the data."""
        if (
            instance.value in [True, StageStates.STAGED.value]
            and value == StageStates.STAGED.value
        ):
            msg = "The device is already staged. Unstage it first."
            print(msg)
            return False

        if value == StageStates.STAGED.value:
            # Steps:
            # 1. Render 'write_dir' with datetime lib
            # 2. Replace unsupported characters with underscores (sanitize).
            # 3. Check if sanitized 'write_dir' exists
            # 4. Render 'file_name' with .format().
            # 5. Replace unsupported characters with underscores.

            sanitizer = re.compile(pattern=r"[\":<>|\*\?\s]")
            date = now(as_object=True)
            write_dir = Path(sanitizer.sub("_", date.strftime(self.write_dir.value)))
            if not write_dir.exists():
                msg = f"Path '{write_dir}' does not exist."
                print(msg)
                return False

            file_name = self.file_name.value

            uid = (
                str(uuid.uuid4()) if "{uid" in file_name or "{suid" in file_name else ""
            )

            full_file_path = write_dir / file_name.format(
                num=self.frame_num.value, uid=uid, suid=uid[:8]
            )
            full_file_path = sanitizer.sub("_", str(full_file_path))

            print(f"{now()}: {full_file_path = }")

            await self.full_file_path.write(full_file_path)

            return True

        return False

    @stage.putter
    async def stage(self, *args, **kwargs):
        """The stage method."""
        return await self._stage(*args, **kwargs)

    async def _get_current_dataset(self, frame):
        """The method to return a desired dataset.

        See https://scikit-image.org/docs/stable/auto_examples/data/plot_3d.html
        for details about the dataset returned by the base class' method.
        """
        dataset = skimage.data.cells3d().sum(axis=1)
        # This particular example dataset has 60 frames available, so we will cycle the slices for frame>=60.
        return dataset[frame % dataset.shape[0], ...]

    @acquire.putter
    @no_reentry
    async def acquire(self, instance, value):
        """The acquire method to perform an individual acquisition of a data point."""
        if (
            value != AcqStatuses.ACQUIRING.value
            # or self.stage.value not in [True, StageStates.STAGED.value]
        ):
            return False

        if (
            instance.value in [True, AcqStatuses.ACQUIRING.value]
            and value == AcqStatuses.ACQUIRING.value
        ):
            print(
                f"The device is already acquiring. Please wait until the '{AcqStatuses.IDLE.value}' status."
            )
            return True

        await self.acquire.write(AcqStatuses.ACQUIRING.value)

        # Delegate saving the resulting data to a blocking callback in a thread.
        payload = {
            "filename": self.full_file_path.value,
            "data": await self._get_current_dataset(frame=self.frame_num.value),
            "uid": str(uuid.uuid4()),
            "timestamp": ttime.time(),
            "frame_number": self.frame_num.value,
        }

        await self._request_queue.async_put(payload)
        response = await self._response_queue.async_get()

        if response["success"]:
            # Increment the counter only on a successful saving of the file.
            await self.frame_num.write(self.frame_num.value + 1)

        # await self.acquire.write(AcqStatuses.IDLE.value)

        return False

    @staticmethod
    def saver(request_queue, response_queue):
        """The saver callback for threading-based queueing."""
        while True:
            received = request_queue.get()
            filename = received["filename"]
            data = received["data"]
            frame_number = received["frame_number"]
            try:
                save_hdf5_nd(fname=filename, data=data, mode="x", group_path="enc1")
                print(
                    f"{now()}: saved {frame_number=} {data.shape} data into:\n  {filename}"
                )

                success = True
                error_message = ""
            except Exception as exc:  # pylint: disable=broad-exception-caught
                success = False
                error_message = exc
                print(
                    f"Cannot save file {filename!r} due to the following exception:\n{exc}"
                )

            response = {"success": success, "error_message": error_message}
            response_queue.put(response)


class OphydDeviceWithCaprotoIOC(Device):
    """An ophyd Device which works with the base caproto extension IOC."""

    write_dir = Cpt(EpicsSignal, "write_dir", string=True)
    file_name = Cpt(EpicsSignal, "file_name", string=True)
    full_file_path = Cpt(EpicsSignalRO, "full_file_path", string=True)
    frame_num = Cpt(EpicsSignal, "frame_num")
    ioc_stage = Cpt(EpicsSignal, "stage", string=True)
    acquire = Cpt(EpicsSignal, "acquire", string=True)

    def set(self, command):
        """The set method with values for staging and acquiring."""

        expected_old_value = None
        expected_new_value = None
        obj = None
        cmd = None

        # print(f"{now()}: {command = }")
        if command in [StageStates.STAGED.value, "stage"]:
            expected_old_value = StageStates.UNSTAGED.value
            expected_new_value = StageStates.STAGED.value
            obj = self.ioc_stage
            cmd = StageStates.STAGED.value

        if command in [StageStates.UNSTAGED.value, "unstage"]:
            expected_old_value = StageStates.STAGED.value
            expected_new_value = StageStates.UNSTAGED.value
            obj = self.ioc_stage
            cmd = StageStates.UNSTAGED.value

        if command in [AcqStatuses.ACQUIRING.value, "acquire"]:
            expected_old_value = AcqStatuses.ACQUIRING.value
            expected_new_value = AcqStatuses.IDLE.value
            obj = self.acquire
            cmd = AcqStatuses.ACQUIRING.value

        def cb(value, old_value, **kwargs):
            # pylint: disable=unused-argument
            # print(f"{now()}: {old_value} -> {value}")
            if value == expected_new_value and old_value == expected_old_value:
                return True
            return False

        st = SubscriptionStatus(obj, callback=cb, run=False)
        # print(f"{now()}: {cmd = }")
        obj.put(cmd)
        return st


def check_args(parser_, split_args_):
    """Helper function to process caproto CLI args."""
    parsed_args = parser_.parse_args()
    prefix = parsed_args.prefix
    if not prefix:
        parser_.error("The 'prefix' argument must be specified.")

    ioc_opts, run_opts = split_args_(parsed_args)
    return ioc_opts, run_opts


if __name__ == "__main__":
    parser, split_args = template_arg_parser(
        default_prefix="", desc=textwrap.dedent(CaprotoSaveIOC.__doc__)
    )
    ioc_options, run_options = check_args(parser, split_args)
    ioc = CaprotoSaveIOC(**ioc_options)
    run(ioc.pvdb, **run_options)