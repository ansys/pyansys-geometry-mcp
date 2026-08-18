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

"""Test tools."""

from unittest.mock import MagicMock

import pytest

from ansys.geometry.mcp import PyAnsysGeometryContext
from ansys.geometry.mcp.tools import (
    create_box,
    create_design,
    export_design_to,
    get_design_info,
    get_product_status,
)


def test_get_product_status_tool(ctx: PyAnsysGeometryContext):
    """Test getting the product status."""
    status = get_product_status(ctx)
    assert "Product backend is connected:" in status


def test_create_design(ctx: PyAnsysGeometryContext):
    """Test creating a new design."""
    result = create_design(ctx, "test_create_design_001")
    assert "test_create_design_001" in result
    assert "created successfully" in result


def test_get_design_info(ctx: PyAnsysGeometryContext):
    """Test retrieving information about the active design."""
    create_design(ctx, "test_get_design_info_001")
    result = get_design_info(ctx)
    assert isinstance(result, str)
    assert len(result) > 0


def test_export_design_to(ctx: PyAnsysGeometryContext, tmp_path_factory: pytest.TempPathFactory):
    """Test exporting the active design to scdocx format."""
    design_name = "test_export_design_001"
    create_design(ctx, design_name)

    # Define the location and expected file location
    location = tmp_path_factory.mktemp("test_export_to_scdocx")
    file_location = location / f"{design_name}.scdocx"

    result = export_design_to(ctx, file_format="scdocx", folder=str(file_location))
    assert "Design exported to SCDOCX file:" in result


@pytest.mark.parametrize(
    "file_format",
    ["fmd", "step", "iges", "disco", "parasolid_text", "parasolid_bin"],
)
def test_export_design_to_formats(ctx: PyAnsysGeometryContext, file_format: str, tmp_path_factory: pytest.TempPathFactory):
    """Test exporting the active design to each supported file format."""
    design_name = f"test_export_{file_format}_001"
    create_design(ctx, design_name)
    create_box(ctx, name=f"{file_format}_box", width=1.0, depth=1.0, height=1.0)

    # Define the location and expected file location
    location = tmp_path_factory.mktemp(f"test_export_to_{file_format}")
    file_location = location / f"{design_name}.{file_format}"
    result = export_design_to(ctx, file_format=file_format, folder=str(file_location))
    assert f"Design exported to {file_format.upper()} file:" in result


def test_export_design_to_unsupported_format(ctx: PyAnsysGeometryContext, tmp_path_factory: pytest.TempPathFactory):
    """Test that an unsupported format returns an error message."""
    design_name = "test_export_unsupported_001"
    create_design(ctx, design_name)

    # Define the location and expected file location
    location = tmp_path_factory.mktemp("test_export_to_scdocx")
    file_location = location / f"{design_name}.scdocx"

    result = export_design_to(ctx, file_format="xyz_unsupported", folder=str(file_location))
    assert "Unsupported format" in result


def test_export_design_to_not_connected():
    """Test that exporting when not connected returns an error message."""
    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result.product_instance = None
    result = export_design_to(mock_ctx, file_format="scdocx")
    assert "not connected" in result

