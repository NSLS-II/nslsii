import argparse
import socket
from socket import gaierror, herror

from caproto.threading.client import Context


def get_ioc_hostname(pvname):
    """A helper function to get the IOC hostname based on the provided PV."""

    ctx = Context()
    (pv,) = ctx.get_pvs(pvname)
    pv.wait_for_connection()
    s = pv.circuit_manager.socket

    epics_addr = s.getpeername()[0]
    sci_addr = epics_addr.split(".")
    sci_addr[2] = str(int(sci_addr[2]) - 3)
    sci_addr = ".".join(sci_addr)

    try:
        hostname = socket.gethostbyaddr(sci_addr)[0]
    except (gaierror, herror):
        hostname = socket.gethostbyaddr(epics_addr)[0]

    return hostname


def main():
    # Used by the `sync-experiment` command

    parser = argparse.ArgumentParser(description="Get the IOC hostname based on the provided PV")
    parser.add_argument("-p", "--pv", dest="pvname", type=str, help="PV to query information about", required=True)

    args = parser.parse_args()
    hostname = get_ioc_hostname(args.pvname)
    print(f"IOC hostname for '{args.pvname}' is '{hostname}'.")
