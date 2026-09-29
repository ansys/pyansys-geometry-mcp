# Copyright (C) 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for the shared helpers."""

from unittest.mock import MagicMock

from ansys.geometry.mcp.misc.helpers import connect_to_modeler_in_persistent_python


def test_no_python_session(ctx, monkeypatch):
    """Test connecting to the Modeler instance in the persistent Python session when no Python session is available."""
    # The app context is session scoped, so monkeypatch restores it for the next test.
    monkeypatch.setattr(ctx.request_context.lifespan_context, "python_session", None)
    result = connect_to_modeler_in_persistent_python(ctx)
    assert (
        result == "No Python session available. The persistent Python session was not initialized."
    )


def test_already_connected_python_session(ctx, monkeypatch):
    """Test connecting to the Modeler instance in the persistent Python session when already connected."""
    session = MagicMock()
    session.metadata = {"instance": MagicMock(host="localhost", port=50051)}

    monkeypatch.setattr(ctx.request_context.lifespan_context, "python_session", session)
    result = connect_to_modeler_in_persistent_python(ctx)
    assert "Already connected to persistent PyAnsys Geometry session" in result


def test_no_modeler_in_lifespan_context(ctx, monkeypatch):
    """Test connecting to the Modeler instance in the persistent Python session when no Modeler instance is available in the lifespan context."""
    session = MagicMock()
    session.metadata = {}

    monkeypatch.setattr(ctx.request_context.lifespan_context, "python_session", session)
    monkeypatch.setattr(ctx.request_context.lifespan_context, "product_instance", None)
    result = connect_to_modeler_in_persistent_python(ctx)
    assert result == "No Modeler instance available in lifespan context."


def test_successful_python_session_connection(ctx, monkeypatch):
    """Test successfully connecting to the Modeler instance in the persistent Python session."""
    session = MagicMock()
    session.metadata = {}

    monkeypatch.setattr(ctx.request_context.lifespan_context, "python_session", session)
    assert ctx.request_context.lifespan_context.product_instance is not None

    result = connect_to_modeler_in_persistent_python(ctx)
    assert result is not None
