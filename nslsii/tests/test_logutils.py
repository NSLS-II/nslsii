import os
from pathlib import Path
from unittest.mock import MagicMock

import IPython.core.interactiveshell

from nslsii import configure_ipython_exc_logging
from nslsii.common.ipynb.logutils import log_exception


def test_log_exception():
    ip = IPython.core.interactiveshell.InteractiveShell()
    ip.logger = MagicMock()
    ip.set_custom_exc((BaseException, ), log_exception)
    ip.run_cell("raise Exception")
    ip.logger.log_write.assert_called_with("Exception\n", kind="output")


def test_configure_ipython_exc_logging(tmpdir):
    log_file_path = Path(tmpdir) / Path("bluesky_ipython.log")

    ip = IPython.core.interactiveshell.InteractiveShell()
    os.environ["BLUESKY_IPYTHON_LOG_FILE"] = str(log_file_path)
    bluesky_ipython_log_file_path = configure_ipython_exc_logging(
        exception_logger=log_exception,
        ipython=ip,
    )
    assert bluesky_ipython_log_file_path == str(log_file_path)
    assert log_file_path.exists()


def test_configure_ipython_exc_logging_file_exists(tmpdir):
    log_file_path = Path(tmpdir) / Path("bluesky_ipython.log")

    with open(log_file_path, "w") as f:
        f.write("log log log")

    ip = IPython.core.interactiveshell.InteractiveShell()
    os.environ["BLUESKY_IPYTHON_LOG_FILE"] = str(log_file_path)
    bluesky_ipython_log_file_path = configure_ipython_exc_logging(
        exception_logger=log_exception,
        ipython=ip,
    )
    assert bluesky_ipython_log_file_path == str(log_file_path)
    assert log_file_path.exists()


def test_configure_ipython_exc_logging_rotate(tmpdir):
    log_file_path = Path(tmpdir) / Path("bluesky_ipython.log")

    with open(log_file_path, "w") as f:
        f.write("log log log")

    ip = IPython.core.interactiveshell.InteractiveShell()
    os.environ["BLUESKY_IPYTHON_LOG_FILE"] = str(log_file_path)
    bluesky_ipython_log_file_path = configure_ipython_exc_logging(
        exception_logger=log_exception,
        ipython=ip,
        rotate_file_size=0
    )
    assert bluesky_ipython_log_file_path == str(log_file_path)
    assert log_file_path.exists()

    old_log_file_path = log_file_path.parent / Path(log_file_path.name + ".old")
    assert old_log_file_path.exists()
