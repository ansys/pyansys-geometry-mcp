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

"""Test tools."""

from unittest.mock import MagicMock, patch

import pytest

from ansys.geometry.mcp import PyAnsysGeometryContext
from ansys.geometry.mcp.tools import (
    _build_sketch,
    _find_body,
    add_component,
    create_box,
    create_design,
    create_named_selection,
    export_design_to,
    extrude_sketch,
    get_command_history,
    get_design_3d_scene,
    get_design_info,
    get_geometry_ctx,
    get_product_status,
    get_screenshot,
    get_transcript,
    intersect_body,
    list_bodies,
    list_components,
    move_body_to_component,
    read_image_in_base64,
    revolve_sketch,
    subtract_body,
    unite_body,
)


def test_get_product_status_tool(ctx):
    """Test getting the product status."""
    status = get_product_status(ctx)
    assert "Product backend is connected:" in status


def test_create_design(ctx):
    """Test creating a new design."""
    result = create_design(ctx, "test_create_design_001")
    assert "test_create_design_001" in result
    assert "created successfully" in result


def test_get_design_info(ctx):
    """Test retrieving information about the active design."""
    create_design(ctx, "test_get_design_info_001")
    result = get_design_info(ctx)
    assert isinstance(result, str)
    assert len(result) > 0


def test_export_design_to(ctx, tmp_path_factory: pytest.TempPathFactory):
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
def test_export_design_to_formats(ctx, file_format: str, tmp_path_factory: pytest.TempPathFactory):
    """Test exporting the active design to each supported file format."""
    design_name = f"test_export_{file_format}_001"
    create_design(ctx, design_name)
    create_box(ctx, name=f"{file_format}_box", width=1.0, depth=1.0, height=1.0)

    # Define the location and expected file location
    location = tmp_path_factory.mktemp(f"test_export_to_{file_format}")
    file_location = location / f"{design_name}.{file_format}"
    result = export_design_to(ctx, file_format=file_format, folder=str(file_location))

    assert f"Design exported to {file_format.upper()} file:" in result
    assert file_location.exists()


def test_export_design_to_unsupported_format(ctx, tmp_path_factory: pytest.TempPathFactory):
    """Test that an unsupported format returns an error message."""
    design_name = "test_export_unsupported_001"
    create_design(ctx, design_name)

    # Define the location and expected file location
    location = tmp_path_factory.mktemp("test_export_to_scdocx")
    file_location = location / f"{design_name}"

    result = export_design_to(ctx, file_format="xyz_unsupported", folder=str(file_location))
    assert "Unsupported format" in result


def test_export_design_to_not_connected():
    """Test that exporting when not connected returns an error message."""
    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result.product_instance = None
    result = export_design_to(mock_ctx, file_format="scdocx")
    assert "not connected" in result


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


@pytest.mark.skip(reason="design.plot() opens a blocking GUI window; cannot be automated")
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


def test_build_sketch_primitives():
    """Test all _build_sketch branches: default plane, custom plane, every primitive type, and invalid type."""
    sketch, _ = _build_sketch(
        [
            {"type": "circle", "center_x": 0.0, "center_y": 0.0, "radius": 1.0},
            {"type": "box", "center_x": 0.0, "center_y": 0.0, "width": 2.0, "height": 2.0},
            {"type": "polygon", "center_x": 0.0, "center_y": 0.0, "inner_radius": 0.5, "sides": 6},
            {"type": "segment", "start_x": 0.0, "start_y": 0.0, "end_x": 1.0, "end_y": 0.0},
            {
                "type": "arc",
                "center_x": 0.5,
                "center_y": 0.0,
                "start_x": 0.0,
                "start_y": 0.0,
                "end_x": 1.0,
                "end_y": 0.0,
            },
        ]
    )
    assert sketch is not None

    sketch2, _ = _build_sketch(
        [{"type": "circle", "center_x": 0.0, "center_y": 0.0, "radius": 1.0}],
        plane_origin=[0.0, 0.0, 1.0],
        plane_dir_x=[1.0, 0.0, 0.0],
        plane_dir_y=[0.0, 1.0, 0.0],
    )
    assert sketch2 is not None

    with pytest.raises(ValueError, match="Unsupported sketch primitive type"):
        _build_sketch([{"type": "triangle"}])


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

    result = list_components(ctx)
    assert "parent_comp" in result
    assert "child_comp" in result


