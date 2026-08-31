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

"""Unit tests for the selection tools."""

from unittest.mock import MagicMock, patch

import pytest

from ansys.geometry.mcp import tools
from ansys.geometry.mcp.context import PyAnsysGeometryContext
from ansys.geometry.mcp.misc.auxiliary import find_body
from ansys.geometry.mcp.tools import get_geometry_ctx
from ansys.geometry.mcp.tools.selection_tools import (
    create_named_selection,
    extend_body_selection,
    filter_bodies,
    group_bodies,
    list_entities,
    order_bodies,
    select_bodies,
)


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

    assert "type_box" not in select_bodies(ctx, handle, criteria="surface")


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
    assert (
        select_bodies(ctx, handle, criteria="volume", max_value=2.0)
        == "min_value must be provided for 'volume' criterion."
    )


def test_select_bodies_surface_area(ctx: PyAnsysGeometryContext):
    """criteria='surface_area' finds the 6 m² box in range and misses it out of range."""
    handle = _setup(ctx, "test_select_bodies_surface_area", box_name="sa_box")

    assert "sa_box" in select_bodies(
        ctx, handle, criteria="surface_area", min_value=5.0, max_value=7.0
    )
    assert (
        select_bodies(ctx, handle, criteria="surface_area", min_value=100.0, max_value=200.0) == []
    )


def test_select_bodies_location(ctx: PyAnsysGeometryContext):
    """x/y/z_location criteria find the box at centroid (0, 0, 0.5) m and miss it far away."""
    handle = _setup(ctx, "test_select_bodies_location", box_name="loc_box")

    # centroid X=0, Y=0, Z=0.5 for a 1×1×1 m box extruded from the XY plane
    assert "loc_box" in select_bodies(
        ctx, handle, criteria="x_location", min_value=-0.1, max_value=0.1
    )
    assert select_bodies(ctx, handle, criteria="x_location", min_value=50.0, max_value=100.0) == []

    assert "loc_box" in select_bodies(
        ctx, handle, criteria="y_location", min_value=-0.1, max_value=0.1
    )
    assert select_bodies(ctx, handle, criteria="y_location", min_value=50.0, max_value=100.0) == []

    assert "loc_box" in select_bodies(
        ctx, handle, criteria="z_location", min_value=0.4, max_value=0.6
    )
    assert select_bodies(ctx, handle, criteria="z_location", min_value=50.0, max_value=100.0) == []


def test_select_bodies_missing_args_return_error(ctx: PyAnsysGeometryContext):
    """Color without color arg, and an invalid handle, both return error strings."""
    handle = _setup(ctx, "test_select_bodies_errors")

    assert isinstance(select_bodies(ctx, handle, criteria="color"), str)
    assert isinstance(select_bodies(ctx, "not-a-real-handle", criteria="all"), str)


def test_filter_bodies_solid_surface(ctx: PyAnsysGeometryContext):
    """is_solid retains the box; is_surface removes it."""
    handle = _setup(ctx, "test_filter_bodies_solid_surface", box_name="solid_box")

    # Populate the selection builder with the box
    select_bodies(ctx, handle, criteria="all")

    assert "solid_box" in filter_bodies(ctx, handle, criteria="is_solid")
    assert "solid_box" not in filter_bodies(ctx, handle, criteria="is_surface")


def test_filter_bodies_name(ctx: PyAnsysGeometryContext):
    """criteria='name' returns the matching body; omitting name returns an error string."""
    handle = _setup(ctx, "test_filter_bodies_name", box_name="filter_named_box")
    select_bodies(ctx, handle, criteria="all")

    result = filter_bodies(ctx, handle, criteria="name", name="filter_named_box")
    assert result == ["filter_named_box"]

    result = filter_bodies(ctx, handle, criteria="name")
    assert isinstance(result, str)


