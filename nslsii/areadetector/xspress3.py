from collections import OrderedDict
import functools
import hashlib
import logging
import re
import time

from ophyd.areadetector import EpicsSignalWithRBV as SignalWithRBV
from ophyd import Signal, EpicsSignal, EpicsSignalRO, DerivedSignal

from ophyd import (
    Component as Cpt,
    FormattedComponent as FC,  # noqa: F401
    DynamicDeviceComponent as DynamicDeviceCpt,
)
from ophyd.areadetector.filestore_mixins import FileStorePluginBase

from ophyd.areadetector.plugins import HDF5Plugin
from ophyd.areadetector import ADBase
from ophyd.areadetector import Xspress3Detector
from ophyd.device import BlueskyInterface, Staged
from ophyd.status import DeviceStatus

from databroker.assets.handlers import (
    Xspress3HDF5Handler,
    # XS3_XRF_DATA_KEY as XRF_DATA_KEY,
)

from ..detectors.utils import makedirs


logger = logging.getLogger(__name__)


# are these used?
#
# def ev_to_bin(ev):
#     """Convert eV to bin number"""
#     return int(ev / 10)
#
#
# def bin_to_ev(bin_):
#     """Convert bin number to eV"""
#     return int(bin_) * 10
#
#
# class EvSignal(DerivedSignal):
#     """A signal that converts a bin number into electron volts"""
#
#     def __init__(self, parent_attr, *, parent=None, **kwargs):
#         bin_signal = getattr(parent, parent_attr)
#         super().__init__(derived_from=bin_signal, parent=parent, **kwargs)
#
#     def get(self, **kwargs):
#         bin_ = super().get(**kwargs)
#         return bin_to_ev(bin_)
#
#     def put(self, ev_value, **kwargs):
#         bin_value = ev_to_bin(ev_value)
#         return super().put(bin_value, **kwargs)
#
#     def describe(self):
#         desc = super().describe()
#         desc[self.name]["units"] = "eV"
#         return desc


