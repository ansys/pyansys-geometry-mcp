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

"""Unit tests for the selection tools."""

from unittest.mock import MagicMock, patch

import pytest

from ansys.geometry.mcp import tools
from ansys.geometry.mcp.context import PyAnsysGeometryContext
from ansys.geometry.mcp.misc.auxiliary import find_body
from ansys.geometry.mcp.tools import get_geometry_ctx
from ansys.geometry.mcp.tools.selection_tools import (
    create_named_selection,
    extend_selection,
    filter_entities,
    group_entities,
    list_entities,
    order_entities,
    select_entities,
)

from .conftest import add_component, create_box

# Every handle-based tool, with a criterion valid for bodies and its error prefix.
# "volume" on an edge is invalid for all of them, so it doubles as the unsupported case.
_HANDLE_TOOLS = [
    pytest.param(select_entities, "all", "Error selecting", id="select"),
    pytest.param(filter_entities, "is_solid", "Error filtering", id="filter"),
    pytest.param(order_entities, "volume", "Error ordering", id="order"),
    pytest.param(group_entities, "volume", "Error grouping", id="group"),
    pytest.param(extend_selection, "volume", "Error extending", id="extend"),
]


def _setup(ctx, design_name, box_name="box"):
    """Create a fresh design, a 1×1×1 m box, and a selection builder; return the handle."""
    tools.create_design(ctx, design_name)
    create_box(ctx, name=box_name, width=1.0, height=1.0, depth=1.0)
    return tools.create_selection_builder(ctx)


def _colored_box(ctx, design_name, box_name, color):
    """Create a box with a display color set; return the selection handle."""
    handle = _setup(ctx, design_name, box_name=box_name)
    design = get_geometry_ctx(ctx).product_instance.get_active_design()
    find_body(design, box_name).set_color(color)
    return handle


# ---------------------------------------------------------------------------
# Behaviour shared by every handle-based tool
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fn, criteria, error", _HANDLE_TOOLS)
def test_tool_not_connected(fn, criteria, error):
    """Each tool reports a disconnected backend instead of raising."""
    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result.product_instance = None
    assert "not connected" in fn(mock_ctx, "handle", "body", criteria=criteria)


@pytest.mark.parametrize("fn, criteria, error", _HANDLE_TOOLS)
def test_tool_invalid_handle(ctx: PyAnsysGeometryContext, fn, criteria, error):
    """Each tool rejects a selection handle that is not in the registry."""
    assert "Invalid selection handle" in fn(ctx, "not-a-real-handle", "body", criteria=criteria)


@pytest.mark.parametrize("fn, criteria, error", _HANDLE_TOOLS)
def test_tool_unsupported_criteria(ctx: PyAnsysGeometryContext, fn, criteria, error):
    """A criterion that does not apply to the entity type lists the supported ones."""
    handle = _setup(ctx, "test_unsupported_criteria")

    result = fn(ctx, handle, "edge", criteria="volume")
    assert "not supported" in result
    assert "entity_type 'edge'" in result


@pytest.mark.parametrize("fn, criteria, error", _HANDLE_TOOLS)
def test_tool_reports_backend_errors(ctx: PyAnsysGeometryContext, fn, criteria, error):
    """Tools preserve selections and record item updates even when reporting errors."""
    handle = _setup(ctx, "test_tool_backend_errors")
    select_entities(ctx, handle, "body", criteria="all")
    app_context = get_geometry_ctx(ctx)
    selection_builder = app_context.selection_registry[handle]
    selection = selection_builder.bodies

    with patch(
        "ansys.geometry.mcp.tools.selection_tools._identifiers",
        side_effect=Exception("Test error"),
    ):
        assert error in fn(ctx, handle, "body", criteria=criteria)
    assert selection_builder._bodies is selection
    assert [body.name for body in selection.items] == ["box"]
    result_name = {
        select_entities: "matching",
        filter_entities: "matching",
        order_entities: "ordered",
        group_entities: "groups",
        extend_selection: "extended",
    }[fn]
    assert app_context.command_history[-2].startswith(f"{result_name} = selection_builder.bodies.")
    result_items = (
        "[item for group in groups for item in group.items]"
        if fn is group_entities
        else f"{result_name}.items"
    )
    assert app_context.command_history[-1] == f"selection_builder._bodies.items[:] = {result_items}"


