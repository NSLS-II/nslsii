import os
from pathlib import Path
import stat
from unittest.mock import MagicMock

import appdirs
import IPython.core.interactiveshell
import pytest

from nslsii import configure_bluesky_logging, configure_ipython_logging
from nslsii.common.ipynb.logutils import log_exception


def test_configure_bluesky_logging(tmpdir):
    """
    Set environment variable BLUESKY_LOG_FILE and assert the log
    file is created.
    """
    log_file_path = Path(tmpdir) / Path("bluesky.log")

    ip = IPython.core.interactiveshell.InteractiveShell()
    os.environ["BLUESKY_LOG_FILE"] = str(log_file_path)
    bluesky_log_file_path = configure_bluesky_logging(ipython=ip,)
    assert bluesky_log_file_path == log_file_path
    assert log_file_path.exists()


def test_configure_bluesky_logging_with_nonexisting_dir(tmpdir):
    """
    Set environment variable BLUESKY_LOG_FILE to include a directory
    that does not exist. Assert an exception is raised.
    """
    log_dir = Path(tmpdir) / Path("does_not_exist")
    log_file_path = log_dir / Path("bluesky.log")

    ip = IPython.core.interactiveshell.InteractiveShell()
    os.environ["BLUESKY_LOG_FILE"] = str(log_file_path)
    with pytest.raises(FileNotFoundError):
        configure_bluesky_logging(ipython=ip,)


def test_configure_bluesky_logging_with_unwriteable_dir(tmpdir):
    """
    Set environment variable BLUESKY_LOG_FILE to include a directory
    that is not writeable. Assert an exception is raised.
    """

    log_dir = Path(tmpdir)
    log_file_path = log_dir / Path("bluesky.log")

    # make the log_dir read-only to force an exception
    log_dir.chmod(mode=stat.S_IREAD)

    ip = IPython.core.interactiveshell.InteractiveShell()
    os.environ["BLUESKY_LOG_FILE"] = str(log_file_path)
    with pytest.raises(PermissionError):
        configure_bluesky_logging(ipython=ip,)


def test_default_bluesky_logging():
    """
    Remove environment variable BLUESKY_LOG_FILE and test that
    the default log file path is used. This test creates a
    directory rather than using pytest's tmp_path so the test
    must clean up at the end.
    """
    test_appname = "bluesky-test"
    user_log_dir = Path(appdirs.user_log_dir(appname=test_appname))

    # log directory must exist
    # nslsii.configure_bluesky_logging() will not create it
    user_log_dir.mkdir(parents=True)

    log_file_path = Path(appdirs.user_log_dir(appname=test_appname)) / Path(
        "bluesky.log"
    )

    ip = IPython.core.interactiveshell.InteractiveShell()
    os.environ.pop("BLUESKY_LOG_FILE", default=None)

    bluesky_log_file_path = configure_bluesky_logging(
        ipython=ip, appdirs_appname=test_appname
    )
    assert bluesky_log_file_path == log_file_path
    assert log_file_path.exists()

    # clean up the file and directory this test creates
    bluesky_log_file_path.unlink()
    bluesky_log_file_path.parent.rmdir()


def test_ipython_log_exception():
    ip = IPython.core.interactiveshell.InteractiveShell()
    ip.logger = MagicMock()
    ip.set_custom_exc((BaseException,), log_exception)
    ip.run_cell("raise Exception")
    ip.logger.log_write.assert_called_with("Exception\n", kind="output")


def test_default_ipython_exc_logging():
    test_appname = "bluesky-test"
    log_dir = Path(appdirs.user_log_dir(appname=test_appname))
    log_file_path = log_dir / Path("bluesky_ipython.log")

    # the log directory must exist already
    # nslsii.configure_ipython_exc_logging() will not create it
    log_dir.mkdir(parents=True)

    ip = IPython.core.interactiveshell.InteractiveShell()
    os.environ.pop("BLUESKY_IPYTHON_LOG_FILE", default=None)
    bluesky_ipython_log_file_path = configure_ipython_logging(
        exception_logger=log_exception, ipython=ip, appdirs_appname=test_appname
    )

    assert bluesky_ipython_log_file_path == log_file_path
    assert log_file_path.exists()

    bluesky_ipython_log_file_path.unlink()
    bluesky_ipython_log_file_path.parent.rmdir()


def test_configure_ipython_exc_logging(tmpdir):
    log_file_path = Path(tmpdir) / Path("bluesky_ipython.log")

    ip = IPython.core.interactiveshell.InteractiveShell()
    os.environ["BLUESKY_IPYTHON_LOG_FILE"] = str(log_file_path)
    bluesky_ipython_log_file_path = configure_ipython_logging(
        exception_logger=log_exception, ipython=ip,
    )
    assert bluesky_ipython_log_file_path == log_file_path
    assert log_file_path.exists()


def test_configure_ipython_exc_logging_with_nonexisting_dir(tmpdir):
    log_dir = Path(tmpdir) / Path("does_not_exist")
    log_file_path = log_dir / Path("bluesky_ipython.log")

    ip = IPython.core.interactiveshell.InteractiveShell()
    os.environ["BLUESKY_IPYTHON_LOG_FILE"] = str(log_file_path)
    with pytest.raises(UserWarning):
        configure_ipython_logging(
            exception_logger=log_exception, ipython=ip,
        )


def test_configure_ipython_exc_logging_with_unwriteable_dir(tmpdir):
    log_dir = Path(tmpdir)
    log_file_path = log_dir / Path("bluesky_ipython.log")

    log_dir.chmod(stat.S_IREAD)

    ip = IPython.core.interactiveshell.InteractiveShell()
    os.environ["BLUESKY_IPYTHON_LOG_FILE"] = str(log_file_path)
    with pytest.raises(PermissionError):
        configure_ipython_logging(
            exception_logger=log_exception, ipython=ip,
        )


def test_configure_ipython_exc_logging_file_exists(tmpdir):
    log_file_path = Path(tmpdir) / Path("bluesky_ipython.log")

    with open(log_file_path, "w") as f:
        f.write("log log log")

    ip = IPython.core.interactiveshell.InteractiveShell()
    os.environ["BLUESKY_IPYTHON_LOG_FILE"] = str(log_file_path)
    bluesky_ipython_log_file_path = configure_ipython_logging(
        exception_logger=log_exception, ipython=ip,
    )
    assert bluesky_ipython_log_file_path == log_file_path
    assert log_file_path.exists()


def test_configure_ipython_exc_logging_rotate(tmpdir):
    log_file_path = Path(tmpdir) / Path("bluesky_ipython.log")

    with open(log_file_path, "w") as f:
        f.write("log log log")

    ip = IPython.core.interactiveshell.InteractiveShell()
    os.environ["BLUESKY_IPYTHON_LOG_FILE"] = str(log_file_path)
    bluesky_ipython_log_file_path = configure_ipython_logging(
        exception_logger=log_exception, ipython=ip, rotate_file_size=0
    )
    assert bluesky_ipython_log_file_path == log_file_path
    assert log_file_path.exists()

    old_log_file_path = log_file_path.parent / Path(log_file_path.name + ".old")
    assert old_log_file_path.exists()