def test_list_bodies(ctx):
    """Test listing bodies for the full design, a specific component, an empty component, and a missing component."""
    create_design(ctx, "test_list_bodies_001")
    add_component(ctx, name="body_comp")
    add_component(ctx, name="empty_comp")
    create_box(
        ctx, name="listed_box", width=1.0, depth=1.0, height=1.0, parent_component_name="body_comp"
    )

    full = list_bodies(ctx)
    assert "listed_box" in full

    scoped = list_bodies(ctx, component_name="body_comp")
    assert "listed_box" in scoped

    assert "No bodies found" in list_bodies(ctx, component_name="empty_comp")
    assert "not found" in list_bodies(ctx, component_name="nonexistent_comp")


def test_create_box_with_custom_origin(ctx):
    """Test creating a box at an origin other than (0, 0, 0)."""
    create_design(ctx, "test_create_box_origin_001")
    result = create_box(
        ctx, name="offset_box", width=1.0, depth=1.0, height=1.0, origin=[2.0, 3.0, 4.0]
    )
    assert "offset_box" in result
    assert "successfully" in result

    bodies = list_bodies(ctx)
    assert "offset_box" in bodies


def test_boolean_operations(ctx):
    """Test subtract, unite, and intersect boolean operations on overlapping boxes."""
    create_design(ctx, "test_boolean_ops_001")
    for prefix in ("subtract", "unite", "intersect"):
        create_box(ctx, name=f"{prefix}_target", width=2.0, depth=2.0, height=2.0)
        create_box(ctx, name=f"{prefix}_tool", width=1.0, depth=1.0, height=1.0)

    assert "complete" in subtract_body(
        ctx, target_body_name="subtract_target", tool_body_name="subtract_tool"
    )
    assert "complete" in unite_body(
        ctx, target_body_name="unite_target", tool_body_name="unite_tool"
    )
    assert "complete" in intersect_body(
        ctx, target_body_name="intersect_target", tool_body_name="intersect_tool"
    )


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


def test_get_command_history(ctx):
    """Test that command history returns a list of strings after executing commands."""
    result = get_command_history(ctx)
    assert len(result) == 3
    assert result[0] == "selection_registry = {}"

    create_design(ctx, "test_get_command_history_001")
    result = get_command_history(ctx)
    assert len(result) == 4

    create_box(ctx, name="test_box", width=1.0, depth=1.0, height=1.0)
    result = get_command_history(ctx)
    assert len(result) == 10


def test_get_transcript(ctx):
    """Test that the transcript contains the correct commands after each operation."""
    create_design(ctx, "test_transcript_001")
    result = get_transcript(ctx)
    assert result.count("test_transcript_001") == 1
    assert 'design = instance.create_design("test_transcript_001")' in result

    create_box(ctx, name="transcript_box", width=1.0, depth=1.0, height=1.0)
    result = get_transcript(ctx)
    assert result.count("transcript_box") == 1
    assert "sketch.box(center=Point2D([0.0, 0.0]), width=1.0, height=1.0)" in result


