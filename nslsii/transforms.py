# DataBroker "transforms" for patching up documents
# on their way out.
import copy


def remove_zeros(shape):
    """
    Remove any zeroes from the shape.
    """
    return [dim for dim in shape if dim!=0]


def swap_dim1_dim2(shape):
    """
    Swap the first two dimensions of the shape.
    """
    shape[0], shape[1] = shape[1], shape[0]
    return shape


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


def rsoxs_fix_shape(descriptor):
    """
    Fix an RSOXS Event Descriptor.
    """
    descriptor = copy.deepcopy(descriptor)
    for key, value in descriptor['data_keys'].items():
        shape = descriptor['data_keys'][key]['shape']
        if shape:
            shape = remove_zeros(shape)
            descriptor['data_keys'][key]['shape'] = (1, *shape)

    return descriptor


