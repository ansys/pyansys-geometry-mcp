# Copyright (C) 2026 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Best-effort guard against orphaned backend processes on Windows.

``ansys-geometry-core`` launches local backends (Discovery, SpaceClaim, the
Geometry Service exe) with a plain ``subprocess.Popen`` call and relies on
``os.kill(pid, SIGTERM)`` for cleanup (see ``ProductInstance.close()``). That
cleanup only runs if this MCP server's own Python process gets a chance to
run its shutdown code. If an MCP client stops the server by force-terminating
the process directly (for example, clicking "stop"/"restart" in an editor's
MCP UI, which on Windows typically maps to ``TerminateProcess`` rather than a
graceful signal), no Python code -- including ``finally`` blocks, ``atexit``
handlers, or signal handlers -- ever runs, and the backend is left running as
an orphan.

Windows Job Objects close this gap at the OS level: assigning the backend's
PID to a job object created with ``JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE``
guarantees the OS terminates that process (and, in the common case, any
children *it* spawns after being assigned, since new child processes inherit
their creator's job membership by default) the moment the job object's last
open handle is closed -- which happens automatically when this process exits,
by any means whatsoever, including a hard external kill.

This is a no-op on non-Windows platforms: an equivalent guarantee there would
require establishing a process group (or ``PR_SET_PDEATHSIG``) at the point
the backend is launched, which is inside ``ansys-geometry-core`` and outside
this package's control.
"""

import ctypes
import sys

from ansys.common.mcp.logging_config import get_logger

logger = get_logger(__name__)

#: Keeps the job object handle(s) alive for the life of this process. If this
#: were allowed to go out of scope, Python could close the handle (and thus
#: kill the guarded process) as soon as the reference is garbage collected.
_job_handles: list[int] = []

# Win32 constants used below (see the Windows SDK's jobapi2.h / winnt.h).
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_PROCESS_TERMINATE = 0x0001
_PROCESS_SET_QUOTA = 0x0100


def _build_extended_limit_information() -> ctypes.Structure:
    """Build a ``JOBOBJECT_EXTENDED_LIMIT_INFORMATION`` struct via ctypes.

    Only ``LimitFlags`` is set (to ``JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE``);
    every other field keeps its zero-initialized default, which Windows
    interprets as "no additional limit".
    """

    class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = (
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", ctypes.c_uint32),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.c_uint32),
            ("Affinity", ctypes.c_void_p),
            ("PriorityClass", ctypes.c_uint32),
            ("SchedulingClass", ctypes.c_uint32),
        )

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = (
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        )

    class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = (
            ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        )

    info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    return info


def guard_process(pid: int) -> bool:
    """Ensure a locally-launched backend process dies with this MCP server.

    Assigns ``pid`` to a new Windows job object configured with
    ``JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE``. The job handle is kept open for
    the remainder of this process's lifetime, so the OS terminates ``pid``
    (even by force) the instant this process exits -- whether that is a
    normal shutdown, a crash, or an external hard kill.

    Parameters
    ----------
    pid : int
        Process ID of the locally-launched backend (for example, the PID
        tracked by ``ansys.geometry.core.connection.product_instance.ProductInstance``).

    Returns
    -------
    bool
        ``True`` if the guard was successfully installed. ``False`` on
        non-Windows platforms, or if any Win32 call failed -- in which case
        a warning is logged and the caller can safely proceed without the
        extra protection (the existing best-effort ``os.kill`` cleanup in
        ``ansys-geometry-core`` is unaffected either way).

    """
    if sys.platform != "win32":
        return False

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            raise ctypes.WinError(ctypes.get_last_error())

        info = _build_extended_limit_information()
        if not kernel32.SetInformationJobObject(
            job,
            _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
            ctypes.byref(info),
            ctypes.sizeof(info),
        ):
            raise ctypes.WinError(ctypes.get_last_error())

        process = kernel32.OpenProcess(_PROCESS_TERMINATE | _PROCESS_SET_QUOTA, False, pid)
        if not process:
            raise ctypes.WinError(ctypes.get_last_error())

        if not kernel32.AssignProcessToJobObject(job, process):
            raise ctypes.WinError(ctypes.get_last_error())

        _job_handles.append(job)
        logger.info(
            f"Backend process {pid} assigned to a Windows job object; it will be "
            "terminated automatically if this MCP server exits unexpectedly."
        )
        return True
    except OSError as e:
        logger.warning(f"Could not guard backend process {pid} against orphaning: {e}")
        return False