def test_create_named_selection(ctx):
    """Test create_named_selection with bodies, faces, edges, vertices, components,
    and all error paths: not connected, no entities, missing body, missing component."""
    # Test the not connected case
    disconnected_ctx = MagicMock()
    disconnected_ctx.fastmcp._lifespan_result.product_instance = None
    assert "not connected" in create_named_selection(disconnected_ctx, "ns", body_names=["x"])

    # Test the no entities provided case
    assert "At least one entity list" in create_named_selection(ctx, "empty_ns")

    # Test setup: design with a box and a component
    create_design(ctx, "test_named_sel_001")
    add_component(ctx, name="ns_comp")
    create_box(
        ctx,
        name="ns_box",
        width=1.0,
        depth=1.0,
        height=1.0,
        parent_component_name="ns_comp",
    )
    create_box(ctx, name="root_box", width=1.0, depth=1.0, height=1.0, origin=[5, 5, 5])

    # Test not-found error paths
    assert "not found" in create_named_selection(ctx, "bad_ns", body_names=["no_such_body"])
    assert "not found" in create_named_selection(ctx, "bad_ns", component_names=["no_such_comp"])
    assert "not found" in create_named_selection(ctx, "bad_ns", beam_ids=["nonexistent_beam"])
    assert "not found" in create_named_selection(
        ctx, "bad_ns", coordinate_system_ids=["nonexistent_cs"]
    )
    assert "not found" in create_named_selection(ctx, "bad_ns", datum_point_ids=["nonexistent_dp"])

    # Test the bodies case
    result = create_named_selection(ctx, "ns_bodies", body_names=["ns_box"])
    assert "created successfully" in result

    # Test the components case
    result = create_named_selection(ctx, "ns_comps", component_names=["ns_comp"])
    assert "created successfully" in result

    app_context = get_geometry_ctx(ctx)
    design = app_context.product_instance.get_active_design()
    box_body = _find_body(design, "ns_box")
    root_box_body = _find_body(design, "root_box")

    face = box_body.faces[0]
    result = create_named_selection(ctx, "ns_faces", face_ids=[face.id])
    assert "created successfully" in result

    edge = box_body.edges[0]
    result = create_named_selection(ctx, "ns_edges", edge_ids=[edge.id])
    assert "created successfully" in result

    vertex = root_box_body.vertices[0]
    result = create_named_selection(ctx, "ns_verts", vertex_ids=[vertex.id])
    assert "created successfully" in result

    # Test the mixed entities case
    result = create_named_selection(
        ctx,
        "ns_mixed",
        body_names=["ns_box"],
        face_ids=[face.id],
        edge_ids=[edge.id],
        vertex_ids=[vertex.id],
        component_names=["ns_comp"],
    )
    assert "created successfully" in result

    # Test the command history records the call
    history = app_context.command_history
    assert any("create_named_selection" in cmd and "ns_mixed" in cmd for cmd in history)

    # Test design_point_ids
    from ansys.geometry.core.math import Frame, Plane, Point3D, UnitVector3D
    from pint import Quantity

    design.add_design_point("dp_test", Point3D([1, 2, 3]))
    dp = design.design_points[0]
    result = create_named_selection(ctx, "ns_design_points", design_point_ids=[dp.id])
    assert "created successfully" in result

    # Test datum_plane_ids
    design.create_datum_plane(
        "datp_test",
        Plane(
            origin=Point3D([0, 0, 0]),
            direction_x=UnitVector3D([1, 0, 0]),
            direction_y=UnitVector3D([0, 1, 0]),
        ),
    )
    datum_pl = design.datum_planes[0]
    result = create_named_selection(ctx, "ns_datum_planes", datum_plane_ids=[datum_pl.id])
    assert "created successfully" in result

    # Test beam_ids
    profile = design.add_beam_circular_profile("bp_test", Quantity(0.1, "m"))
    beam = design.create_beam(Point3D([0, 0, 0]), Point3D([1, 0, 0]), profile)
    result = create_named_selection(ctx, "ns_beams", beam_ids=[beam.id])
    assert "created successfully" in result

    # Test coordinate_system_ids
    cs = design.create_coordinate_system("cs_test", Frame())
    result = create_named_selection(ctx, "ns_coord_sys", coordinate_system_ids=[cs.id])
    assert "created successfully" in result

    # Test datum_point_ids
    design.create_datum_point("datp_pt_test", Point3D([5, 5, 5]))
    datum_pt = design.datum_points[0]
    result = create_named_selection(ctx, "ns_datum_points", datum_point_ids=[datum_pt.id])
    assert "created successfully" in result


def test_create_named_selection_errors(ctx):
    """Test error handling in create_named_selection."""
    app_context = get_geometry_ctx(ctx)
    design = app_context.product_instance.get_active_design()
    with patch.object(design, "create_named_selection", side_effect=Exception("Test error")):
        result = create_named_selection(ctx, "ns_error", body_names=["ns_box"])
        assert "Error" in result
