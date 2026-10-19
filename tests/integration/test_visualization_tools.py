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

from unittest.mock import MagicMock, patch

import pytest
from pyvista.plotting import system_supports_plotting

from ansys.geometry.mcp.tools import (
    create_design,
    read_image_in_base64,
    visualize,
)

from .conftest import create_box

skip_no_xserver = pytest.mark.skipif(
    not system_supports_plotting(), reason="Requires active X Server"
)


def test_visualize_saves_image(ctx, tmp_path_factory: pytest.TempPathFactory):
    """Test saving an image of the active design when a path is provided."""
    create_design(ctx, "test_screenshot_001")
    create_box(ctx, name="screenshot_box", width=1.0, depth=1.0, height=1.0)

    # Test with an explicit path
    path = str(tmp_path_factory.mktemp("screenshots") / "scene.png")
    result = visualize(ctx, path=path)
    assert "3D scene image saved:" in result

    # Test without an explicit path
    app_context = MagicMock()
    app_context.command_history = []
    design = app_context.product_instance.get_active_design.return_value
    mock_ctx = MagicMock()
    with (
        patch(
            "ansys.geometry.mcp.tools.visualization_tools.get_geometry_ctx",
            return_value=app_context,
        ),
        patch("ansys.geometry.mcp.tools.visualization_tools.time.time", return_value=123),
    ):
        result = visualize(mock_ctx, save=True)
        design.plot.assert_called_once_with(
            screenshot="design_3d_scene_123.png",
            use_service_colors=False,
        )
        design.plot.reset_mock()
        result_without_colors = visualize(mock_ctx, path="scene.png", use_service_colors=False)

    design.plot.assert_called_once_with(
        screenshot="scene.png",
        use_service_colors=False,
    )
    assert "3D scene image saved: design_3d_scene_123.png" == result
    assert "3D scene image saved: scene.png" == result_without_colors
    assert app_context.command_history == [
        "design.plot(screenshot='design_3d_scene_123.png', use_service_colors=False)",
        "design.plot(screenshot='scene.png', use_service_colors=False)",
    ]


def test_visualize_not_connected():
    """Test that visualization without a backend returns an error message."""
    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result.product_instance = None
    result = visualize(mock_ctx)
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
