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

"""Unit tests for BodySelection tools."""

from ansys.geometry.mcp import tools
from ansys.geometry.mcp.context import PyAnsysGeometryContext
from ansys.geometry.mcp.selection.body_selection_tools import select_bodies


def _setup(ctx, design_name, box_name="box"):
    """Create a fresh design, a 1×1×1 m box, and a selection builder; return the handle."""
    tools.create_design(ctx, design_name)
    tools.create_box(ctx, name=box_name, width=1.0, height=1.0, depth=1.0)
    return tools.create_selection_builder(ctx)


def test_select_bodies_type_criteria(ctx: PyAnsysGeometryContext):
    """all/visible/solid return the box; surface does not (box is solid)."""
    handle = _setup(ctx, "test_select_bodies_types", box_name="type_box")

    for criteria in ("all", "visible", "solid"):
        result = select_bodies(ctx, handle, criteria=criteria)
        assert isinstance(result, list), criteria
        assert "type_box" in result, criteria

    result = select_bodies(ctx, handle, criteria="surface")
    assert isinstance(result, list)
    assert "type_box" not in result


def test_select_bodies_name(ctx: PyAnsysGeometryContext):
    """criteria='name' returns the matching body; omitting name returns an error string."""
    handle = _setup(ctx, "test_select_bodies_name", box_name="named_box")

    result = select_bodies(ctx, handle, criteria="name", name="named_box")
    assert result == ["named_box"]

    result = select_bodies(ctx, handle, criteria="name")
    assert isinstance(result, str)


def test_select_bodies_named_selection_missing_arg(ctx: PyAnsysGeometryContext):
    """criteria='named_selection' without the named_selection arg returns an error string."""
    handle = _setup(ctx, "test_select_bodies_named_sel")

    result = select_bodies(ctx, handle, criteria="named_selection")
    assert isinstance(result, str)


def test_select_bodies_volume(ctx: PyAnsysGeometryContext):
    """criteria='volume' finds the 1 m³ box in range, misses it out of range, errors with no bounds."""
    handle = _setup(ctx, "test_select_bodies_volume", box_name="vol_box")

    assert "vol_box" in select_bodies(ctx, handle, criteria="volume", min_value=0.5, max_value=2.0)
    assert select_bodies(ctx, handle, criteria="volume", min_value=100.0, max_value=200.0) == []
    assert isinstance(select_bodies(ctx, handle, criteria="volume", min_value=0.5), list)
    assert select_bodies(ctx, handle, criteria="volume", max_value=2.0) == "min_value must be provided for 'volume' criterion."


def test_select_bodies_surface_area(ctx: PyAnsysGeometryContext):
    """criteria='surface_area' finds the 6 m² box in range and misses it out of range."""
    handle = _setup(ctx, "test_select_bodies_surface_area", box_name="sa_box")

    assert "sa_box" in select_bodies(ctx, handle, criteria="surface_area", min_value=5.0, max_value=7.0)
    assert select_bodies(ctx, handle, criteria="surface_area", min_value=100.0, max_value=200.0) == []


def test_select_bodies_location(ctx: PyAnsysGeometryContext):
    """x/y/z_location criteria find the box at centroid (0, 0, 0.5) m and miss it far away."""
    handle = _setup(ctx, "test_select_bodies_location", box_name="loc_box")

    # centroid X=0, Y=0, Z=0.5 for a 1×1×1 m box extruded from the XY plane
    assert "loc_box" in select_bodies(ctx, handle, criteria="x_location", min_value=-0.1, max_value=0.1)
    assert select_bodies(ctx, handle, criteria="x_location", min_value=50.0, max_value=100.0) == []

    assert "loc_box" in select_bodies(ctx, handle, criteria="y_location", min_value=-0.1, max_value=0.1)
    assert select_bodies(ctx, handle, criteria="y_location", min_value=50.0, max_value=100.0) == []

    assert "loc_box" in select_bodies(ctx, handle, criteria="z_location", min_value=0.4, max_value=0.6)
    assert select_bodies(ctx, handle, criteria="z_location", min_value=50.0, max_value=100.0) == []


def test_select_bodies_missing_args_return_error(ctx: PyAnsysGeometryContext):
    """Color without color arg, and an invalid handle, both return error strings."""
    handle = _setup(ctx, "test_select_bodies_errors")

    assert isinstance(select_bodies(ctx, handle, criteria="color"), str)
    assert isinstance(select_bodies(ctx, "not-a-real-handle", criteria="all"), str)