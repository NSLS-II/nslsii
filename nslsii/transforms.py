# DataBroker "transforms" for patching up documents
# on their way out.
import copy


def fix_csx_scaler_shape(d)
    d = copy.deepcopy(d)
    for k, v in list(d['data_keys'].items()):
        if v['source'].startswith('PV:XF:23ID1-ES{Sclr:1}Wfrm'):
            d['data_keys'][k]['shape'] = []
    return d
