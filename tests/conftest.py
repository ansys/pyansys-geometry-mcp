# Copyright (C) 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
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

"""Configuration for MCP tool test modules."""

from pathlib import Path
from unittest.mock import MagicMock

import ansys.geometry.core as pyansys_geometry
import pytest

from ansys.geometry.mcp import app

FILES_DIR = Path(Path(__file__).parent, "files")


@pytest.fixture(scope="session")
def context(use_existing_service):
    """Start the geometry backend once for the whole test session."""
    app.context = app.create_context()
    app.context.transport_mode = "insecure"
    app.context.connect_to_existing_service = use_existing_service

    # Launch the backend without starting the MCP stdio protocol, following the same
    # order as product_lifespan().
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


@pytest.fixture(scope="session")
def use_existing_service(request):
    value: str = request.config.getoption("--use-existing-service")
    return True if value.lower() == "yes" else False


@pytest.fixture(scope="session", autouse=True)
def use_tracker(request):
    """Fixture to enable or disable the tracker."""
    value: str = request.config.getoption("--use-tracker", default="no")  # Explicitly set default

    if value.lower() == "yes":
        pyansys_geometry.USE_TRACKER_TO_UPDATE_DESIGN = True
    else:
        pyansys_geometry.USE_TRACKER_TO_UPDATE_DESIGN = False

    yield  # This allows the test to run

    # Revert the state after the test session
    pyansys_geometry.USE_TRACKER_TO_UPDATE_DESIGN = False


def pytest_addoption(parser):
    parser.addoption(
        "--use-existing-service",
        action="store",
        default="no",
        help=(
            "Use Modeler object to connect to an existing service. Options: 'yes' or 'no'."
            " By default, 'no'."
        ),
        choices=("yes", "no"),
    )
    parser.addoption(
        "--use-tracker",
        action="store",
        default="no",
        help=("Enable the tracker to update the design. Options: 'yes' or 'no'. By default, 'no'."),
        choices=("yes", "no"),
    )
