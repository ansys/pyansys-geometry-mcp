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

"""Configuration for MCP tool test modules."""

from unittest.mock import MagicMock
import uuid

import pytest

from ansys.geometry.mcp import app


@pytest.fixture(scope="session")
def context():
    """Start the geometry backend once for the whole test session."""
    app.context = app.create_context()
    app.context.transport_mode = "insecure"

    # Launch the backend without starting the MCP stdio protocol.
    app.product_startup()
    yield app.context

    app.product_cleanup()


@pytest.fixture(scope="session")
def ctx(context):
    """Return a minimal MCP Context that resolves to the real app context.

    Tools call ``ctx.fastmcp._lifespan_result`` to reach the context, so we
    wire that attribute to the live session context without starting any server.
    """
    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result = context
    return mock_ctx


@pytest.fixture
def selection_handle(context):
    """Register a fresh SelectionBuilder and return its handle."""
    sb = context.product_instance.create_selection_builder()
    handle = str(uuid.uuid4())
    context.selection_registry[handle] = sb
    yield handle
    context.selection_registry.pop(handle, None)