# ---------------------------------------------------------------------------
# select_entities
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "criteria, kwargs, matches",
    [
        ("all", {}, True),
        ("visible", {}, True),
        ("solid", {}, True),
        ("surface", {}, False),
        ("name", {"name": "sel_box"}, True),
        ("volume", {"min_value": 0.5, "max_value": 2.0}, True),
        ("volume", {"min_value": 100.0, "max_value": 200.0}, False),
        ("volume", {"min_value": 0.5}, True),
        ("surface_area", {"min_value": 5.0, "max_value": 7.0}, True),
        ("surface_area", {"min_value": 100.0, "max_value": 200.0}, False),
        # Centroid of a 1 m box extruded from the XY plane is (0, 0, 0.5).
        ("x_location", {"min_value": -0.1, "max_value": 0.1}, True),
        ("x_location", {"min_value": 50.0, "max_value": 100.0}, False),
        ("y_location", {"min_value": -0.1, "max_value": 0.1}, True),
        ("y_location", {"min_value": 50.0, "max_value": 100.0}, False),
        ("z_location", {"min_value": 0.4, "max_value": 0.6}, True),
        ("z_location", {"min_value": 50.0, "max_value": 100.0}, False),
    ],
)
def test_select_bodies_by_criteria(ctx: PyAnsysGeometryContext, criteria, kwargs, matches):
    """Each body criterion finds the box when it should and misses it when it should not."""
    handle = _setup(ctx, f"test_select_{criteria}", box_name="sel_box")
    selection_builder = get_geometry_ctx(ctx).selection_registry[handle]
    selection = selection_builder.bodies

    result = select_entities(ctx, handle, "body", criteria=criteria, **kwargs)
    assert isinstance(result, list)
    assert ("sel_box" in result) is matches
    assert selection_builder._bodies is selection
    assert [body.name for body in selection.items] == result


def test_select_bodies_named_selection_and_color(ctx: PyAnsysGeometryContext):
    """Both criteria need entities prepared first: a named selection group and a display color."""
    handle = _colored_box(ctx, "test_select_ns_color", "ns_color_box", "#FF0000")
    create_named_selection(ctx, "ns_group", body_names=["ns_color_box"])

    assert select_entities(
        ctx, handle, "body", criteria="named_selection", named_selection="ns_group"
    ) == ["ns_color_box"]
    assert "ns_color_box" in select_entities(ctx, handle, "body", criteria="color", color="#FF0000")


def test_select_faces_and_edges(ctx: PyAnsysGeometryContext):
    """Face and edge queries return IDs; their location queries also pass a range type."""
    handle = _setup(ctx, "test_select_faces_edges", box_name="fe_box")
    selection_builder = get_geometry_ctx(ctx).selection_registry[handle]
    face_selection = selection_builder.faces
    edge_selection = selection_builder.edges

    assert len(select_entities(ctx, handle, "face", criteria="all")) == 6
    assert len(select_entities(ctx, handle, "edge", criteria="all")) == 12

    faces = select_entities(
        ctx, handle, "face", criteria="z_location", min_value=-0.1, max_value=1.1
    )
    edges = select_entities(
        ctx, handle, "edge", criteria="z_location", min_value=-0.1, max_value=1.1
    )
    assert len(faces) > 0
    assert len(edges) > 0
    assert selection_builder._faces is face_selection
    assert selection_builder._edges is edge_selection
    assert [face.id for face in face_selection.items] == faces
    assert [edge.id for edge in edge_selection.items] == edges


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"criteria": "name"}, "Body name must be provided"),
        ({"criteria": "named_selection"}, "Named selection name must be provided"),
        ({"criteria": "color"}, "Color must be provided"),
        ({"criteria": "x_location"}, "At least one of min_value or max_value"),
    ],
)
def test_select_entities_missing_args(ctx: PyAnsysGeometryContext, kwargs, message):
    """Criteria that need an extra argument say which one is missing."""
    handle = _setup(ctx, "test_select_missing_args")

    assert message in select_entities(ctx, handle, "body", **kwargs)


