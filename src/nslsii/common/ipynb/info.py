from __future__ import annotations

import platform
import sys

import psutil
from IPython.display import HTML


def get_sys_info():
    """Display info on system and output as nice HTML"""
    html = f"<h3>System Information for {platform.node()}</h3>"
    html += "<table>"

    html += '<tr><td align="left">Python Executable</td>'
    html += f"<td>{sys.executable}</td></tr>"
    html += f"<tr><td>Kernel PID</td><td>{psutil.Process().pid}</td></tr>"

    mem = psutil.virtual_memory()
    html += "<tr><td>Total System Memory</td>"
    html += f"<td>{mem.total / 1024**3:.4} Mb</td></td>"
    html += "<tr><td>Total Memory Used</td>"
    html += f"<td>{mem.used / 1024**3:.4} Mb</td></td>"
    html += "<tr><td>Total Memory Free</td>"
    html += f"<td>{mem.free / 1024**3:.4} Mb</td></td>"

    html += f"<tr><td>Number of CPU Cores</td><td>{psutil.cpu_count()}</td></tr>"
    html += (
        f"<tr><td>Current CPU Load</td><td>{psutil.cpu_percent(1, False)} %</td></tr>"
    )

    html += "</table>"
    return HTML(html)


def show_kernels():
    """Show all IPython Kernels on System"""

    total_mem = psutil.virtual_memory().total

    html = (
        f"<h3>IPython Notebook Processes on {platform.node()}</h3>"
        "<table><tr>"
        "<th>Username</th><th>PID</th><th>CPU Usage</th>"
        "<th>Process Memory</th><th>System Memory Used</th><th>Status</th>"
        "</tr>"
    )

    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(
                attrs=["pid", "username", "cmdline", "memory_info", "status"]
            )
        except psutil.NoSuchProcess:
            pass
        else:
            if any(
                x in pinfo["cmdline"] for x in ["IPython.kernel", "ipykernel_launcher"]
            ):
                html += "<tr>"
                html += "<td>{username}</td><td>{pid}</td>".format(**pinfo)
                p = psutil.Process(pinfo["pid"]).cpu_percent(0.1)
                html += f"<td>{p}%</td>"
                html += "<td>{:.4} Mb</td>".format(pinfo["memory_info"].vms / 1024**3)
                html += "<td>{:.3}%</td>".format(
                    100 * pinfo["memory_info"].vms / total_mem
                )
                html += "<td>{}</td>".format(pinfo["status"])
                html += "</tr>"

    html += "</table>"
    return HTML(html)
