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

"""Tests for ``ansys.geometry.mcp.server``."""

from unittest.mock import MagicMock

from ansys.geometry.mcp.server import PyAnsysGeometryMCP


class TestGuardLocalBackendProcess:
    """Tests for ``PyAnsysGeometryMCP._guard_local_backend_process``."""

    def test_guards_process_when_pid_available(self, mocker):
        """When a local ProductInstance PID is found, guard_process is called with it."""
        guard_process = mocker.patch("ansys.geometry.mcp._process_guard.guard_process")

        instance = MagicMock()
        instance.client._product_instance._pid = 4242

        PyAnsysGeometryMCP._guard_local_backend_process(instance)

        guard_process.assert_called_once_with(4242)

    def test_no_op_when_product_instance_is_none(self, mocker):
        """Docker/remote backends (no local ProductInstance) are left untouched."""
        guard_process = mocker.patch("ansys.geometry.mcp._process_guard.guard_process")

        instance = MagicMock()
        instance.client._product_instance = None

        PyAnsysGeometryMCP._guard_local_backend_process(instance)

        guard_process.assert_not_called()

    def test_no_op_when_attribute_missing(self, mocker):
        """A missing private attribute (future ansys-geometry-core change) is tolerated."""
        guard_process = mocker.patch("ansys.geometry.mcp._process_guard.guard_process")

        instance = MagicMock(spec=[])  # no attributes at all

        PyAnsysGeometryMCP._guard_local_backend_process(instance)

        guard_process.assert_not_called()
