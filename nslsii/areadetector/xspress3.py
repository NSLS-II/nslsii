import logging
import re
import time as ttime
from collections import OrderedDict

from databroker.assets.handlers import Xspress3HDF5Handler

from ophyd import Component as Cpt
from ophyd import DynamicDeviceComponent as DynamicDeviceCpt
from ophyd import EpicsSignal, EpicsSignalRO, Signal
from ophyd.areadetector import ADBase
from ophyd.areadetector import EpicsSignalWithRBV as SignalWithRBV
from ophyd.areadetector import Xspress3Detector
from ophyd.areadetector.filestore_mixins import FileStorePluginBase
from ophyd.areadetector.plugins import HDF5Plugin
from ophyd.device import BlueskyInterface, Staged
from ophyd.status import DeviceStatus

from ..detectors.utils import makedirs


logger = logging.getLogger(__name__)


class Xspress3Trigger(BlueskyInterface):
    """
    A basic trigger mixin. Good enough for simple cases.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._acquire_status = None
        self._abs_trigger_count = None

    def stage(self):
        self._abs_trigger_count = 0
        self.cam.acquire.subscribe(self._acquire_changed)
        return super().stage()

    def unstage(self):
        super_unstage_result = super().unstage()
        self.cam.acquire.clear_sub(self._acquire_changed)
        self._acquire_status = None
        return super_unstage_result

    def _acquire_changed(self, value=None, old_value=None, **kwargs):
        """Respond to changes in the Xspress3Detector.cam.acquire PV.

        The important behavior of this method is to mark self._acquire_status
        as `finished` when Xspress3Detector.cam.acquire changes from 1 to 0
        (high to low). A RunEngine is waiting for this change.

        Parameters
        ----------
        value: int
            new value of the Xspress3Detector.cam.acquire PV
        old_value: int
            previous value of the Xspress3Detector.cam.acquire PV
        kwargs: dict
            unused

        Returns
        -------
        No return value
        """

        if self._acquire_status is None:
            return
        if (old_value == 1) and (value == 0):
            # Negative-going edge means an acquisition just finished.
            self._acquire_status.set_finished()
            self._acquire_status = None

    def new_acquire_status(self):
        """
        Create, remember, and return a Status object that will be marked
        as `finished` when acquisition is done (see _acquire_changed). The
        intention is that this Status will be used by another object,
        for example a RunEngine.

        Returns
        -------
        DeviceStatus
        """

        self._acquire_status = DeviceStatus(self)
        return self._acquire_status

    def trigger(self):
        if self._staged != Staged.yes:
            raise RuntimeError(
                "tried to trigger Xspress3 with prefix {self.prefix} but it is not staged"
            )

        acquire_status = self.new_acquire_status()
        self.cam.acquire.put(1, wait=False)
        trigger_time = ttime.time()

        # tell the associated file plugins to do something about
        # each channel's data by invoking
        # FileStore.generate_datum(key=channel.name, ...)
        for channel in self.iterate_channels():
            self.dispatch(key=channel.name, timestamp=trigger_time)

        self._abs_trigger_count += 1

        return acquire_status


class Xspress3FileStore(FileStorePluginBase, HDF5Plugin):
    """
    Create resource and datum documents.
    """

    # TODO: these PVs may be obsolete
    num_capture_calc = Cpt(EpicsSignal, "NumCapture_CALC")
    num_capture_calc_disable = Cpt(EpicsSignal, "NumCapture_CALC.DISA")

    filestore_spec = Xspress3HDF5Handler.HANDLER_NAME

    def __init__(
        self,
        basename,
        *,
        stage_sleep_time=0.5,
        # JL: what are mds keys?
        # mds_key_format="{self.parent.cam.name}_ch{channel_number}",
        mds_key_format="{self.parent.name}_channels_channel{channel_number:02}",
        parent,
        **kwargs,
    ):
        """

        Parameters
        ----------
        basename:
        stage_sleep_time: int
            number of seconds to pause at the end of method stage()
        mds_key_format: str
        parent: Xspress3Detector, required
        kwargs:
        """
        super().__init__(basename, parent=parent, **kwargs)

        if not isinstance(parent, Xspress3Detector):
            raise TypeError(
                "parent must be an instance of ophyd.areadetector.Xspress3Detector"
            )

        # establish PV values to be set when this detector is staged
        # the original values will be replaced when it is unstaged
        self.stage_sigs[self.blocking_callbacks] = 1
        self.stage_sigs[self.enable] = 1
        self.stage_sigs[self.compression] = "zlib"
        self.stage_sigs[self.file_template] = "%s%s_%6.6d.h5"

        # allow for a pause when staging this detector
        self.stage_sleep_time = stage_sleep_time

        self._filestore_res = None
        # JL: what are mds_keys?
        self.mds_keys = {
            channel.channel_number: mds_key_format.format(
                self=self, channel_number=channel.channel_number
            )
            for channel in parent.iterate_channels()
        }

    def stop(self, success=False):
        super_stop_return = super().stop(success=success)
        self.capture.put(0)
        return super_stop_return

    def kickoff(self):
        raise NotImplementedError()

    def collect(self):
        raise NotImplementedError()

    def make_filename(self):
        file_name, read_path, write_path = super().make_filename()
        if self.parent.make_directories.get():
            makedirs(write_path)
        return file_name, read_path, write_path

    def stage(self):
        logger.debug("staging Xspress3 '%s'", self.parent.prefix)

        # force the Xspress3 to stop acquiring
        self.parent.cam.acquire.put(0, wait=True)

        total_points_reading = self.parent.total_points.get()
        if total_points_reading < 1:
            raise RuntimeError(f"total_points '{self.parent.total_points}' must be set")
        spectra_per_point_reading = self.parent.spectra_per_point.get()
        total_capture = total_points_reading * spectra_per_point_reading

        # stop previous acquisition
        # JL: this was set above, don't set it again
        # self.stage_sigs[self.parent.cam.acquire] = 0

        # re-order the stage signals and disable the calc record which is
        # interfering with the capture count
        # JL: can we get rid of num_capture_calc_disable?
        # JL: is self.num_capture even in stage_sigs?
        self.stage_sigs.pop(self.num_capture, None)
        self.stage_sigs.pop(self.parent.cam.num_images, None)
        self.stage_sigs[self.num_capture_calc_disable] = 1

        external_trig_reading = self.parent.external_trig.get()
        if external_trig_reading:
            logger.debug(
                "Xspress3 '%s' will be triggered externally", self.parent.prefix
            )
            self.stage_sigs[self.parent.cam.trigger_mode] = "TTL Veto Only"
            self.stage_sigs[self.parent.cam.num_images] = total_capture
        else:
            logger.debug(
                "Xspress3 '%s' will be triggered internally", self.parent.prefix
            )
            self.stage_sigs[self.parent.cam.trigger_mode] = "Internal"
            # JL: why not total_capture as above?
            self.stage_sigs[self.parent.cam.num_images] = spectra_per_point_reading

        self.stage_sigs[self.auto_save] = "No"

        filename, read_path, write_path = self.make_filename()
        logger.debug(
            "xspress3 '%s' read path: '%s' write path: '%s' filename: '%s'",
            self.parent.prefix,
            read_path,
            write_path,
            filename,
        )

        logger.debug("erasing old spectra with '%s'", self.parent.cam.erase)
        self.parent.cam.erase.put(1, wait=True)

        # this must be set after self.parent.cam.num_images because at the EPICS
        # layer there is a helpful link that sets this equal to that (but
        # not the other way)
        # JL: hoping num_capture does not exist on the new IOC
        self.stage_sigs[self.num_capture] = total_capture

        # apply the stage_sigs values
        super_stage_result = super().stage()

        # self._fn comes from FileStorePluginBase
        self._fn = self.file_template.get() % (
            self._fp,
            self.file_name.get(),
            self.file_number.get(),
        )

        if not self.file_path_exists.get():
            raise IOError(f"path '{self.file_path.get()}' does not exist on the IOC")

        logger.debug("inserting the filestore resource: '%s'", self._fn)
        # JL: calling generate_resource() in stage is usual
        self._generate_resource({})
        # JL: the last element of the last element of self._asset_docs_cache
        #     is the "resource"?
        # self._asset_docs_cache looks like this:
        #   [  ("resource", {
        #         "uid": ,
        #         "resource-kwargs" : {key-values here go into the spec'd handler __init__}
        #         "spec": "WHAT KIND OF FILE",
        #         "root": the start of the path,
        #         "resource-path": the rest of the path,
        #         "path-semantics": "posix":,
        #         "run-start-id": }
        #      )
        #      ("datum", {
        #       "datum_id": "resource-uuid/datum-identifier",
        #       "resource_id": "resource"
        #       "datum-kwargs": {...}})
        #      ("datum-page", {}) this is in the future
        #   ]
        self._filestore_res = self._asset_docs_cache[-1][-1]

        # this gets automatically turned off at the end
        self.capture.put(1)

        # Xspress3 needs a bit of time to configure itself...
        # this does not play nice with the event loop :/
        ttime.sleep(self.stage_sleep_time)

        return super_stage_result

    def unstage(self):
        try:
            i = 0
            # this needs a fail-safe, RE will now hang forever here
            # as we eat all SIGINT to ensure that cleanup happens in
            # orderly manner.
            # If we are here this is a sign that we have not configured the xs3
            # correctly and it is expecting to capture more points than it
            # was triggered to take.
            while self.capture.get() == 1:
                i += 1
                if (i % 50) == 0:
                    logger.warning("Still capturing data .... waiting.")
                ttime.sleep(0.1)
                if i > 150:
                    logger.warning("Still capturing data .... giving up.")
                    logger.warning(
                        "Check that the xspress3 is configured to take the right "
                        "number of frames "
                        f"(it is trying to take {self.parent.cam.num_images.get()})"
                    )
                    self.capture.put(0)
                    break

        except KeyboardInterrupt:
            self.capture.put(0)
            logger.warning("Still capturing data .... interrupted.")

        return super().unstage()

    def generate_datum(self, key, timestamp, datum_kwargs):
        """Create datum kwargs for one Xspress3 channel following a trigger().

        Parameters
        ----------
        key: str
            Xspress3 channel 'name', for example "det1_channels_channel01"
        timestamp: float
        datum_kwargs: dict

        Returns
        -------
        no return value
        """

        logger.debug("generate_datum() called with key '%s'", key)
        # find the channel corresponding to `key`
        # and create the corresponding datum_kwargs
        # if we do not find a corresponding channel then we have a problem
        for channel in self.parent.iterate_channels():
            if channel.name == key:
                datum_kwargs.update(
                    {
                        "frame": self.parent._abs_trigger_count,
                        "channel": channel.channel_number,
                    }
                )
                self.mds_keys[channel.channel_number] = key
                super().generate_datum(
                    key=key, timestamp=timestamp, datum_kwargs=datum_kwargs
                )
                # we are done
                return
            else:
                pass

        # we have a problem
        # the `key` parameter did not match any of our channels
        raise ValueError(
            f"failed to find channel with name '{key}' "
            f"on Xspress3 detector with PV prefix '{self.parent.prefix}'"
        )

    # JL: is there any reason to keep this?
    def configure(self, total_points=0, master=None, external_trig=False, **kwargs):
        raise NotImplementedError()

    def describe(self):
        spec_desc = {
            "external": "FILESTORE:",
            "dtype": "array",
            # is there a better value than this for shape?
            "shape": (self.width.get(),),
            "source": "FileStore:",
        }

        # # JL: replace with parent.iterate_channels()
        # desc = OrderedDict()
        # for chan in self.channels:
        #     key = self.mds_keys[chan]
        #     desc[key] = spec_desc

        return {
            self.mds_keys[channel.channel_number]: spec_desc
            for channel in self.parent.iterate_channels()
        }


# start new IOC classes
# are these general areadetector plugins?
# for now they are being used just for xspress3
class Mca(ADBase):
    array_data = Cpt(EpicsSignal, "ArrayData")


class McaSum(ADBase):
    array_data = Cpt(EpicsSignal, "ArrayData")


class McaRoi(ADBase):
    roi_name = Cpt(EpicsSignal, "Name")
    min_x = Cpt(EpicsSignal, "MinX")
    size_x = Cpt(EpicsSignal, "SizeX")
    total_rbv = Cpt(EpicsSignalRO, "Total_RBV")

    use = Cpt(SignalWithRBV, "Use")

    mcaroi_prefix_re = re.compile(
        r"MCA(?P<channel_number>\d+)ROI:(?P<mcaroi_number>\d+):"
    )

    def __init__(self, prefix, *args, **kwargs):
        super().__init__(prefix, *args, **kwargs)
        # peel the 'number' off of the prefix
        # the prefix looks like "MCA1ROI:1:"
        # and we want the 1 at the end
        mcaroi_prefix_match = self.mcaroi_prefix_re.search(prefix)
        if mcaroi_prefix_match is None:
            raise ValueError(
                f"mcaroi prefix '{prefix}' does not match the expected pattern `{self.mcaroi_prefix_re.pattern}`"
            )
        self.mcaroi_number = int(mcaroi_prefix_match.group("mcaroi_number"))

    def configure_mcaroi(self, *, min_x, size_x, roi_name=None, use=True):
        """
        Configure the details of an MCAROI.

        Parameters
        ----------
        min_x: int
            the starting bin? for the roi
        size_x: int
            the width in bins? for the roi
        roi_name: str, optional
        use: bool, defaults to True
        """

        logger.debug(
            "configuring Xspress3 MCAROI '%s': name '%s' min_x '%d' size_x '%d' use '%s'",
            self.prefix,
            roi_name,
            min_x,
            size_x,
            use,
        )
        self.min_x.put(int(min_x))
        self.size_x.put(int(size_x))
        if roi_name:
            self.roi_name.put(roi_name)
        self.use.put(use)

    # remove in favor of configure_mcaroi
    def configure_roi(self, ev_min, ev_size):
        """Configure the MCAROI with min and size eV

        Parameters
        ----------
        ev_min : int
            minimum electron volts for ROI
        ev_size : int
            ROI size (width) in electron volts
        """
        ev_min = int(ev_min)
        ev_size = int(ev_size)

        # assume if this ROI is being configured
        # that it should be read, meaning the
        # "use" PV must be set to 1
        use_roi = 1
        configuration_changed = any(
            [
                self.min_x.get() != ev_min,
                self.size_x.get() != ev_size,
                self.use.get() != use_roi,
            ]
        )

        if configuration_changed:
            logger.debug(
                "Setting up Xspress3 ROI: name=%s ev_min=%s ev_size=%s "
                "use=%s prefix=%s channel=%s",
                self.name,
                ev_min,
                ev_size,
                use_roi,
                self.prefix,
                # self.parent is the ?? class
                # self.parent.parent is the ?? class
                # TODO: I don't like the assumption that self has a parent
                self.parent.parent.channel_num,
            )

            self.min_x.put(ev_min)
            self.size_x.put(ev_size)
            self.use.put(use_roi)
        else:
            # nothing has changed
            pass

    def clear(self):
        """Clear and disable this ROI"""
        # it is enough to just disable the ROI
        # self.min_x.put(0)
        # self.size_x.put(0)
        self.use.put(0)


class Sca(ADBase):
    # includes Dead Time correction, for example
    # sca numbers go from 0 to 10
    clock_ticks = Cpt(EpicsSignalRO, "0:Value_RBV")
    reset_ticks = Cpt(EpicsSignalRO, "1:Value_RBV")
    reset_counts = Cpt(EpicsSignalRO, "2:Value_RBV")
    all_event = Cpt(EpicsSignalRO, "3:Value_RBV")
    all_good = Cpt(EpicsSignalRO, "4:Value_RBV")
    window_1 = Cpt(EpicsSignalRO, "5:Value_RBV")
    window_2 = Cpt(EpicsSignalRO, "6:Value_RBV")
    pileup = Cpt(EpicsSignalRO, "7:Value_RBV")
    event_width = Cpt(EpicsSignalRO, "8:Value_RBV")
    dt_factor = Cpt(EpicsSignalRO, "9:Value_RBV")
    dt_percent = Cpt(EpicsSignalRO, "10:Value_RBV")


def _validate_mcaroi_number(mcaroi_number):
    """
    Raise ValueError if the MCAROI number is
     1. not an integer
     2. outside the allowed interval [1,48]

    Parameters
    ----------
    mcaroi_number: could be anything
        MCAROI number candidate

    """
    if not isinstance(mcaroi_number, int):
        raise ValueError(f"MCAROI number '{mcaroi_number}' is not an integer")
    elif not 1 <= mcaroi_number <= 48:
        raise ValueError(
            f"MCAROI number '{mcaroi_number}' is outside the allowed interval [1,48]"
        )
    else:
        # everything is awesome
        pass


def build_channel_class(channel_number, mcaroi_numbers, channel_parent_classes=None):
    """Build an Xspress3 channel class with the specified channel number and MCAROI numbers.

    MCAROI numbers need not be consecutive.

    The complication of using dynamically generated classes
    is the price for the relative ease of including the channel
    number in MCAROI PVs and the ability to specify the number
    of MCAROIs that will be used rather than defaulting to the
    maximum of 48 per channel.

    Parameters
    ----------
    channel_number: int
        the channel number, 1-16
    mcaroi_numbers: Sequence of int
         sequence of MCAROI numbers, not necessarily consecutive, allowed values are 1-48
    channel_parent_classes: list-like, optional
        sequence of all parent classes for the generated channel class,
        by default the only parent is ophyd.areadetector.ADBase

    Returns
    -------
    a dynamically generated class similar to this:
        class GeneratedXspress3Channel(ADBase):
            channel_num = 2
            sca = Cpt(Sca, ...)
            mca = Cpt(Mca, ...)
            mca_sum = Cpt(McaSum, ...)
            mcarois = DDC(...4 McaRois...)

            def get_mcaroi(self, *, number):
                ...
            def iterate_mcarois(self):
                ...
            def clear_all_rois(self):
                ...

    """
    if channel_parent_classes is None:
        channel_parent_classes = tuple([ADBase])

    _validate_channel_number(channel_number=channel_number)

    # create a tuple in case the mcaroi_numbers parameter can be iterated only once
    mcaroi_numbers = tuple([mcaroi_number for mcaroi_number in mcaroi_numbers])
    for mcaroi_number in mcaroi_numbers:
        _validate_mcaroi_number(mcaroi_number=mcaroi_number)

    mcaroi_name_re = re.compile(r"mcaroi\d{2}")

    # the next six functions will become methods of the generated channel class
    def __repr__(self):
        return f"{self.__class__.__name__}(channel_number={self.channel_number}, mcaroi_numbers={self.mcaroi_numbers})"

    def get_mcaroi_count(self):
        return len(mcaroi_numbers)

    def get_mcaroi(self, *, mcaroi_number):
        _validate_mcaroi_number(mcaroi_number=mcaroi_number)
        try:
            return getattr(self.mcarois, f"mcaroi{mcaroi_number:02d}")
        except AttributeError as ae:
            raise ValueError(
                f"no MCAROI on channel {self.channel_number} "
                f"with prefix '{self.prefix}' has number {mcaroi_number}"
            ) from ae

    def iterate_mcaroi_attr_names(self):
        for attr_name in self.mcarois.__dir__():
            if mcaroi_name_re.match(attr_name):
                yield attr_name

    def iterate_mcarois(self):
        """
        Iterate over McaRoi children of the Xspress3Channel.mcarois attribute.

        Yields
        ------
        McaRoi instance
        """
        for mcaroi_name, mcaroi in self.mcarois._signals.items():
            if mcaroi_name_re.match(mcaroi_name):
                yield mcaroi

    def clear_all_rois(self):
        """Clear all MCAROIs"""
        for mcaroi in self.iterate_mcarois():
            mcaroi.clear()

    return type(
        "GeneratedXspress3Channel",
        channel_parent_classes,
        {
            "__repr__": __repr__,
            "channel_number": channel_number,
            "mcaroi_numbers": tuple(sorted(mcaroi_numbers)),
            "sca": Cpt(Sca, f"C{channel_number}SCA:"),
            "mca": Cpt(Mca, f"MCA{channel_number}:"),
            "mca_sum": Cpt(McaSum, f"MCASUM{channel_number}:"),
            "mcarois": DynamicDeviceCpt(
                defn=OrderedDict(
                    {
                        f"mcaroi{mcaroi_i:02d}": (
                            McaRoi,
                            # MCAROI PV suffixes look like "MCA1ROI:2:"
                            f"MCA{channel_number}ROI:{mcaroi_i:d}:",
                            # no keyword parameters
                            dict(),
                        )
                        for mcaroi_i in mcaroi_numbers
                    }
                )
            ),
            "get_mcaroi_count": get_mcaroi_count,
            "get_mcaroi": get_mcaroi,
            "iterate_mcaroi_attr_names": iterate_mcaroi_attr_names,
            "iterate_mcarois": iterate_mcarois,
            "clear_all_rois": clear_all_rois,
        },
    )


def _validate_channel_number(channel_number):
    """
    Raise ValueError if the channel number is
     1. not an integer
     2. outside the allowed interval [1,16]

    Parameters
    ----------
    channel_number: could be anything, but should be int
        channel number candidate

    """
    if not isinstance(channel_number, int):
        raise ValueError(f"channel number '{channel_number}' is not an integer")
    elif not 1 <= channel_number <= 16:
        raise ValueError(
            f"channel number '{channel_number}' is outside the allowed interval [1,16]"
        )
    else:
        # everything is great
        pass


def build_detector_class(
    channel_numbers,
    mcaroi_numbers,
    detector_parent_classes=None,
    extra_class_members=None,
):
    """Build an Xspress3 detector class with the specified channel and roi numbers.

    The complication of using dynamically generated detector classes
    is the price for being able to easily specify the exact number of
    channels and MCAROIs per channel in use on the detector.

    Detector classes generated by build_detector_class include these "soft" PVs
    which are not part of the Xspress3 IOC but are used by Xspress3FileStore:
        external_trig
        total_points
        spectra_per_point
        make_directories
        rewindable

    Parameters
    ----------
    channel_numbers: Sequence of int
        sequence of channel numbers, 1-16, for the detector; for example [1, 2, 3, 8]
    mcaroi_numbers: Sequence of int
        sequence of MCAROI numbers, 1-48, for each channel; for example [1, 2, 3, 10]
    detector_parent_classes: list-like, optional
        sequence of all parent classes for the generated detector class,
        if specified include *all* necessary parent classes; if not specified
        the default parent is ophyd.areadetector.Xspress3Detector
    extra_class_members: Dict[String, Any]
        a dictionary of extra class members to be passed to the builtin type(...)
        function; see the builtin type function for allowed key-value pairs

    Returns
    -------
    a dynamically generated class similar to the following:
        class GeneratedXspress3Detector(Xspress3Detector, SomeMixinClass, ...):
            external_trig = Cpt(Signal, value=False)
            total_points = Cpt(Signal, value=-1)
            spectra_per_point = Cpt(Signal, value=1)
            make_directories = Cpt(Signal, value=False)
            rewindable = Cpt(Signal, value=False)
            channels = DDC(...4 Xspress3Channels with 3 ROIs each...)

            def get_channel_count(self):
                ....
            def get_channel(self, channel_number):
                ....
            def iterate_channels(self):
                ...
    """
    if detector_parent_classes is None:
        detector_parent_classes = tuple([Xspress3Detector])

    if extra_class_members is None:
        extra_class_members = dict()

    # in case channel_numbers can be iterated only once, create a tuple
    channel_numbers = tuple([channel_number for channel_number in channel_numbers])

    # in case mcaroi_numbers can be iterated only once, create a tuple
    mcaroi_numbers = tuple([mcaroi_number for mcaroi_number in mcaroi_numbers])

    channel_attr_name_re = re.compile(r"channel\d{2}")

    # the following four functions will become methods of the generated detector class
    def __repr__(self):
        return f"{self.__class__.__name__}(channels=({','.join([str(channel) for channel in self.iterate_channels()])}))"

    def get_channel_count(self):
        return len(channel_numbers)

    def get_channel(self, *, channel_number):
        _validate_channel_number(channel_number=channel_number)
        try:
            return getattr(self.channels, f"channel{channel_number:02d}")
        except AttributeError as ae:
            raise ValueError(
                f"no channel on detector with prefix '{self.prefix}' "
                f"has number {channel_number}"
            ) from ae

    def iterate_channels(self):
        """
        Iterate over channel objects found on the channels attribute.

        Yields
        ------
        a Channel object
        """

        for channel_attr_name in self.channels.__dir__():
            if channel_attr_name_re.match(channel_attr_name):
                yield getattr(self.channels, channel_attr_name)

    return type(
        "GeneratedXspress3Detector",
        detector_parent_classes,
        dict(
            **{
                "channel_numbers": tuple(sorted(channel_numbers)),
                "external_trig": Cpt(
                    Signal, value=False, doc="Use external triggering"
                ),
                "total_points": Cpt(
                    Signal,
                    value=-1,
                    doc="The total number of points to acquire overall",
                ),
                "spectra_per_point": Cpt(
                    Signal, value=1, doc="Number of spectra per point"
                ),
                "make_directories": Cpt(
                    Signal, value=False, doc="Make directories on the Xspress3 side"
                ),
                "rewindable": Cpt(
                    Signal,
                    value=False,
                    doc="Xspress3 cannot safely be rewound in bluesky",
                ),
                "channels": DynamicDeviceCpt(
                    defn=OrderedDict(
                        {
                            f"channel{c:02d}": (
                                build_channel_class(
                                    channel_number=c, mcaroi_numbers=mcaroi_numbers
                                ),
                                # there is no discrete channel prefix
                                # for the Xspress3 IOC
                                # so specify an empty string here
                                "",
                                # no keyword arguments, so pass an empty dictionary
                                dict(),
                            )
                            for c in channel_numbers
                        }
                    )
                ),
                "__repr__": __repr__,
                "get_channel_count": get_channel_count,
                "get_channel": get_channel,
                "iterate_channels": iterate_channels,
            },
            **extra_class_members,
        ),
    )
