# DataBroker "transforms" for patching up documents
# on their way out.
import copy


def csx_fix_scaler_shape(d):
    """
    Transform an Event Descriptor.

    Look for sources that match the pattern of a Scaler.
    Ensure that their shape is [].
    """
    d = copy.deepcopy(d)
    for k, v in list(d['data_keys'].items()):
        if v['source'].startswith('PV:XF:23ID1-ES{Sclr:1}Wfrm'):
            d['data_keys'][k]['shape'] = []
    return d