class Xspress3FileStore(FileStorePluginBase, HDF5Plugin):
    """Xspress3 acquisition -> filestore"""

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
        mds_key_format="{self.cam.name}_ch{chan}",
        # JL: it seems like parent can not be None
        parent,
        **kwargs,
    ):
        """

        Parameters
        ----------
        basename:
        stage_sleep_time:
        mds_key_format: ???
        parent: Xspress3Detector, required
        kwargs:
        """
        super().__init__(basename, parent=parent, **kwargs)
        # JL removed these in favor of self.parent and self.parent.cam
        # det = parent
        # self.cam = det.cam

        if not isinstance(parent, Xspress3Detector):
            raise TypeError(
                "parent must be an instance of ophyd.areadetector.Xspress3Detector"
            )

        # Use the EpicsSignal file_template from the detector
        self.stage_sigs[self.blocking_callbacks] = 1
        self.stage_sigs[self.enable] = 1
        self.stage_sigs[self.compression] = "zlib"
        self.stage_sigs[self.file_template] = "%s%s_%6.6d.h5"

        self._filestore_res = None

        # JL: generating a list of channel numbers
        # JL: try to replace this with parent.iterate_channels()
        # self.channels = list(
        #     range(
        #         1,
        #         len([_ for _ in parent.component_names if _.startswith("chan")]) + 1)
        # )

        self.stage_sleep_time = stage_sleep_time
        # JL replace the following using parent.iterate_channels()
        # self.mds_keys = {
        #     chan:
        #     mds_key_format.format(
        #         self=self,
        #         chan=chan
        #     )
        #     for chan
        #     in self.channels
        # }
        # JL: what are mds_keys?
        self.mds_keys = {
            channel.channel_number: mds_key_format.format(
                self=self, chan=channel.channel_number
            )
            for channel in parent.iterate_channels()
        }

    def stop(self, success=False):
        ret = super().stop(success=success)
        self.capture.put(0)
        return ret

    def kickoff(self):
        # TODO
        raise NotImplementedError()

    def collect(self):
        # TODO (hxn-specific implementation elsewhere)
        raise NotImplementedError()

    def make_filename(self):
        fn, rp, write_path = super().make_filename()
        if self.parent.make_directories.get():
            makedirs(write_path)
        return fn, rp, write_path

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
                time.sleep(0.1)
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
        """
        Parameters
        ----------
        key: str
            Xspress3 channel attribute path, for example:
              "det1.channels.channel01"
        timestamp: float
        datum_kwargs: dict-like

        Returns
        -------
        """
        # # JL: replace the following using parent.iterate_channels()
        # sn, n = next(
        #     (f"channel{j}", j)
        #     for j in self.channels
        #     if getattr(
        #         self.parent,    # detector
        #         f"channel{j}"   # channel1, channel2, ...
        #     ).name == key       # detector.channel1.name
        # )
        #
        # # JL: replace the following
        # datum_kwargs.update(
        #     {
        #         "frame": self.parent._abs_trigger_count,
        #         "channel": int(sn[7:])  # channel1
        #     }                           # 01234567
        # )
        #
        # # JL: replace these two lines
        # self.mds_keys[n] = key
        # super().generate_datum(key, timestamp, datum_kwargs)

        # if we do not find the channel corresponding to
        # the 'key' parameter then we have a problem
        for channel in self.parent.iterate_channels():
            if channel.name == key:
                datum_kwargs.update(
                    {
                        "frame": self.parent._abs_trigger_count,  # JL: what?
                        "channel": channel.channel_number,
                    }
                )
                self.mds_keys[channel.channel_number] = key
                return super().generate_datum(
                    key=key, timestamp=timestamp, datum_kwargs=datum_kwargs
                )

        # we have a problem
        raise ValueError(
            f"failed to find '{key}' on Xspress3 detector with PV prefix {self.parent.prefix}"
        )

    def stage(self):
        logger.debug("Stopping acquisition for xspress3 '%s'", self.parent.prefix)
        # really force it to stop acquiring
        self.parent.cam.acquire.put(0, wait=True)

        total_points_reading = self.parent.total_points.get()
        if total_points_reading < 1:
            raise RuntimeError(
                f"You must set total_points for Xspress3 {self.parent.prefix}"
            )
        spectra_per_point_reading = self.parent.spectra_per_point.get()
        total_capture = total_points_reading * spectra_per_point_reading

        # stop previous acquisition
        self.stage_sigs[self.parent.cam.acquire] = 0

        # re-order the stage signals and disable the calc record which is
        # interfering with the capture count
        self.stage_sigs.pop(self.num_capture, None)
        self.stage_sigs.pop(self.parent.cam.num_images, None)
        self.stage_sigs[self.num_capture_calc_disable] = 1

        # if should external trigger
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
            # JL: this looks wrong - why not total_capture as above?
            self.stage_sigs[self.parent.cam.num_images] = spectra_per_point_reading

        self.stage_sigs[self.auto_save] = "No"

        filename, read_path, write_path = self.make_filename()
        logger.debug(
            "read path: '%s' write path: '%s' filename: '%s'",
            read_path,
            write_path,
            filename,
        )

        logger.debug("Erasing old spectra")
        self.parent.cam.erase.put(1, wait=True)

        # this must be set after self.parent.cam.num_images because at the EPICS
        # layer there is a helpful link that sets this equal to that (but
        # not the other way)
        # JL: hoping num_capture does not exist on the new IOC
        self.stage_sigs[self.num_capture] = total_capture

        # apply the stage_sigs values
        super_stage_result = super().stage()

        self._fn = self.file_template.get() % (
            self._fp,
            self.file_name.get(),
            self.file_number.get(),
        )

        if not self.file_path_exists.get():
            raise IOError(f"Path {self.file_path.get()} does not exits on IOC")

        logger.debug("Inserting the filestore resource: %s", self._fn)
        self._generate_resource({})
        # JL: the last element of the last element of self._asset_docs_cache
        #     is the "resource"?
        self._filestore_res = self._asset_docs_cache[-1][-1]

        # this gets automatically turned off at the end
        self.capture.put(1)

        # Xspress3 needs a bit of time to configure itself...
        # this does not play nice with the event loop :/
        # JL: does the new IOC need this?
        time.sleep(self.stage_sleep_time)

        return super_stage_result

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


