def test_ipynb():
    from nslsii.common import ipynb
    obj = ipynb.get_sys_info()
    obj.data
    obj.filename
    obj.metadata
    obj.url
    obj.reload()

def test_touchbl():
    from nslsii.common import if_touch_beamline
    if if_touch_beamline():
        pass