@pytest.mark.parametrize(
    "entity_type, criteria, max_value, expected",
    [
        ("body", "volume", 2.0, 1),
        ("body", "surface_area", 7.0, 1),
        ("face", "area", 2.0, 6),
        ("edge", "length", 2.0, 12),
        ("body", "volume", 0.5, 0),
    ],
)
def test_select_measure_min_defaults_to_zero(
    ctx: PyAnsysGeometryContext, entity_type, criteria, max_value, expected
):
    """A measure criterion with only max_value is treated as [0, max_value]."""
    handle = _setup(ctx, f"test_select_min_default_{criteria}")

    result = select_entities(ctx, handle, entity_type, criteria=criteria, max_value=max_value)
    assert isinstance(result, list)
    assert len(result) == expected


# ---------------------------------------------------------------------------
# filter_entities
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "criteria, kwargs",
    [
        ("volume", {"min_value": 0.5, "max_value": 2.0}),
        ("volume", {"find_max": True}),
        ("volume", {"find_min": True}),
        ("surface_area", {"min_value": 5.0, "max_value": 7.0}),
        ("face_count", {"min_value": 1, "max_value": 10}),
        ("face_count", {"find_max": True}),
        ("edge_count", {"find_max": True}),
        ("loop_count", {"find_max": True}),
        ("surface_count", {"surface_type": "plane", "min_value": 1, "max_value": 10}),
        ("surface_count", {"surface_type": "plane", "find_max": True}),
        ("curve_count", {"curve_type": "line", "find_min": True}),
        ("name", {"name": "num_box"}),
        ("containing_surface_type", {"surface_type": "plane"}),
        ("containing_curve_type", {"curve_type": "line"}),
        ("is_solid", {}),
    ],
)
def test_filter_bodies_by_criteria(ctx: PyAnsysGeometryContext, criteria, kwargs):
    """Every body filter criterion retains the only box in the design."""
    handle = _setup(ctx, f"test_filter_{criteria}", box_name="num_box")
    select_entities(ctx, handle, "body", criteria="all")

    assert "num_box" in filter_entities(ctx, handle, "body", criteria=criteria, **kwargs)


def test_filter_bodies_excluding_criteria(ctx: PyAnsysGeometryContext):
    """A solid box is dropped by an out-of-range volume and by the surface-body filter."""
    handle = _setup(ctx, "test_filter_excluding", box_name="excl_box")

    select_entities(ctx, handle, "body", criteria="all")
    assert (
        filter_entities(ctx, handle, "body", criteria="volume", min_value=100.0, max_value=200.0)
        == []
    )

    select_entities(ctx, handle, "body", criteria="all")
    assert filter_entities(ctx, handle, "body", criteria="is_surface") == []
    assert get_geometry_ctx(ctx).selection_registry[handle].bodies.items == []


def test_filter_bodies_by_color(ctx: PyAnsysGeometryContext):
    """criteria='color' keeps the body once its display color has been set."""
    handle = _colored_box(ctx, "test_filter_color", "filter_color_box", "#00FF00")
    select_entities(ctx, handle, "body", criteria="all")

    assert "filter_color_box" in filter_entities(
        ctx, handle, "body", criteria="color", color="#00FF00"
    )


def test_filter_edges(ctx: PyAnsysGeometryContext):
    """All twelve edges of a 1 m box are 1 m long lines."""
    handle = _setup(ctx, "test_filter_edges", box_name="filter_edge_box")

    select_entities(ctx, handle, "edge", criteria="all")
    assert (
        len(filter_entities(ctx, handle, "edge", criteria="length", min_value=0.5, max_value=1.5))
        == 12
    )

    select_entities(ctx, handle, "edge", criteria="all")
    assert len(filter_entities(ctx, handle, "edge", criteria="curve_type", curve_type="line")) == 12


