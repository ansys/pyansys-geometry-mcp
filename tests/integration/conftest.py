# Copyright (C) 2023 - 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
# SPDX-License-Identifier: MIT
#
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

"""This testing module automatically connects to the Geometry service running
at localhost:50051.

If you want to override these defaults, set the following environment variables.

- export ANSRV_GEO_HOST=127.0.0.1
- export ANSRV_GEO_PORT=50051
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import ansys.tools.visualization_interface as viz_interface
import pytest
import pyvista as pv

from ansys.geometry.mcp import app

pv.OFF_SCREEN = True
viz_interface.TESTING_MODE = True
pv.global_theme.window_size = [600, 600]

FILES_DIR = Path(Path(__file__).parent, "files")
SESSION_TOOLS = "ansys.geometry.mcp.tools.session_tools"


@pytest.fixture(scope="session")
def context(use_existing_service, transport_mode):
    """Start the geometry backend once for the whole test session."""
    python_session = MagicMock()
    python_session.metadata = {}

    app.context = app.create_context()
    app.context.transport_mode = transport_mode
    app.context.connect_to_existing_service = use_existing_service
    app.context.python_session = python_session

    # Launch the backend without starting the MCP stdio protocol.
    app.product_startup()
    yield app.context

    app.product_cleanup()


@pytest.fixture(scope="session")
def startup_history(context):
    """Snapshot the command history produced by product_startup for reuse."""
    return list(context.command_history)


@pytest.fixture(scope="function")
def ctx(context, startup_history):
    """Return a minimal MCP Context that resolves to the real app context.

    Tools call ``ctx.fastmcp._lifespan_result`` to reach the context, so we
    wire that attribute to the live session context without starting any server.
    """
    context.command_history.clear()
    context.command_history.extend(startup_history)

    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result = context
    mock_ctx.request_context.lifespan_context = context
    yield mock_ctx


@pytest.fixture
def execute_mock(monkeypatch, ctx):
    """Replace ``PersistentPythonSession.execute`` with a mock returning a result dict."""
    mock = MagicMock(return_value={"success": True, "stdout": "", "stderr": ""})
    monkeypatch.setattr(ctx.request_context.lifespan_context.python_session, "execute", mock)
    return mock


@pytest.fixture
def connect_mock(monkeypatch):
    """Replace the persistent-session connection helper with a mock returning a Modeler.

    Also keeps the real helper from writing ``metadata["instance"]`` into the
    session-scoped Python session mock, which would leak into later tests.
    """
    mock = MagicMock(return_value=MagicMock(name="modeler"))
    monkeypatch.setattr(f"{SESSION_TOOLS}.connect_to_modeler_in_persistent_python", mock)
    return mock
