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

"""Unit tests for the shared helpers."""

from unittest.mock import MagicMock

from ansys.geometry.mcp.misc.helpers import connect_to_modeler_in_persistent_python


def test_no_python_session(ctx):
    """Test connecting to the Modeler instance in the persistent Python session when no Python session is available."""
    ctx.request_context.lifespan_context.python_session = None
    result = connect_to_modeler_in_persistent_python(ctx)
    assert (
        result == "No Python session available. The persistent Python session was not initialized."
    )


def test_already_connected_python_session(ctx):
    """Test connecting to the Modeler instance in the persistent Python session when already connected."""
    session = MagicMock()
    session.metadata = {"instance": MagicMock(host="localhost", port=50051)}

    ctx.request_context.lifespan_context.python_session = session
    result = connect_to_modeler_in_persistent_python(ctx)
    assert "Already connected to persistent PyAnsys Geometry session" in result


def test_no_modeler_in_lifespan_context(ctx):
    """Test connecting to the Modeler instance in the persistent Python session when no Modeler instance is available in the lifespan context."""
    session = MagicMock()
    session.metadata = {}

    ctx.request_context.lifespan_context.python_session = session
    ctx.request_context.lifespan_context.product_instance = None
    result = connect_to_modeler_in_persistent_python(ctx)
    assert result == "No Modeler instance available in lifespan context."


def test_successful_python_session_connection(ctx):
    """Test successfully connecting to the Modeler instance in the persistent Python session."""
    assert ctx.request_context.lifespan_context.product_instance is not None

    result = connect_to_modeler_in_persistent_python(ctx)
    assert result is not None