@pytest.mark.parametrize(
    "entity_type, criteria, kwargs, expected",
    [
        ("body", "volume", {"max_value": 2.0}, 1),
        ("body", "surface_area", {"max_value": 7.0}, 1),
        ("face", "area", {"max_value": 2.0}, 6),
        ("face", "perimeter", {"max_value": 5.0}, 6),
        ("edge", "length", {"max_value": 2.0}, 12),
        ("body", "volume", {"max_value": 0.5}, 0),
        ("face", "edge_count", {"max_value": 4}, 6),
        ("body", "surface_count", {"surface_type": "plane", "max_value": 6}, 1),
        ("body", "surface_count", {"surface_type": "plane"}, 1),
    ],
)
def test_filter_range_min_defaults_to_zero(
    ctx: PyAnsysGeometryContext, entity_type, criteria, kwargs, expected
):
    """A range filter without min_value is treated as [0, max_value]."""
    handle = _setup(ctx, f"test_filter_min_default_{criteria}")
    select_entities(ctx, handle, entity_type, criteria="all")

    result = filter_entities(ctx, handle, entity_type, criteria=criteria, **kwargs)
    assert isinstance(result, list)
    assert len(result) == expected


@pytest.mark.parametrize(
    "entity_type, kwargs, message",
    [
        ("body", {"criteria": "name"}, "name must be provided"),
        ("body", {"criteria": "color"}, "color must be provided"),
        ("body", {"criteria": "containing_surface_type"}, "surface_type must be provided"),
        ("body", {"criteria": "containing_curve_type"}, "curve_type must be provided"),
        ("body", {"criteria": "surface_count"}, "surface_type must be provided"),
        ("body", {"criteria": "curve_count"}, "curve_type must be provided"),
        (
            "body",
            {"criteria": "volume", "find_max": True, "find_min": True},
            "Cannot set both",
        ),
        (
            "body",
            {
                "criteria": "surface_count",
                "surface_type": "plane",
                "find_max": True,
                "find_min": True,
            },
            "Cannot set both",
        ),
        ("edge", {"criteria": "curve_type"}, "curve_type must be provided"),
    ],
)
def test_filter_entities_missing_args(ctx: PyAnsysGeometryContext, entity_type, kwargs, message):
    """Criteria that need an extra argument or a single find flag say what is wrong."""
    handle = _setup(ctx, "test_filter_missing_args")
    select_entities(ctx, handle, entity_type, criteria="all")

    assert message in filter_entities(ctx, handle, entity_type, **kwargs)


# ---------------------------------------------------------------------------
# order_entities and group_entities
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "entity_type, kwargs, count",
    [
        ("body", {"criteria": "volume"}, 1),
        ("body", {"criteria": "face_count"}, 1),
        ("body", {"criteria": "surface_count"}, 1),
        ("body", {"criteria": "curve_count"}, 1),
        ("face", {"criteria": "area"}, 6),
        ("face", {"criteria": "perimeter"}, 6),
        ("face", {"criteria": "curve_count", "curve_type": "line"}, 6),
        ("edge", {"criteria": "length"}, 12),
    ],
)
def test_order_entities(ctx: PyAnsysGeometryContext, entity_type, kwargs, count):
    """Ordering returns every selected entity, just rearranged."""
    handle = _setup(ctx, "test_order_entities", box_name="order_box")
    select_entities(ctx, handle, entity_type, criteria="all")
    selection_builder = get_geometry_ctx(ctx).selection_registry[handle]
    attr = {"body": "bodies", "face": "faces", "edge": "edges"}[entity_type]
    selection = getattr(selection_builder, attr)

    ordered = order_entities(ctx, handle, entity_type, **kwargs)
    assert isinstance(ordered, list)
    assert len(ordered) == count
    assert getattr(selection_builder, f"_{attr}") is selection
    assert [item.name if entity_type == "body" else item.id for item in selection.items] == ordered


def test_order_faces_curve_count_requires_curve_type(ctx: PyAnsysGeometryContext):
    """The face curve_count criterion is the only ordering rule taking an argument."""
    handle = _setup(ctx, "test_order_missing_arg")
    select_entities(ctx, handle, "face", criteria="all")

    assert "curve_type must be provided" in order_entities(
        ctx, handle, "face", criteria="curve_count"
    )


def test_order_bodies_curve_count_rejects_curve_type(ctx: PyAnsysGeometryContext):
    """Body curve_count counts every curve, so a curve_type is refused instead of ignored."""
    handle = _setup(ctx, "test_order_body_curve_type")
    select_entities(ctx, handle, "body", criteria="all")

    assert "curve_type is not supported" in order_entities(
        ctx, handle, "body", criteria="curve_count", curve_type="line"
    )


