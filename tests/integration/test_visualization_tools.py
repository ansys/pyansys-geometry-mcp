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
