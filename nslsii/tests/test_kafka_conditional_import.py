from unittest.mock import Mock

import nslsii

import IPython.core.interactiveshell


def test_conditional_import():
    """ It is important that nslsii can be imported without bluesky_kafka. """

    # verify `from bluesky_kafka import Publisher` has not been executed yet
    assert "Publisher" not in dir(nslsii)

    ip = IPython.core.interactiveshell.InteractiveShell()
    nslsii.configure_base(
        user_ns=ip.user_ns,
        # a mock databroker will be enough for this test
        broker_name=Mock(),
        bec=False,
        epics_context=False,
        magics=False,
        mpl=False,
        configure_logging=False,
        pbar=False,
        ipython_logging=False,
        # this is the important condition for the test
        publish_documents_to_kafka=False,
    )

    # verify the call to configure_base did not execute `from bluesky_kafka import Publisher`
    assert "Publisher" not in dir(nslsii)