@pytest.mark.parametrize(
    "tool, entity_type, criteria",
    [
        (filter_entities, "body", "number_surfaces"),
        (filter_entities, "face", "number_curves"),
        (order_entities, "body", "number_of_surfaces"),
        (order_entities, "body", "number_of_curves"),
        (order_entities, "face", "number_curves"),
        (extend_selection, "body", "number_of_faces"),
        (extend_selection, "face", "number_of_loops"),
    ],
)
def test_legacy_count_criteria_rejected(ctx: PyAnsysGeometryContext, tool, entity_type, criteria):
    """Count criteria share the *_count names, and the error points to them."""
    handle = _setup(ctx, "test_legacy_count_names")
    select_entities(ctx, handle, entity_type, criteria="all")

    message = tool(ctx, handle, entity_type, criteria=criteria)
    assert f"Criterion '{criteria}' is not supported" in message
    assert "_count" in message


@pytest.mark.parametrize(
    "entity_type, criteria, count",
    [
        ("body", "volume", 1),
        ("body", "name", 1),
        ("face", "body", 6),
        ("face", "area", 6),
        ("edge", "curve_type", 12),
    ],
)
def test_group_entities(ctx: PyAnsysGeometryContext, entity_type, criteria, count):
    """Grouping partitions the selection, so the group sizes add up to the selection size."""
    handle = _setup(ctx, "test_group_entities", box_name="group_box")
    select_entities(ctx, handle, entity_type, criteria="all")
    selection_builder = get_geometry_ctx(ctx).selection_registry[handle]
    attr = {"body": "bodies", "face": "faces", "edge": "edges"}[entity_type]
    selection = getattr(selection_builder, attr)

    groups = group_entities(ctx, handle, entity_type, criteria=criteria)
    assert isinstance(groups, list)
    assert sum(len(group) for group in groups) == count
    assert getattr(selection_builder, f"_{attr}") is selection
    assert [item.name if entity_type == "body" else item.id for item in selection.items] == [
        identifier for group in groups for identifier in group
    ]


# ---------------------------------------------------------------------------
# extend_selection
# ---------------------------------------------------------------------------


def test_extend_bodies_by_shared_property(ctx: PyAnsysGeometryContext):
    """Two identical boxes: extending from one by volume pulls in the other."""
    handle = _setup(ctx, "test_extend_shared", box_name="extend_box")
    create_box(ctx, name="extend_twin", width=1.0, height=1.0, depth=1.0)

    select_entities(ctx, handle, "body", criteria="name", name="extend_box")
    extended = extend_selection(ctx, handle, "body", criteria="volume")
    assert "extend_box" in extended
    assert "extend_twin" in extended


def test_extend_bodies_nearby(ctx: PyAnsysGeometryContext):
    """nearby is the only rule taking a distance, and the backend has no proximity search."""
    handle = _setup(ctx, "test_extend_nearby", box_name="nearby_box")
    select_entities(ctx, handle, "body", criteria="all")

    assert "distance must be provided" in extend_selection(ctx, handle, "body", criteria="nearby")
    assert "not supported for CoreService backends" in extend_selection(
        ctx, handle, "body", criteria="nearby", distance=5.0
    )

    # Stand in for the missing backend support to check the call is transcribed.
    selection = get_geometry_ctx(ctx).selection_registry[handle].bodies
    with patch.object(selection, "extend_nearby_bodies", return_value=selection):
        assert isinstance(
            extend_selection(ctx, handle, "body", criteria="nearby", distance=5.0), list
        )
    assert 'extend_nearby_bodies(5.0, "all")' in tools.get_session_script(ctx)