def test_filter_bodies_numeric_range(ctx: PyAnsysGeometryContext):
    """Volume and surface_area range filtering; find_max/find_min also return the sole box."""
    handle = _setup(ctx, "test_filter_bodies_numeric", box_name="num_box")
    select_bodies(ctx, handle, criteria="all")

    # 1×1×1 box: volume=1 m³, surface_area=6 m²
    assert "num_box" in filter_bodies(ctx, handle, criteria="volume", min_value=0.5, max_value=2.0)
    assert filter_bodies(ctx, handle, criteria="volume", min_value=100.0, max_value=200.0) == []

    # Repopulate the selection builder for the next test, since filter_bodies modifies it
    select_bodies(ctx, handle, criteria="all")
    assert "num_box" in filter_bodies(ctx, handle, criteria="volume", find_max=True)

    # Repopulate the selection builder for the next test, since filter_bodies modifies it
    select_bodies(ctx, handle, criteria="all")
    assert "num_box" in filter_bodies(ctx, handle, criteria="volume", find_min=True)

    assert "num_box" in filter_bodies(
        ctx, handle, criteria="surface_area", min_value=5.0, max_value=7.0
    )
    assert (
        filter_bodies(ctx, handle, criteria="surface_area", min_value=100.0, max_value=200.0) == []
    )

    assert isinstance(filter_bodies(ctx, handle, criteria="volume"), str)


def test_filter_bodies_count_criteria(ctx: PyAnsysGeometryContext):
    """face_count/edge_count/loop_count with find_max return the box (6 faces, 12 edges, 6 loops)."""
    handle = _setup(ctx, "test_filter_bodies_counts", box_name="count_box")
    select_bodies(ctx, handle, criteria="all")

    assert "count_box" in filter_bodies(ctx, handle, criteria="face_count", find_max=True)
    assert "count_box" in filter_bodies(ctx, handle, criteria="edge_count", find_max=True)
    assert "count_box" in filter_bodies(ctx, handle, criteria="loop_count", find_max=True)

    assert isinstance(filter_bodies(ctx, handle, criteria="face_count"), str)


def test_filter_bodies_surface_curve_type(ctx: PyAnsysGeometryContext):
    """containing_surface_type='plane' and containing_curve_type='line' both match the box."""
    handle = _setup(ctx, "test_filter_bodies_types", box_name="type_box")
    select_bodies(ctx, handle, criteria="all")

    assert "type_box" in filter_bodies(
        ctx, handle, criteria="containing_surface_type", surface_type="plane"
    )
    assert "type_box" in filter_bodies(
        ctx, handle, criteria="containing_curve_type", curve_type="line"
    )

    assert isinstance(filter_bodies(ctx, handle, criteria="containing_surface_type"), str)
    assert isinstance(filter_bodies(ctx, handle, criteria="containing_curve_type"), str)


def test_filter_bodies_number_surfaces_curves(ctx: PyAnsysGeometryContext):
    """number_surfaces/number_curves with find_max return the box; missing type arg errors."""
    handle = _setup(ctx, "test_filter_bodies_num_surf_curves", box_name="ns_box")
    select_bodies(ctx, handle, criteria="all")

    assert "ns_box" in filter_bodies(
        ctx, handle, criteria="number_surfaces", surface_type="plane", find_max=True
    )
    assert "ns_box" in filter_bodies(
        ctx, handle, criteria="number_curves", curve_type="line", find_max=True
    )

    assert isinstance(filter_bodies(ctx, handle, criteria="number_surfaces"), str)
    assert isinstance(filter_bodies(ctx, handle, criteria="number_curves"), str)


def test_filter_bodies_missing_args_return_error(ctx: PyAnsysGeometryContext):
    """Color without color arg and an invalid handle both return error strings."""
    handle = _setup(ctx, "test_filter_bodies_errors")
    select_bodies(ctx, handle, criteria="all")

    assert isinstance(filter_bodies(ctx, handle, criteria="color"), str)
    assert isinstance(filter_bodies(ctx, "not-a-real-handle", criteria="is_solid"), str)


@pytest.mark.parametrize(
    "fn, kwargs",
    [
        (select_bodies, {"selection_handle": "h", "criteria": "all"}),
        (filter_bodies, {"selection_handle": "h", "criteria": "is_solid"}),
        (order_bodies, {"selection_handle": "h", "criteria": "volume"}),
        (group_bodies, {"selection_handle": "h", "criteria": "volume"}),
        (extend_body_selection, {"selection_handle": "h", "criteria": "volume"}),
    ],
)
def test_not_connected(fn, kwargs):
    """Every body-selection tool returns a 'not connected' error when product_instance is None."""
    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result.product_instance = None
    result = fn(mock_ctx, **kwargs)
    assert "not connected" in result


