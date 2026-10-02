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

"""Unit tests for the visualization tools."""

from unittest.mock import MagicMock

import pytest
from pyvista.plotting import system_supports_plotting

from ansys.geometry.mcp.tools import (
    create_box,
    create_design,
    get_design_3d_scene,
    get_screenshot,
    read_image_in_base64,
)

skip_no_xserver = pytest.mark.skipif(
    not system_supports_plotting(), reason="Requires active X Server"
)


def test_get_screenshot(ctx, tmp_path_factory: pytest.TempPathFactory):
    """Test capturing a screenshot of the active design."""
    create_design(ctx, "test_screenshot_001")
    create_box(ctx, name="screenshot_box", width=1.0, depth=1.0, height=1.0)
    path = str(tmp_path_factory.mktemp("screenshots") / "scene.png")
    result = get_screenshot(ctx, path=path)
    assert "3D scene screenshot saved:" in result


def test_get_screenshot_not_connected():
    """Test that getting a screenshot when not connected returns an error message."""
    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result.product_instance = None
    result = get_screenshot(mock_ctx)
    assert "not connected" in result


@skip_no_xserver
def test_get_design_3d_scene(ctx):
    """Test opening the 3D scene window of the active design."""
    create_design(ctx, "test_3d_scene_001")
    create_box(ctx, name="scene_box", width=1.0, depth=1.0, height=1.0)
    result = get_design_3d_scene(ctx)
    assert "3D scene window opened" in result


def test_get_design_3d_scene_not_connected():
    """Test that opening the 3D scene when not connected returns an error message."""
    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result.product_instance = None
    result = get_design_3d_scene(mock_ctx)
    assert "not connected" in result


def test_read_image_in_base64(ctx, tmp_path):
    """Test that a valid file is returned as a base64-encoded string."""
    import base64

    image_data = b"\x89PNG\r\n\x1a\n"  # minimal PNG-like bytes
    image_file = tmp_path / "test.png"
    image_file.write_bytes(image_data)

    result = read_image_in_base64(ctx, str(image_file))

    assert "base64" in result
    assert result["base64"] == base64.b64encode(image_data).decode("utf-8")

    result = read_image_in_base64(ctx, str(tmp_path / "nonexistent.png"))

    assert "error" in result
    assert "nonexistent.png" in result["error"]