# moved this into the build_channel_class function
# class Xspress3ChannelBase(ADBase):
#     """"""
#
#     roi_name_format = "Det{self.channel_number}_{roi_name}"
#     roi_total_name_format = "Det{self.channel_number}_{roi_name}_total"
#
#     def __init__(self, prefix, *args, **kwargs):
#         super().__init__(prefix, *args, **kwargs)
#
#     #
#     # instead use channels.channelNN.get_mcaroi().configure_roi(...)
#     #
#     # def set_roi(self, index_or_roi, *, ev_min, ev_size, name=None):
#     #     """Configure MCAROI with energy range and optionally name.
#     #
#     #     Parameters
#     #     ----------
#     #     index_or_roi : int
#     #         The roi index or instance to set
#     #     ev_min : int
#     #         low eV setting
#     #     ev_size : int
#     #         roi width eV setting
#     #     name : str, optional
#     #         The unformatted ROI name to set. Each channel specifies its own
#     #         `roi_name_format` and `roi_sum_name_format` in which the name
#     #         parameter will get expanded.
#     #     """
#     #     if isinstance(index_or_roi, McaRoi):
#     #         roi = index_or_roi
#     #     else:
#     #         if index_or_roi <= 0:
#     #             raise ValueError("MCAROI index starts from 1")
#     #         roi = getattr(self.mcarois, f"mcaroi{index_or_roi:02d}")
#     #
#     #     roi.configure_roi(ev_min, ev_size)
#     #
#     #     if name is not None:
#     #         roi_name = self.roi_name_format.format(self=self, roi_name=name)
#     #         roi.roi_name.name = roi_name
#     #         roi.total_rbv.name = self.roi_total_name_format.format(
#     #             self=self, roi_name=roi_name
#     #         )
#     #         # apply the ophyd name to the PV roi_name
#     #         # this is new behavior
#     #         roi.roi_name.put(roi_name)
#
#     # def clear_all_rois(self):
#     #     """Clear all ROIs"""
#     #     for mcaroi in self.iterate_mcarois():
#     #         mcaroi.clear()


def _validate_mcaroi_numbers(mcaroi_numbers):
    """
    Raise ValueError if any MCAROI number is
     1. not an integer
     2. outside the allowed interval [1,48]

    Parameters
    ----------
    mcaroi_numbers: Sequence
        MCAROI number candidates

    """
    non_integer_values = [
        mcaroi_number
        for mcaroi_number in mcaroi_numbers
        if not isinstance(mcaroi_number, int)
    ]
    if len(non_integer_values) > 0:
        raise ValueError(
            f"MCAROI numbers include non-integer values: {non_integer_values}"
        )

    out_of_bounds_numbers = [
        mcaroi_number
        for mcaroi_number in mcaroi_numbers
        if not 1 <= mcaroi_number <= 48
    ]
    if len(out_of_bounds_numbers) > 0:
        raise ValueError(
            f"MCAROI numbers {out_of_bounds_numbers} are outside the allowed interval [1,48]"
        )