def test_list_bodies(ctx):
    """Test listing bodies for the full design, a specific component, an empty component, and a missing component."""
    tools.create_design(ctx, "test_list_bodies_001")
    tools.add_component(ctx, name="body_comp")
    tools.add_component(ctx, name="empty_comp")
    tools.create_box(
        ctx, name="listed_box", width=1.0, depth=1.0, height=1.0, parent_component_name="body_comp"
    )

    full = list_entities(ctx, entity_type="bodies")
    assert "listed_box" in full

    scoped = list_entities(ctx, entity_type="bodies", component_name="body_comp")
    assert "listed_box" in scoped

    assert "No bodies found" in list_entities(
        ctx, entity_type="bodies", component_name="empty_comp"
    )
    assert "not found" in list_entities(
        ctx, entity_type="bodies", component_name="nonexistent_comp"
    )


def test_list_faces(ctx):
    """Test listing faces returns face IDs and surface types, and handles missing/disconnected cases."""
    # Not connected
    disconnected_ctx = MagicMock()
    disconnected_ctx.fastmcp._lifespan_result.product_instance = None
    assert "not connected" in list_entities(disconnected_ctx, "faces", body_name="box")

    # Missing body_name
    assert "required" in list_entities(ctx, "faces")

    # Body not found
    tools.create_design(ctx, "test_list_faces_001")
    assert "not found" in list_entities(ctx, "faces", body_name="nonexistent_body")

    # Valid body with faces
    tools.create_box(ctx, name="face_box", width=1.0, depth=1.0, height=1.0)
    result = list_entities(ctx, "faces", body_name="face_box")
    assert "id=" in result
    assert "surface_type=" in result
    # A box has 6 faces
    assert len(result.strip().splitlines()) == 6

    # Test method exception handling
    with patch(
        "ansys.geometry.mcp.tools.selection_tools.find_body", side_effect=Exception("Test error")
    ):
        result = list_entities(ctx, "faces", body_name="face_box")
        assert "Error" in result


def test_list_edges(ctx):
    """Test listing edges returns edge IDs and curve types, and handles missing/disconnected cases."""
    # Not connected
    disconnected_ctx = MagicMock()
    disconnected_ctx.fastmcp._lifespan_result.product_instance = None
    assert "not connected" in list_entities(disconnected_ctx, "edges", body_name="box")

    # Missing body_name
    assert "required" in list_entities(ctx, "edges")

    # Body not found
    tools.create_design(ctx, "test_list_edges_001")
    assert "not found" in list_entities(ctx, "edges", body_name="nonexistent_body")

    # Valid body with edges
    tools.create_box(ctx, name="edge_box", width=1.0, depth=1.0, height=1.0)
    result = list_entities(ctx, "edges", body_name="edge_box")
    assert "id=" in result
    assert "curve_type=" in result
    # A box has 12 edges
    assert len(result.strip().splitlines()) == 12

    # Test method exception handling
    with patch(
        "ansys.geometry.mcp.tools.selection_tools.find_body", side_effect=Exception("Test error")
    ):
        result = list_entities(ctx, "edges", body_name="edge_box")
        assert "Error" in result


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
    tools.create_design(ctx, "test_named_sel_001")
    tools.add_component(ctx, name="ns_comp")
    tools.create_box(
        ctx,
        name="ns_box",
        width=1.0,
        depth=1.0,
        height=1.0,
        parent_component_name="ns_comp",
    )
    tools.create_box(ctx, name="root_box", width=1.0, depth=1.0, height=1.0, origin=[5, 5, 5])

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

    # Test method exception handling
    with patch.object(design, "create_named_selection", side_effect=Exception("Test error")):
        result = create_named_selection(ctx, "ns_error", body_names=["ns_box"])
        assert "Error" in result

    box_body = find_body(design, "ns_box")
    root_box_body = find_body(design, "root_box")

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
