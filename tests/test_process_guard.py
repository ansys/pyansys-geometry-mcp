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

"""Tests for ``ansys.geometry.mcp._process_guard``.

The Win32 calls are mocked throughout -- these tests exercise the guard's
control flow (constant values, call ordering, error handling) rather than
real OS behavior, so they run identically on any platform.
"""

from unittest.mock import MagicMock

from ansys.geometry.mcp import _process_guard


def test_non_windows_is_a_no_op(mocker):
    """On non-Windows platforms, guard_process returns False without touching ctypes."""
    mocker.patch.object(_process_guard.sys, "platform", "linux")
    win_dll = mocker.patch.object(_process_guard.ctypes, "WinDLL", create=True)

    result = _process_guard.guard_process(1234)

    assert result is False
    win_dll.assert_not_called()


def test_successful_guard_assigns_process_to_job(mocker):
    """A successful guard calls the four Win32 APIs in order and keeps the handle alive."""
    mocker.patch.object(_process_guard.sys, "platform", "win32")
    kernel32 = MagicMock()
    kernel32.CreateJobObjectW.return_value = 111  # job handle
    kernel32.SetInformationJobObject.return_value = 1  # nonzero == success
    kernel32.OpenProcess.return_value = 222  # process handle
    kernel32.AssignProcessToJobObject.return_value = 1  # nonzero == success
    mocker.patch.object(_process_guard.ctypes, "WinDLL", return_value=kernel32, create=True)
    mocker.patch.object(_process_guard, "_job_handles", [])

    result = _process_guard.guard_process(4321)

    assert result is True
    kernel32.CreateJobObjectW.assert_called_once_with(None, None)
    kernel32.SetInformationJobObject.assert_called_once()
    kernel32.OpenProcess.assert_called_once_with(
        _process_guard._PROCESS_TERMINATE | _process_guard._PROCESS_SET_QUOTA, False, 4321
    )
    kernel32.AssignProcessToJobObject.assert_called_once_with(111, 222)
    assert _process_guard._job_handles == [111]


def test_create_job_object_failure_returns_false(mocker):
    """If CreateJobObjectW fails (returns falsy), the guard returns False and logs a warning."""
    mocker.patch.object(_process_guard.sys, "platform", "win32")
    kernel32 = MagicMock()
    kernel32.CreateJobObjectW.return_value = 0
    mocker.patch.object(_process_guard.ctypes, "WinDLL", return_value=kernel32, create=True)
    mocker.patch.object(_process_guard.ctypes, "get_last_error", return_value=5)

    result = _process_guard.guard_process(999)

    assert result is False


def test_assign_process_failure_returns_false(mocker):
    """If AssignProcessToJobObject fails, the guard returns False without raising."""
    mocker.patch.object(_process_guard.sys, "platform", "win32")
    kernel32 = MagicMock()
    kernel32.CreateJobObjectW.return_value = 111
    kernel32.SetInformationJobObject.return_value = 1
    kernel32.OpenProcess.return_value = 222
    kernel32.AssignProcessToJobObject.return_value = 0
    mocker.patch.object(_process_guard.ctypes, "WinDLL", return_value=kernel32, create=True)
    mocker.patch.object(_process_guard.ctypes, "get_last_error", return_value=5)

    result = _process_guard.guard_process(999)

    assert result is False