# cache returned class objects to avoid
# building redundant classes
@functools.lru_cache(100)
def build_channel_class(channel_number, mcaroi_numbers, channel_parent_classes=None):
    """Build an Xspress3 channel class with the specified channel number and MCAROI numbers.

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
         sequence of MCAROI numbers, allowed values are 1-48
    channel_parent_classes: list-like, optional
        sequence of all parent classes for the generated channel class,
        by default the only parent is ophyd.areadetector.ADBase

    Returns
    -------
    a dynamically generated class similar to this:
        class GeneratedXspress3Channel_94e52ec5(ADBase):
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

    _validate_channel_numbers(channel_numbers=(channel_number,))

    # create a tuple in case the mcaroi_numbers parameter can be iterated only once
    mcaroi_numbers = tuple([mcaroi_number for mcaroi_number in mcaroi_numbers])
    _validate_mcaroi_numbers(mcaroi_numbers)

    mcaroi_name_re = re.compile(r"mcaroi\d{2}")

    def get_mcaroi(self, *, number):
        _validate_mcaroi_numbers((number,))
        try:
            return getattr(self.mcarois, f"mcaroi{number:02d}")
        except AttributeError as ae:
            raise ValueError(
                f"no MCAROI on channel {self.channel_number} "
                f"with prefix '{self.prefix}' has number {number}"
            ) from ae

    # this function will become a method of the generated channel class
    def iterate_mcarois(self):
        """
        Iterate over McaRoi children of the Xspress3Channel.mcarois attribute.

        Yields
        ------
        mcaroi name, McaRoi instance
        """
        for mcaroi_name, mcaroi in self.mcarois._signals.items():
            if mcaroi_name_re.match(mcaroi_name):
                yield mcaroi_name, mcaroi

    def clear_all_rois(self):
        """Clear all MCAROIs"""
        for mcaroi in self.iterate_mcarois():
            mcaroi.clear()

    # rather than build the mcaroi numbers directly in to the name of the
    # generated class use shake.hexdigest(4) for a short, unique-ish, reproducible
    # class name suffix based on all the parameters used to generate the channel class
    shake = hashlib.shake_128()
    shake.update(f"{channel_number}+{mcaroi_numbers}+{channel_parent_classes}".encode())
    channel_class_suffix = shake.hexdigest(4)

    return type(
        f"GeneratedXspress3Channel_{channel_class_suffix}",
        channel_parent_classes,
        {
            "channel_number": channel_number,
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
            "get_mcaroi": get_mcaroi,
            "iterate_mcarois": iterate_mcarois,
            "clear_all_rois": clear_all_rois,
        },
    )


def _validate_channel_numbers(channel_numbers):
    """
    Raise ValueError if any channel number is
     1. not an integer
     2. outside the allowed interval [1,16]

    Parameters
    ----------
    channel_numbers: Sequence
        channel number candidates

    """
    non_integer_values = [
        channel_number
        for channel_number in channel_numbers
        if not isinstance(channel_number, int)
    ]
    if len(non_integer_values) > 0:
        raise ValueError(f"channel number(s) {non_integer_values} are not integers")

    out_of_bounds_numbers = [
        channel_number
        for channel_number in channel_numbers
        if not 1 <= channel_number <= 16
    ]
    if len(out_of_bounds_numbers) > 0:
        raise ValueError(
            f"channel number(s) {out_of_bounds_numbers} are outside the allowed interval [1,16]"
        )


# cache returned class objects to
# avoid building redundant classes
@functools.lru_cache(100)
def build_detector_class(channel_numbers, mcaroi_numbers, detector_parent_classes=None):
    """Build an Xspress3 detector class with the specified channel and roi numbers.

    The complication of using dynamically generated detector classes
    is the price for being able to easily specify the exact number of
    channels and ROIs per channel present on the detector.

    Detector classes generated by this function include these "soft" signals
    which are not part of the Xspress3 IOC but are used by Xspress3FileStore:
        external_trig
        total_points
        spectra_per_point
        make_directories
        rewindable

    Parameters
    ----------
    channel_numbers: Sequence of int
        sequence of channel numbers for the detector, 1-16
    mcaroi_numbers: Sequence of int
        sequence of MCAROI numbers for each channel, 1-48
    detector_parent_classes: list-like, optional
        in addition to ophyd.areadetector.Xspress3Detector these
        classes will be parents of the generated detector class

    Returns
    -------
    a dynamically generated class similar to this:
        class GeneratedXspress3Detector_83d41db4(Xspress3Detector, SomeMixinClass, ...):
            external_trig = Cpt(Signal, value=False)
            total_points = Cpt(Signal, value=-1)
            spectra_per_point = Cpt(Signal, value=1)
            make_directories = Cpt(Signal, value=False)
            rewindable = Cpt(Signal, value=False)
            channels = DDC(...4 Xspress3Channels with 3 ROIs each...)

            def iterate_channels(self):
                ...
    """
    if detector_parent_classes is None:
        detector_parent_classes = tuple()

    # in case channel_numbers can be iterated only once, create a tuple
    channel_numbers = tuple([channel_number for channel_number in channel_numbers])

    # in case the mcaroi_numbers parameter can be iterated only once, create a tuple
    mcaroi_numbers = tuple([mcaroi_number for mcaroi_number in mcaroi_numbers])

    channel_name_re = re.compile(r"channel_\d{1,2}")

    # this function will become a method of the generated detector class
    def iterate_channels(self):
        """
        Iterate over channel objects found on the channels attribute.

        Yields
        ------
        Channel object name, Channel object
        """
        for signal_name, signal in self.channels._signals.items():
            if channel_name_re.match(signal_name):
                yield signal_name, signal

    # rather than build the channel numbers and mcaroi numbers directly in to
    # the name of the generated class use shake.hexdigest(4) for a short, unique-ish,
    # reproducible class name suffix based on all the parameters used to generate
    # the detector class
    shaker = hashlib.shake_128()
    shaker.update(
        f"{channel_numbers}+{mcaroi_numbers}+{detector_parent_classes}".encode()
    )
    detector_class_suffix = shaker.hexdigest(4)

    return type(
        f"GeneratedXspress3Detector_{detector_class_suffix}",
        (Xspress3Detector, *detector_parent_classes),
        {
            "external_trig": Cpt(Signal, value=False, doc="Use external triggering"),
            "total_points": Cpt(
                Signal, value=-1, doc="The total number of points to acquire overall"
            ),
            "spectra_per_point": Cpt(
                Signal, value=1, doc="Number of spectra per point"
            ),
            "make_directories": Cpt(
                Signal, value=False, doc="Make directories on the DAQ side"
            ),
            "rewindable": Cpt(
                Signal, value=False, doc="Xspress3 cannot safely be rewound in bluesky"
            ),
            "channels": DynamicDeviceCpt(
                defn=OrderedDict(
                    {
                        f"channel_{c}": (
                            build_channel_class(
                                channel_number=c, mcaroi_numbers=mcaroi_numbers
                            ),
                            # there is no discrete Xspress3 channel prefix
                            # so specify an empty string here
                            "",
                            dict(),
                        )
                        for c in channel_numbers
                    }
                )
            ),
            "iterate_channels": iterate_channels,
        },
    )


# end new IOC classes


class XspressTrigger(BlueskyInterface):
    """Base class for trigger mixin classes

    Subclasses must define a method with this signature:

    `acquire_changed(self, value=None, old_value=None, **kwargs)`
    """

    # TODO **
    # count_time = self.cam.acquire_period

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # settings
        self._status = None
        self._acquisition_signal = self.cam.acquire
        self._abs_trigger_count = 0

    def stage(self):
        self._abs_trigger_count = 0
        self._acquisition_signal.subscribe(self._acquire_changed)
        return super().stage()

    def unstage(self):
        ret = super().unstage()
        self._acquisition_signal.clear_sub(self._acquire_changed)
        self._status = None
        return ret

    def _acquire_changed(self, value=None, old_value=None, **kwargs):
        "This is called when the 'acquire' signal changes."
        if self._status is None:
            return
        if (old_value == 1) and (value == 0):
            # Negative-going edge means an acquisition just finished.
            self._status._finished()

    def trigger(self):
        if self._staged != Staged.yes:
            raise RuntimeError("not staged")

        self._status = DeviceStatus(self)
        self._acquisition_signal.put(1, wait=False)
        trigger_time = time.time()

        for sn in self.read_attrs:
            if sn.startswith("channel") and "." not in sn:
                ch = getattr(self, sn)
                self.dispatch(ch.name, trigger_time)

        self._abs_trigger_count += 1
        return self._status
