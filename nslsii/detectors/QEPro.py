import logging

from ophyd import (Device, Component as Cpt, FormattedComponent as FC,
                   Signal)
from ophyd import (EpicsSignal, EpicsSignalRO, DeviceStatus, DerivedSignal)
from ophyd.areadetector import EpicsSignalWithRBV as SignalWithRBV

#class QEProTECAtSetPoint(DerivedSignal):
#    def __init__(self, trigger, *, parent=None, **kwargs):
#        trigger = getattr(parent, trigger)
#        super().__init__(derived_from=trigger, parent=parent, **kwargs)
#
#    def inverse(self, value):
#        if abs(value - curr_tec_temp.get()) < .5:
#            return 1
#        else:
#            return 0
#
#    def forward(self, value):
#        return value


class QEPro(Device):
   
    # Device information
    serial = Cpt(EpicsSignal, 'SERIAL')
    model = Cpt(EpicsSignal, 'MODEL')

    # Device Status
    status = Cpt(EpicsSignal, 'STATUS')
    status_msg = Cpt(EpicsSignal, 'STATUS_MSG')
    connected = Cpt(EpicsSignalRO, 'CONNECTED_RBV')

    # Utility signal that periodically checks device temps.
    __check_status = Cpt(EpicsSignal, 'CHECK_STATUS')

    # Bit array outlining which features are supported by the device
    features = Cpt(EpicsSignalRO, 'FEATURES_RBV')
    
    # Togglable features (if supported)
    strobe = Cpt(SignalWithRBV, 'STROBE')
    electric_dark_correction = Cpt(SignalWithRBV, 'EDC')
    non_linearity_correction = Cpt(SignalWithRBV, 'NLC')
    shutter = Cpt(SignalWithRBV, 'SHUTTER')
   
    # Thermal electric cooler settings
    tec = Cpt(SignalWithRBV, 'TEC')
    tec_temp = Cpt(SignalWithRBV, 'TEC_TEMP')
    curr_tec_temp = Cpt(EpicsSignalRO, 'CURR_TEC_TEMP_RBV') 
    
    # Light source feature signals
    light_source = Cpt(SignalWithRBV, 'LIGHT_SOURCE')
    light_source_intensity = Cpt(SignalWithRBV, 'LIGHT_SOURCE_INTENSITY')
    light_source_count = Cpt(EpicsSignalRO, 'LIGHT_SOURCE_COUNT_RBV')

    # Signals for specifying the number of spectra to average and counter for spectra
    # collected in current scan
    num_spectra = Cpt(SignalWithRBV, 'NUM_SPECTRA')
    spectra_collected = Cpt(EpicsSignalRO, 'SPECTRA_COLLECTED_RBV')

    # Integration time settings (in ms)
    int_min_time = Cpt(EpicsSignalRO, 'INT_MIN_TIME_RBV')
    int_max_time = Cpt(EpicsSignalRO, 'INT_MAX_TIME_RBV')
    integration_time = Cpt(SignalWithRBV, 'INTEGRATION_TIME')
    
    # Internal buffer feature settings
    buff_min_capacity = Cpt(EpicsSignalRO, 'BUFF_MIN_CAPACITY_RBV')
    buff_max_capacity = Cpt(EpicsSignalRO, 'BUFF_MAX_CAPACITY_RBV')
    buff_capacity = Cpt(SignalWithRBV, 'BUFF_CAPACITY')
    buff_element_count = Cpt(EpicsSignalRO, 'BUFF_ELEMENT_COUNT_RBV')

    # Formatted Spectra
    spectrum = Cpt(EpicsSignal, 'SPECTRUM')
    dark = Cpt(EpicsSignal, 'DARK')
    reference = Cpt(EpicsSignal, 'REFERENCE')
    
    # Length of spectrum (in pixels)
    formatted_spectrum_len = Cpt(EpicsSignalRO, 'FORMATTED_SPECTRUM_LEN_RBV')

    # X-axis format and array
    x_axis = Cpt(EpicsSignal, 'X_AXIS')
    x_axis_format = Cpt(SignalWithRBV, 'X_AXIS_FORMAT')

    # Dark/Ref available signals
    dark_available = Cpt(EpicsSignalRO, 'DARK_AVAILABLE_RBV')
    ref_available = Cpt(EpicsSignalRO, 'REF_AVAILABLE_RBV')

    # Collection settings and start signals.
    collect = Cpt(SignalWithRBV, 'COLLECT')
    collect_mode = Cpt(SignalWithRBV, 'COLLECT_MODE')
    spectrum_type = Cpt(SignalWithRBV, 'SPECTRUM_TYPE')
    correction = Cpt(SignalWithRBV, 'CORRECTION')
    trigger_mode = Cpt(SignalWithRBV, 'TRIGGER_MODE')


    def __init__(self, prefix, *, )

    @property
    def has_nlc_feature(self):
        return self.features.get() & 32

    @property
    def has_lightsource_feature(self):
        return self.features.get() & 16

    @property
    def has_edc_feature(self):
        return self.features.get() & 8

    @property
    def has_buffer_feature(self):
        return self.features.get() & 4

    @property
    def has_tec_feature(self):
        return self.features.get() & 2

    @property
    def has_irrad_feature(self):
        return self.features.get() & 1


    def get_dark_frame(self):

        self.spectrum_type.put(1)
        self.collect.put(1)
    
    def get_reference_frame(self):

        if self.dark_available.get() == 0:
            return
        self.spectrum_type.put(2)
        self.collect.put(1)


