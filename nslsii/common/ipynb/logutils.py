import traceback


def log_exception(ipyshell, etype, evalue, tb, tb_offset=None):
    """A custom IPython exception handler that logs exception tracebacks to
    the IPython log file.

    References:
        https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.interactiveshell.html
        https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.logger.html

    Usage:
        from nslsii.common.ipynb.logutils import log_exception
        get_ipython().set_custom_exc((BaseException, ), log_exception)

        %logstart -o -t ipython_log/beamline.log rotate

    Parameters
    ----------
    ipyshell : TerminalInteractiveShell

    etype : type of evalue

    evalue : BaseException

    tb : traceback

    tb_offset : ???

    Returns
    -------
    list of traceback lines
    """
    tb_lines = traceback.format_exception(etype, evalue, tb)
    for tb_line in tb_lines:
        ipyshell.logger.log_write(tb_line, kind="output")
    ipyshell.showtraceback((etype, evalue, tb), tb_offset=tb_offset)

    return tb_lines
