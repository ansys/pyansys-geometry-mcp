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

"""Unit tests for the modeling tools."""

from unittest.mock import MagicMock

from ansys.geometry.mcp.tools import (
    add_component,
    create_box,
    create_design,
    extrude_sketch,
    list_entities,
    move_body_to_component,
    revolve_sketch,
)


def test_create_box_with_custom_origin(ctx):
    """Test creating a box at an origin other than (0, 0, 0)."""
    create_design(ctx, "test_create_box_origin_001")
    result = create_box(
        ctx, name="offset_box", width=1.0, depth=1.0, height=1.0, origin=[2.0, 3.0, 4.0]
    )
    assert "offset_box" in result
    assert "successfully" in result

    bodies = list_entities(ctx, entity_type="body")
    assert "offset_box" in bodies


def test_extrude_sketch(ctx):
    """Test extruding a circular sketch into a cylinder."""
    create_design(ctx, "test_extrude_001")
    result = extrude_sketch(
        ctx,
        name="extruded_cylinder",
        sketch_primitives=[{"type": "circle", "center_x": 0.0, "center_y": 0.0, "radius": 0.5}],
        distance=1.0,
    )
    assert "extruded successfully" in result


def test_revolve_sketch(ctx):
    """Test revolving a circular sketch around an axis to create a torus."""
    create_design(ctx, "test_revolve_001")
    result = revolve_sketch(
        ctx,
        name="revolved_torus",
        sketch_primitives=[{"type": "circle", "center_x": 2.0, "center_y": 0.0, "radius": 0.5}],
        axis_direction=[0.0, 1.0, 0.0],
        rotation_origin=[0.0, 0.0, 0.0],
    )
    assert "revolved successfully" in result


def test_add_and_list_components(ctx):
    """Test adding root and nested components, a missing-parent error, and listing them."""
    create_design(ctx, "test_components_001")

    assert "added successfully" in add_component(ctx, name="parent_comp")
    assert "added successfully" in add_component(
        ctx, name="child_comp", parent_component_name="parent_comp"
    )
    assert "not found" in add_component(
        ctx, name="orphan", parent_component_name="nonexistent_parent"
    )

    result = list_entities(ctx, entity_type="component")
    assert "parent_comp" in result
    assert "child_comp" in result


def test_move_body_to_component(ctx):
    """Test moving a body into a component."""
    create_design(ctx, "test_move_body_001")
    create_box(ctx, name="movable_box", width=1.0, depth=1.0, height=1.0)
    add_component(ctx, name="target_comp")
    result = move_body_to_component(
        ctx, body_name="movable_box", target_component_name="target_comp"
    )
    assert "moved to component" in result
    assert "successfully" in result


def test_move_body_to_component_not_found(ctx):
    """Test that a missing body or missing component each return a not-found error."""
    create_design(ctx, "test_move_body_not_found_001")
    add_component(ctx, name="target_comp_not_found")
    create_box(ctx, name="orphan_box", width=1.0, depth=1.0, height=1.0)

    assert "not found" in move_body_to_component(
        ctx, body_name="nonexistent_box", target_component_name="target_comp_not_found"
    )
    assert "not found" in move_body_to_component(
        ctx, body_name="orphan_box", target_component_name="nonexistent_comp"
    )


def test_move_body_to_component_not_connected():
    """Test that moving a body when not connected returns an error message."""
    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result.product_instance = None
    result = move_body_to_component(mock_ctx, body_name="box", target_component_name="comp")
    assert "not connected" in result
