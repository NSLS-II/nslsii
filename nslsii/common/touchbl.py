import os


def if_touch_beamline(envvar="TOUCHBEAMLINE"):
    value = os.environ.get(envvar, "false").lower()
    if value in ("", "n", "no", "f", "false", "off", "0"):
        return False
    elif value in ("y", "yes", "t", "true", "on", "1"):
        return True
    else:
        raise ValueError(f"Unknown value: {value}")
    