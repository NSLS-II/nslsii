from unittest.mock import MagicMock

import IPython.core.interactiveshell

from nslsii.common.ipynb.logutils import log_exception


def test_log_exception():
    ip = IPython.core.interactiveshell.InteractiveShell()
    ip.logger = MagicMock()
    ip.set_custom_exc((BaseException, ), log_exception)
    ip.run_cell("raise Exception")
    ip.logger.log_write.assert_called_with("Exception\n", kind="output")