@pytest.mark.parametrize(
    "entity_type, criteria",
    [
        ("body", "surface_area"),
        ("body", "face_count"),
        ("body", "edge_count"),
        ("face", "area"),
        ("face", "edge_count"),
        ("face", "loop_count"),
        ("face", "coincident"),
        ("edge", "tangent_chain"),
    ],
)
def test_extend_selection_criteria(ctx: PyAnsysGeometryContext, entity_type, criteria):
    """Every remaining extend rule returns a list rather than an error string."""
    handle = _setup(ctx, "test_extend_criteria", box_name="extend_crit_box")
    select_entities(ctx, handle, entity_type, criteria="all")
    selection_builder = get_geometry_ctx(ctx).selection_registry[handle]
    attr = {"body": "bodies", "face": "faces", "edge": "edges"}[entity_type]
    selection = getattr(selection_builder, attr)

    extended = extend_selection(ctx, handle, entity_type, criteria=criteria)
    assert isinstance(extended, list)
    assert getattr(selection_builder, f"_{attr}") is selection
    assert [item.name if entity_type == "body" else item.id for item in selection.items] == extended


# ---------------------------------------------------------------------------
# list_entities
# ---------------------------------------------------------------------------


def test_list_bodies_and_components(ctx: PyAnsysGeometryContext):
    """Bodies can be listed design-wide or scoped to a component; components list as a tree."""
    tools.create_design(ctx, "test_list_bodies_001")
    add_component(ctx, name="body_comp")
    add_component(ctx, name="empty_comp")
    create_box(
        ctx, name="listed_box", width=1.0, depth=1.0, height=1.0, parent_component_name="body_comp"
    )

    assert "listed_box" in list_entities(ctx, entity_type="body")
    assert "listed_box" in list_entities(ctx, entity_type="body", component_name="body_comp")
    assert "body_comp" in list_entities(ctx, entity_type="component")

    assert "No bodies found" in list_entities(ctx, entity_type="body", component_name="empty_comp")
    assert "not found" in list_entities(ctx, entity_type="body", component_name="nonexistent_comp")


@pytest.mark.parametrize(
    "entity_type, detail, count",
    [("face", "surface_type=", 6), ("edge", "curve_type=", 12)],
)
def test_list_faces_and_edges(ctx: PyAnsysGeometryContext, entity_type, detail, count):
    """Listing returns one ID line per entity, and reports missing bodies and backend errors."""
    disconnected_ctx = MagicMock()
    disconnected_ctx.fastmcp._lifespan_result.product_instance = None
    assert "not connected" in list_entities(disconnected_ctx, entity_type, body_name="box")

    assert "required" in list_entities(ctx, entity_type)

    tools.create_design(ctx, f"test_list_{entity_type}_001")
    assert "not found" in list_entities(ctx, entity_type, body_name="nonexistent_body")

    create_box(ctx, name="list_box", width=1.0, depth=1.0, height=1.0)
    result = list_entities(ctx, entity_type, body_name="list_box")
    assert "id=" in result
    assert detail in result
    assert len(result.strip().splitlines()) == count

    with patch(
        "ansys.geometry.mcp.tools.selection_tools.find_body", side_effect=Exception("Test error")
    ):
        assert "Error" in list_entities(ctx, entity_type, body_name="list_box")


# ---------------------------------------------------------------------------
# create_named_selection
# ---------------------------------------------------------------------------


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


def test_create_named_selection_from_selection_handle(ctx: PyAnsysGeometryContext):
    """A selection built via create_selection_builder/select_entities can be saved by handle,
    merged with explicit entities, and reports invalid handles or empty selections."""
    assert "Invalid selection handle" in create_named_selection(
        ctx, "ns_bad_handle", selection_handle="not-a-real-handle"
    )

    handle = _setup(ctx, "test_named_sel_handle", box_name="handle_box")
    assert "no entities selected" in create_named_selection(
        ctx, "ns_empty_selection", selection_handle=handle
    )

    select_entities(ctx, handle, "body", criteria="all")
    result = create_named_selection(ctx, "ns_from_handle", selection_handle=handle)
    assert "created successfully" in result

    # Faces from the handle merge with an explicitly named body.
    select_entities(ctx, handle, "face", criteria="all")
    create_box(ctx, name="extra_box", width=1.0, depth=1.0, height=1.0, origin=[5, 5, 5])
    result = create_named_selection(
        ctx, "ns_from_handle_mixed", selection_handle=handle, body_names=["extra_box"]
    )
    assert "created successfully" in result

    history = tools.get_session_script(ctx)
    assert "create_named_selection" in history
    assert "ns_from_handle_mixed" in history
