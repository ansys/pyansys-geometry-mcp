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

"""MCP selection tools for PyAnsys Geometry-MCP.

Each function decorated with ``@app.tool()`` is exposed as an MCP tool.
The ``ctx`` parameter provides access to the app context (and thus
to the live product instance and command history).

The query/filter/order/group/extend tools all take an ``entity_type`` of
``"body"``, ``"face"``, or ``"edge"`` and dispatch to the matching typed
selection on the selection builder. Not every criterion applies to every
entity type. The tools report the supported criteria when given a bad
combination.

How to add a tool
-----------------
1. Define a Python function with type-annotated parameters.
2. Add a NumPy-style docstring. The summary line becomes the tool description
   visible to the AI assistant.
3. Decorate it with ``@app.tool()``.
4. Access the product instance::

       app_context = ctx.fastmcp._lifespan_result
       instance = app_context.product_instance

Notes
-----
Import this module in ``__main__.py`` to register all tools
with the server before it starts.

"""

from typing import Literal
import uuid

from ansys.common.mcp.logging_config import get_logger
from fastmcp.server import Context

from ansys.geometry.mcp import app
from ansys.geometry.mcp.misc.auxiliary import find_bodies_by_id, get_geometry_ctx
from ansys.geometry.mcp.misc.selection_enums import (
    _CURVE_TYPE_MAP,
    _DEFAULT_RANGE_TYPE,
    _SCOPE_MAP,
    _SURFACE_TYPE_MAP,
)

logger = get_logger(__name__)

EntityType = Literal["body", "face", "edge"]

# Attribute on SelectionBuilder holding the typed selection, and the attribute the
# result is written back to.
_SELECTION_ATTR = {"body": "bodies", "face": "faces", "edge": "edges"}
_RESULT_ATTR = {"body": "_bodies", "face": "_faces", "edge": "_edges"}

_SELECT_METHODS = {
    "body": {
        "all": "get_all_bodies",
        "visible": "get_all_visible_bodies",
        "solid": "get_all_solid_bodies",
        "surface": "get_all_surface_bodies",
        "named_selection": "get_bodies_from_named_selection",
        "name": "get_bodies_with_name",
        "volume": "get_bodies_with_volume",
        "surface_area": "get_bodies_with_surface_area",
        "x_location": "get_bodies_with_x_location",
        "y_location": "get_bodies_with_y_location",
        "z_location": "get_bodies_with_z_location",
        "color": "get_bodies_with_color",
    },
    "face": {
        "all": "get_all_faces",
        "visible": "get_all_visible_faces",
        "named_selection": "get_faces_from_named_selection",
        "area": "get_faces_with_area",
        "x_location": "get_faces_with_x_location",
        "y_location": "get_faces_with_y_location",
        "z_location": "get_faces_with_z_location",
        "color": "get_faces_with_color",
    },
    "edge": {
        "all": "get_all_edges",
        "visible": "get_all_visible_edges",
        "named_selection": "get_edges_from_named_selection",
        "length": "get_edges_with_length",
        "x_location": "get_edges_with_x_location",
        "y_location": "get_edges_with_y_location",
        "z_location": "get_edges_with_z_location",
    },
}

_SELECT_NO_ARG = ("all", "visible", "solid", "surface")
_MEASURE_CRITERIA = ("volume", "surface_area", "area", "perimeter", "length")
_LOCATION_CRITERIA = ("x_location", "y_location", "z_location")

# Criteria supporting min/max ranges plus find_max/find_min, per entity type.
_FILTER_RANGE_CRITERIA = {
    "body": ("volume", "surface_area", "face_count", "edge_count", "loop_count"),
    "face": ("area", "perimeter", "edge_count", "loop_count"),
    "edge": ("length",),
}
# Criteria counting entities of a given surface/curve type.
_FILTER_TYPED_COUNT_CRITERIA = {
    "body": ("number_surfaces", "number_curves"),
    "face": ("number_curves",),
    "edge": (),
}
# Criteria taking no numeric range.
_FILTER_OTHER_CRITERIA = {
    "body": (
        "color",
        "name",
        "containing_surface_type",
        "containing_curve_type",
        "is_surface",
        "is_solid",
    ),
    "face": ("color", "containing_curve_type"),
    "edge": ("curve_type",),
}
# Count-based criteria the backend expects as integers.
_INT_CRITERIA = ("face_count", "edge_count", "loop_count", "number_surfaces", "number_curves")

_ORDER_CRITERIA = {
    "body": (
        "volume",
        "surface_area",
        "face_count",
        "edge_count",
        "loop_count",
        "number_of_surfaces",
        "number_of_curves",
    ),
    "face": ("area", "perimeter", "edge_count", "loop_count", "number_curves"),
    "edge": ("length",),
}

_GROUP_CRITERIA = {
    "body": (
        "volume",
        "surface_area",
        "face_count",
        "edge_count",
        "loop_count",
        "color",
        "name",
    ),
    "face": ("area", "perimeter", "body", "edge_count", "loop_count", "color", "coincident"),
    "edge": ("curve_type",),
}

_EXTEND_METHODS = {
    "body": {
        "volume": "extend_to_same_volume",
        "surface_area": "extend_to_same_surface_area",
        "number_of_faces": "extend_to_same_number_of_faces",
        "number_of_edges": "extend_to_same_number_of_edges",
        "color": "extend_to_same_color",
        "name": "extend_to_same_name",
        "nearby": "extend_nearby_bodies",
    },
    "face": {
        "area": "extend_to_same_area",
        "number_of_edges": "extend_to_same_number_of_edges",
        "number_of_loops": "extend_to_same_number_of_loops",
        "color": "extend_to_same_color",
        "coincident": "extend_to_coincident",
        "coaxial": "extend_to_coaxial_faces",
    },
    "edge": {
        "nearby": "extend_nearby_edges",
        "connected": "extend_to_connected",
        "tangent_chain": "extend_to_tangent_chain",
        "coaxial": "extend_to_coaxial_edges",
    },
}


def _unsupported(criteria: str, entity_type: str, supported) -> str:
    return (
        f"Criterion '{criteria}' is not supported for entity_type '{entity_type}'. "
        f"Supported criteria: {', '.join(sorted(supported))}."
    )


def _identifiers(selection) -> list[str]:
    """Return the IDs of the selected bodies, faces, or edges."""
    return [item.id for item in selection.items]


def _component_tree(node, indent: int) -> list[str]:
    lines = []
    for comp in node.components:
        lines.append("  " * indent + f"id={comp.id}  name={comp.name}")
        lines.extend(_component_tree(comp, indent + 1))
    return lines


def _body_paths(node, prefix: str, name: str | None = None) -> list[str]:
    lines = [
        f"id={body.id}  path={prefix}{body.name}"
        for body in node.bodies
        if name is None or body.name.casefold() == name.casefold()
    ]
    for comp in node.components:
        lines.extend(_body_paths(comp, f"{prefix}{comp.name}/", name))
    return lines


@app.tool()
def list_entities(
    ctx: Context,
    entity_type: Literal["body", "component", "face", "edge"],
    body_id: str | None = None,
    component_id: str | None = None,
    name: str | None = None,
) -> str:
    """List the entities of a given type in the active design.

    This is the discovery tool. Use it to find the exact body and component IDs and names,
    face IDs, and edge IDs that every other tool expects as input.
    Body and component names need not be unique, so other tools take IDs.

    Users refer to bodies by name. To turn a body name into its ID, call this
    tool with ``entity_type="body"`` and ``name`` set to that name. If more than
    one body matches, use the component path to tell them apart, or ask the
    user which one they mean.

    Behavior per ``entity_type``:
    - ``"body"``: ``id=<body id>  path=<component path>/<body name>`` for every
      body, e.g. ``id=0:12  path=MainComponent/Cylinder``. Pass ``name`` to
      list only bodies with that name, and ``component_id`` to restrict the
      listing to one component and its children.
    - ``"component"``: the component hierarchy as an indented tree of
      ``id=<component id>  name=<component name>`` lines. Component names
      need not be unique, so use the ID to refer to a component.
    - ``"face"``: ``id=<face id>  surface_type=<type>`` for every face of
      ``body_id``. Use it whenever a face ID is needed, or to answer
      questions about how many faces a body has or which faces are planes,
      cylinders, cones, and so on.
    - ``"edge"``: ``id=<edge id>  curve_type=<type>`` for every edge of
      ``body_id``. Use it whenever an edge ID is needed, or to answer
      questions about how many edges a body has or which edges are lines,
      circles, arcs, and so on.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    entity_type : str
        Kind of entity to select. Options are ``"body"``, ``"component"``,
        ``"face"``, and ``"edge"``.
    body_id : str, default: None
        ID of the body to inspect. Required for ``"face"`` and ``"edge"``,
        ignored otherwise. List the bodies first to discover valid IDs.
    component_id : str, default: None
        ID of a component to restrict a ``"body"`` listing to, together with its
        children. List the components first to discover IDs. Ignored for the
        other entity types.
    name : str, default: None
        Body name to look up; only bodies with exactly this name (ignoring
        case) are listed. Ignored for the other entity types.

    Returns
    -------
    str
        Newline-separated listing, or an error message.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return f"Product backend is not connected. Cannot list {entity_type} entities."

    if entity_type in ("face", "edge") and body_id is None:
        return f"'body_id' is required when listing {entity_type} entities."

    try:
        design = app_context.product_instance.get_active_design()
        logger.info(f"list_entities: entity_type={entity_type!r}, body_id={body_id!r}")

        if entity_type == "component":
            lines = _component_tree(design, 0)
            return "\n".join(lines) if lines else "No components found in the active design."

        if entity_type == "body":
            if component_id is None:
                root = design
            else:
                from ansys.geometry.core.misc.auxiliary import get_components_from_ids

                matches = get_components_from_ids(design, [component_id])
                if not matches:
                    return f"Component ID '{component_id}' not found."
                root = matches[0]
            lines = _body_paths(root, "", name)
            if lines:
                return "\n".join(lines)
            return f"No bodies named '{name}' found." if name else "No bodies found."

        found, _ = find_bodies_by_id(design, [body_id])
        if not found:
            return (
                f"Body ID '{body_id}' not found. "
                "Use list_entities with entity_type='body' to see available bodies."
            )
        body = found[0]

        if entity_type == "face":
            lines = [f"id={face.id}  surface_type={face.surface_type.name}" for face in body.faces]
            return "\n".join(lines) if lines else f"Body '{body_id}' has no faces."

        lines = [f"id={edge.id}  curve_type={edge.curve_type.name}" for edge in body.edges]
        return "\n".join(lines) if lines else f"Body '{body_id}' has no edges."
    except Exception as e:
        logger.error(f"list_entities failed: {e}")
        return f"Error listing {entity_type} entities: {e}"


@app.tool()
def create_selection_builder(ctx: Context) -> str:
    """Create an empty selection builder in the product backend.

    Use a selection builder when a selection request needs multiple query or refinement
    steps. Start with ``select_entities``, refine with ``filter_entities`` or add related
    entities with ``extend_selection``, and use ``order_entities`` or ``group_entities``
    when ranking or grouping is useful. Save the final set with ``create_named_selection``.
    If the requested entities are already known by name or ID and only need a label, call
    ``create_named_selection`` directly without a builder.

    Call this tool only to start a brand-new selection. If a selection builder already
    exists from earlier in this conversation, reuse its handle in the other
    selection tools instead of calling it again.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).

    Returns
    -------
    str
        Selection handle (opaque ID string) that can be used in subsequent selection tools, or an
        error message if creation fails.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot create selection builder."

    try:
        selection_builder = app_context.product_instance.create_selection_builder()

        # Create a handle for the selection builder to be used in other tools
        handle = str(uuid.uuid4())
        app_context.selection_registry[handle] = selection_builder

        # Perform transcript
        app_context.command_history.append("selection_builder=instance.create_selection_builder()")
        app_context.command_history.append(f"handle = '{handle}'")
        app_context.command_history.append(f"selection_registry['{handle}'] = selection_builder")

        logger.info("create_selection_builder called")
        return handle
    except Exception as e:
        logger.error(f"create_selection_builder failed: {e}")
        return f"Error creating selection builder: {e}"


@app.tool()
def select_entities(
    ctx: Context,
    selection_handle: str,
    entity_type: EntityType,
    criteria: Literal[
        "all",
        "visible",
        "solid",
        "surface",
        "named_selection",
        "name",
        "volume",
        "surface_area",
        "area",
        "length",
        "x_location",
        "y_location",
        "z_location",
        "color",
    ],
    name: str | None = None,
    named_selection: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    color: str | None = None,
) -> list[str] | str:
    """Query the design for entities matching a property and store them in a selection builder.

    Query the design for the starting set of bodies, faces, or edges in a selection
    workflow. The result replaces the builder's current selection for that entity type.
    Follow with ``filter_entities`` to narrow the set, ``extend_selection`` to add
    related entities, or ``create_named_selection`` to save the final set. Pass one
    ``criteria`` value with its one or more corresponding arguments. Available criteria depend
    on ``entity_type``.

    Criteria by ``entity_type``:

    - ``"body"``: ``all``, ``visible``, ``solid``, ``surface``, ``named_selection``,
      ``name``, ``volume``, ``surface_area``, ``x_location``, ``y_location``,
      ``z_location``, ``color``
    - ``"face"``: ``all``, ``visible``, ``named_selection``, ``area``,
      ``x_location``, ``y_location``, ``z_location``, ``color``
    - ``"edge"``: ``all``, ``visible``, ``named_selection``, ``length``,
      ``x_location``, ``y_location``, ``z_location``

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    selection_handle : str
        Handle of the selection builder to use for this query. Reuse the handle
        from the most recent ``create_selection_builder`` call in this
        conversation rather than creating a new one.
    entity_type : str
        Kind of entity to select. Options are ``"body"``, ``"face"``, and ``"edge"``.
    criteria : str
        Selection rule to apply:

        ``"all"``
            Every entity of that type in the design. No extra arguments are needed.
        ``"visible"``
            All currently visible entities. No extra arguments are needed.
        ``"solid"``
            Solid (volumetric) bodies. Bodies only.
        ``"surface"``
            Surface (sheet) bodies. Bodies only.
        ``"named_selection"``
            Entities belonging to a named selection group. Requires ``named_selection``.
        ``"name"``
            Bodies whose name matches exactly. Bodies only. Requires ``name``.
        ``"volume"``
            Bodies whose volume falls in [``min_value``, ``max_value``] (m³).
            Requires ``min_value``.
        ``"surface_area"``
            Bodies whose surface area falls in [``min_value``, ``max_value``] (m²).
            Requires ``min_value``.
        ``"area"``
            Faces whose area falls in [``min_value``, ``max_value``] (m²).
            Requires ``min_value``.
        ``"length"``
            Edges whose length falls in [``min_value``, ``max_value``] (m).
            Requires ``min_value``.
        ``"x_location"``, ``"y_location"``, ``"z_location"``
            Entities whose centroid coordinate on the specified axis falls in
            [``min_value``, ``max_value``] (m). Requires at least one of
            ``min_value`` or ``max_value``.
        ``"color"``
            Bodies or faces with a specific display color. Requires ``color``.
    name : str, default: None
        Body name for the ``"name"`` criterion.
    named_selection : str, default: None
        Named selection label for the ``"named_selection"`` criterion.
    min_value : float, default: None
        Lower bound (inclusive) for range-based criteria.
    max_value : float, default: None
        Upper bound (inclusive) for range-based criteria.
        Pass ``None`` to leave the upper bound open.
    color : str, default: None
        Hex color string for the ``"color"`` criterion, such as ``"#FF0000"``.

    Returns
    -------
    list of str | str
        Body names or face/edge IDs for every match. If no entities match, an empty list
        is returned.

        If the selection handle is invalid, the criterion does not apply to the entity type,
        or required arguments are missing, a string error message is returned.

    Examples
    --------
    All solid bodies:
        ``select_entities(entity_type="body", criteria="solid")``

    All faces of the design:
        ``select_entities(entity_type="face", criteria="all")``

    Edges longer than 0.01 m:
        ``select_entities(entity_type="edge", criteria="length", min_value=0.01)``

    Bodies whose centroid is at Z > 0.05 m:
        ``select_entities(entity_type="body", criteria="z_location", min_value=0.05)``

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return f"Product backend is not connected. Cannot select {entity_type} entities."

    try:
        selection_builder = app_context.selection_registry.get(selection_handle)
        app_context.command_history.append(
            f"selection_builder = selection_registry['{selection_handle}']"
        )
        if selection_builder is None:
            return f"Invalid selection handle: {selection_handle}"

        methods = _SELECT_METHODS[entity_type]
        method_name = methods.get(criteria)
        if method_name is None:
            return _unsupported(criteria, entity_type, methods)

        attr = _SELECTION_ATTR[entity_type]
        selection = getattr(selection_builder, attr)
        method = getattr(selection, method_name)

        if criteria in _SELECT_NO_ARG:
            matching = method()
            call = f"{method_name}()"
        elif criteria == "named_selection":
            if not named_selection:
                return "Named selection name must be provided for 'named_selection' criterion."
            matching = method(named_selection)
            call = f"{method_name}('{named_selection}')"
        elif criteria == "name":
            if not name:
                return "Body name must be provided for 'name' criterion."
            matching = method(name)
            call = f"{method_name}('{name}')"
        elif criteria in _MEASURE_CRITERIA:
            if min_value is None:
                return f"min_value must be provided for '{criteria}' criterion."
            matching = method(min_value, max_value)
            call = f"{method_name}({min_value}, {max_value})"
        elif criteria in _LOCATION_CRITERIA:
            if min_value is None and max_value is None:
                return (
                    f"At least one of min_value or max_value must be provided "
                    f"for '{criteria}' criterion."
                )
            if entity_type == "body":
                matching = method(min=min_value, max=max_value)
                call = f"{method_name}(min={min_value}, max={max_value})"
            else:
                matching = method(_DEFAULT_RANGE_TYPE, min=min_value, max=max_value)
                call = (
                    f"{method_name}(RangeType.RANGETYPE_INTERSECT, "
                    f"min={min_value}, max={max_value})"
                )
        elif criteria == "color":
            if not color:
                return "Color must be provided for 'color' criterion."
            matching = method(color)
            call = f"{method_name}('{color}')"

        app_context.command_history.append(f"matching = selection_builder.{attr}.{call}")
        getattr(selection_builder, _RESULT_ATTR[entity_type]).items[:] = matching.items
        app_context.command_history.append(
            f"selection_builder.{_RESULT_ATTR[entity_type]}.items[:] = matching.items"
        )
        logger.info(
            f"Selected {len(matching.items)} {entity_type} entities using criterion '{criteria}'."
        )
        return _identifiers(matching)
    except Exception as e:
        logger.error(f"Error selecting {entity_type} entities: {e}")
        return f"Error selecting {entity_type} entities: {e}"


@app.tool()
def filter_entities(
    ctx: Context,
    selection_handle: str,
    entity_type: EntityType,
    criteria: Literal[
        "volume",
        "surface_area",
        "area",
        "perimeter",
        "length",
        "face_count",
        "edge_count",
        "loop_count",
        "number_surfaces",
        "number_curves",
        "color",
        "name",
        "containing_surface_type",
        "containing_curve_type",
        "curve_type",
        "is_surface",
        "is_solid",
    ],
    name: str | None = None,
    find_max: bool | None = None,
    find_min: bool | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    surface_type: Literal[
        "plane", "cylinder", "cone", "torus", "sphere", "nurbs", "procedural", "spline"
    ]
    | None = None,
    curve_type: Literal["line", "circle", "ellipse", "nurbs", "procedural", "helix", "spline"]
    | None = None,
    color: str | None = None,
) -> list[str] | str:
    """Narrow the entities already held in a selection builder to those matching a condition.

    Unlike ``select_entities``, which queries the whole design, this tool only keeps
    a subset of the current selection. It does not search the design for new entities.
    Populate the builder with ``select_entities`` or another selection operation first.
    Use ``extend_selection`` when the request is to add related entities. Use
    ``create_named_selection`` to save the resulting set.

    Criteria by ``entity_type``:

    - ``"body"``: ``volume``, ``surface_area``, ``face_count``, ``edge_count``,
      ``loop_count``, ``number_surfaces``, ``number_curves``, ``color``, ``name``,
      ``containing_surface_type``, ``containing_curve_type``, ``is_surface``, ``is_solid``
    - ``"face"``: ``area``, ``perimeter``, ``edge_count``, ``loop_count``,
      ``number_curves``, ``color``, ``containing_curve_type``
    - ``"edge"``: ``length``, ``curve_type``

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    selection_handle : str
        Handle of the selection builder to use for this query. Reuse the handle
        from the most recent ``create_selection_builder`` call in this
        conversation rather than creating a new one.
    entity_type : str
        Kind of entity to filter. Options are ``"body"``, ``"face"``, and ``"edge"``.
    criteria : str
        Filter rule to apply:

        ``"volume"``, ``"surface_area"``, ``"area"``, ``"perimeter"``, ``"length"``
            Keep entities whose measurement falls in [``min_value``, ``max_value``],
            or the single largest/smallest when ``find_max``/``find_min`` is ``True``.
        ``"face_count"``, ``"edge_count"``, ``"loop_count"``
            Keep entities with a count in [``min_value``, ``max_value``], or the
            largest/smallest when ``find_max``/``find_min`` is ``True``.
        ``"number_surfaces"``
            Keep bodies by how many surfaces of ``surface_type`` they contain.
            Requires ``surface_type``.
        ``"number_curves"``
            Keep bodies or faces by how many curves of ``curve_type`` they contain.
            Requires ``curve_type``.
        ``"color"``
            Keep bodies or faces with a specific display color. Requires ``color``.
        ``"name"``
            Keep bodies whose name matches exactly. Bodies only. Requires ``name``.
        ``"containing_surface_type"``
            Keep bodies containing a surface of ``surface_type``. Bodies only.
        ``"containing_curve_type"``
            Keep bodies or faces containing a curve of ``curve_type``.
        ``"curve_type"``
            Keep edges of the given ``curve_type``. Edges only.
        ``"is_surface"`` / ``"is_solid"``
            Keep only surface or only solid bodies. Bodies only.
    name : str, default: None
        Body name for the ``"name"`` criterion.
    find_max : bool, default: False
        Keep only the entity with the maximum value of the criterion.
    find_min : bool, default: False
        Keep only the entity with the minimum value of the criterion.
    min_value : float, default: None
        Lower bound (inclusive) for range-based criteria.
    max_value : float, default: None
        Upper bound (inclusive) for range-based criteria.
    surface_type : str, default: None
        Surface type for the ``"number_surfaces"`` and ``"containing_surface_type"`` criteria.
    curve_type : str, default: None
        Curve type for the ``"number_curves"``, ``"containing_curve_type"``, and
        ``"curve_type"`` criteria.
    color : str, default: None
        Hex color string for the ``"color"`` criterion, e.g. ``"#FF0000"``.

    Returns
    -------
    list of str | str
        Body names or face/edge IDs that survive the filter. If no entities survive
        the filter, an empty list is returned.

        If the selection handle is invalid, the criterion does not apply to the entity type, or
        required arguments are missing, a string error message is returned.

    Examples
    --------
    Keep only bodies with volume of at least 100 m³ (drops the smaller ones):
        ``filter_entities(entity_type="body", criteria="volume", min_value=100)``

    Keep only the single largest face by area:
        ``filter_entities(entity_type="face", criteria="area", find_max=True)``

    Keep only solid bodies:
        ``filter_entities(entity_type="body", criteria="is_solid")``

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return f"Product backend is not connected. Cannot filter {entity_type} entities."

    try:
        selection_builder = app_context.selection_registry.get(selection_handle)
        app_context.command_history.append(
            f"selection_builder = selection_registry['{selection_handle}']"
        )
        if selection_builder is None:
            return f"Invalid selection handle: {selection_handle}"

        range_criteria = _FILTER_RANGE_CRITERIA[entity_type]
        typed_count_criteria = _FILTER_TYPED_COUNT_CRITERIA[entity_type]
        other_criteria = _FILTER_OTHER_CRITERIA[entity_type]
        supported = (*range_criteria, *typed_count_criteria, *other_criteria)
        if criteria not in supported:
            return _unsupported(criteria, entity_type, supported)

        attr = _SELECTION_ATTR[entity_type]
        selection = getattr(selection_builder, attr)

        if criteria in range_criteria:
            if find_max and find_min:
                return "Cannot set both find_max and find_min to True."
            if find_max:
                matching = getattr(selection, f"filter_{attr}_max_{criteria}")()
                call = f"filter_{attr}_max_{criteria}()"
            elif find_min:
                matching = getattr(selection, f"filter_{attr}_min_{criteria}")()
                call = f"filter_{attr}_min_{criteria}()"
            else:
                if min_value is None and max_value is None:
                    return (
                        f"At least one of min_value or max_value must be provided "
                        f"for '{criteria}' criterion."
                    )
                if criteria in _INT_CRITERIA:
                    min_val = int(min_value) if min_value is not None else None
                    max_val = int(max_value) if max_value is not None else None
                else:
                    min_val, max_val = min_value, max_value
                matching = getattr(selection, f"filter_{attr}_by_{criteria}")(min_val, max_val)
                call = f"filter_{attr}_by_{criteria}({min_val}, {max_val})"
        elif criteria in typed_count_criteria:
            enum_key = "surface_type" if criteria == "number_surfaces" else "curve_type"
            enum_val_str = surface_type if criteria == "number_surfaces" else curve_type
            type_map = _SURFACE_TYPE_MAP if criteria == "number_surfaces" else _CURVE_TYPE_MAP
            if enum_val_str is None:
                return f"{enum_key} must be provided for '{criteria}' criterion."
            enum_val = type_map[enum_val_str]
            if find_max and find_min:
                return "Cannot set both find_max and find_min to True."
            if find_max:
                matching = getattr(selection, f"filter_{attr}_max_{criteria}")(enum_val)
                call = f"filter_{attr}_max_{criteria}('{enum_val_str}')"
            elif find_min:
                matching = getattr(selection, f"filter_{attr}_min_{criteria}")(enum_val)
                call = f"filter_{attr}_min_{criteria}('{enum_val_str}')"
            else:
                if min_value is None and max_value is None:
                    return (
                        f"At least one of min_value or max_value must be provided "
                        f"for '{criteria}' criterion."
                    )
                min_val = int(min_value) if min_value is not None else None
                max_val = int(max_value) if max_value is not None else None
                matching = getattr(selection, f"filter_{attr}_by_{criteria}")(
                    enum_val, min_val, max_val
                )
                call = f"filter_{attr}_by_{criteria}('{enum_val_str}', {min_val}, {max_val})"
        elif criteria == "color":
            if not color:
                return "color must be provided for 'color' criterion."
            matching = getattr(selection, f"filter_{attr}_by_color")(color)
            call = f"filter_{attr}_by_color('{color}')"
        elif criteria == "name":
            if not name:
                return "name must be provided for 'name' criterion."
            matching = selection.filter_bodies_by_name(name)
            call = f"filter_bodies_by_name('{name}')"
        elif criteria == "containing_surface_type":
            if not surface_type:
                return "surface_type must be provided for 'containing_surface_type' criterion."
            matching = selection.filter_bodies_containing_surface_types(
                _SURFACE_TYPE_MAP[surface_type]
            )
            call = f"filter_bodies_containing_surface_types('{surface_type}')"
        elif criteria == "containing_curve_type":
            if not curve_type:
                return "curve_type must be provided for 'containing_curve_type' criterion."
            matching = getattr(selection, f"filter_{attr}_containing_curve_types")(
                _CURVE_TYPE_MAP[curve_type]
            )
            call = f"filter_{attr}_containing_curve_types('{curve_type}')"
        elif criteria == "curve_type":
            if not curve_type:
                return "curve_type must be provided for 'curve_type' criterion."
            matching = selection.filter_edges_by_curve_type(_CURVE_TYPE_MAP[curve_type])
            call = f"filter_edges_by_curve_type('{curve_type}')"
        elif criteria == "is_surface":
            matching = selection.filter_surface_bodies()
            call = "filter_surface_bodies()"
        elif criteria == "is_solid":
            matching = selection.filter_solid_bodies()
            call = "filter_solid_bodies()"

        app_context.command_history.append(f"matching = selection_builder.{attr}.{call}")
        getattr(selection_builder, _RESULT_ATTR[entity_type]).items[:] = matching.items
        app_context.command_history.append(
            f"selection_builder.{_RESULT_ATTR[entity_type]}.items[:] = matching.items"
        )
        logger.info(
            f"Filtered to {len(matching.items)} {entity_type} entities "
            f"using criterion '{criteria}'."
        )
        return _identifiers(matching)
    except Exception as e:
        logger.error(f"Error filtering {entity_type} entities: {e}")
        return f"Error filtering {entity_type} entities: {e}"


@app.tool()
def order_entities(
    ctx: Context,
    selection_handle: str,
    entity_type: EntityType,
    criteria: Literal[
        "volume",
        "surface_area",
        "area",
        "perimeter",
        "length",
        "face_count",
        "edge_count",
        "loop_count",
        "number_of_surfaces",
        "number_of_curves",
        "number_curves",
    ],
    curve_type: Literal["line", "circle", "ellipse", "nurbs", "procedural", "helix", "spline"]
    | None = None,
) -> list[str] | str:
    """Order the entities in a selection builder by a numeric property (ascending).

    This ranks the entities already in the builder. It does not discover, add, or
    remove entities. Use ``filter_entities`` to narrow the set, ``extend_selection``
    to add related entities, or ``group_entities`` to partition it by a shared property.

    Criteria by ``entity_type``:

    - ``"body"``: ``volume``, ``surface_area``, ``face_count``, ``edge_count``,
      ``loop_count``, ``number_of_surfaces``, ``number_of_curves``
    - ``"face"``: ``area``, ``perimeter``, ``edge_count``, ``loop_count``,
      ``number_curves`` (requires ``curve_type``)
    - ``"edge"``: ``length``

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    selection_handle : str
        Handle of the selection builder to use for this query. Reuse the handle
        from the most recent ``create_selection_builder`` call in this
        conversation rather than creating a new one.
    entity_type : str
        Kind of entity to order. Options are ``"body"``, ``"face"``, and ``"edge"``.
    criteria : str
        Property to sort by, smallest first.
    curve_type : str, default: None
        Curve type for the face ``"number_curves"`` criterion.

    Returns
    -------
    list of str | str
        Body names or face/edge IDs for every match. If no entities match, an empty list
        is returned.

        If the selection handle is invalid, the criterion does not apply to the entity type, or
        required arguments are missing, a string error message is returned.

    Examples
    --------
    Bodies sorted by volume (smallest first):
        ``order_entities(entity_type="body", criteria="volume")``

    Faces sorted by area:
        ``order_entities(entity_type="face", criteria="area")``

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return f"Product backend is not connected. Cannot order {entity_type} entities."

    try:
        selection_builder = app_context.selection_registry.get(selection_handle)
        app_context.command_history.append(
            f"selection_builder = selection_registry['{selection_handle}']"
        )
        if selection_builder is None:
            return f"Invalid selection handle: {selection_handle}"

        supported = _ORDER_CRITERIA[entity_type]
        if criteria not in supported:
            return _unsupported(criteria, entity_type, supported)

        attr = _SELECTION_ATTR[entity_type]
        method = getattr(getattr(selection_builder, attr), f"order_{attr}_by_{criteria}")

        if criteria == "number_curves":
            if not curve_type:
                return "curve_type must be provided for 'number_curves' criterion."
            ordered = method(_CURVE_TYPE_MAP[curve_type])
            call = f"order_{attr}_by_{criteria}('{curve_type}')"
        else:
            ordered = method()
            call = f"order_{attr}_by_{criteria}()"

        app_context.command_history.append(f"ordered = selection_builder.{attr}.{call}")
        getattr(selection_builder, _RESULT_ATTR[entity_type]).items[:] = ordered.items
        app_context.command_history.append(
            f"selection_builder.{_RESULT_ATTR[entity_type]}.items[:] = ordered.items"
        )
        logger.info(f"Ordered {len(ordered.items)} {entity_type} entities by '{criteria}'.")
        return _identifiers(ordered)
    except Exception as e:
        logger.error(f"Error ordering {entity_type} entities: {e}")
        return f"Error ordering {entity_type} entities: {e}"


@app.tool()
def group_entities(
    ctx: Context,
    selection_handle: str,
    entity_type: EntityType,
    criteria: Literal[
        "volume",
        "surface_area",
        "area",
        "perimeter",
        "face_count",
        "edge_count",
        "loop_count",
        "color",
        "name",
        "body",
        "coincident",
        "curve_type",
    ],
) -> list[list[str]] | str:
    """Group the entities in a selection builder by a shared property.

    Each returned group contains entities that are equal in the chosen property.
    Grouping applies only to entities already in the builder. It does not search the
    design for additional matches. Use ``filter_entities`` to narrow the selection or
    ``extend_selection`` to add related entities.

    Criteria by ``entity_type``:

    - ``"body"``: ``volume``, ``surface_area``, ``face_count``, ``edge_count``,
      ``loop_count``, ``color``, ``name``
    - ``"face"``: ``area``, ``perimeter``, ``body`` (group faces by owning body),
      ``edge_count``, ``loop_count``, ``color``, ``coincident``
    - ``"edge"``: ``curve_type``

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    selection_handle : str
        Handle of the selection builder to use for this query. Reuse the handle
        from the most recent ``create_selection_builder`` call in this
        conversation rather than creating a new one.
    entity_type : str
        Kind of entity to group. Options are ``"body"``, ``"face"``, and ``"edge"``.
    criteria : str
        Property to group by.

    Returns
    -------
    list of list of str | str
        Each inner list holds the body, face, or edge IDs of one group.

        If the selection handle is invalid or the criterion does not apply
        to the entity type, a string error message is returned.

    Examples
    --------
    Group all bodies by color:
        ``group_entities(entity_type="body", criteria="color")``

    Group faces by the body that owns them:
        ``group_entities(entity_type="face", criteria="body")``

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return f"Product backend is not connected. Cannot group {entity_type} entities."

    try:
        selection_builder = app_context.selection_registry.get(selection_handle)
        app_context.command_history.append(
            f"selection_builder = selection_registry['{selection_handle}']"
        )
        if selection_builder is None:
            return f"Invalid selection handle: {selection_handle}"

        supported = _GROUP_CRITERIA[entity_type]
        if criteria not in supported:
            return _unsupported(criteria, entity_type, supported)

        attr = _SELECTION_ATTR[entity_type]
        groups = getattr(getattr(selection_builder, attr), f"group_{attr}_by_{criteria}")()
        app_context.command_history.append(
            f"groups = selection_builder.{attr}.group_{attr}_by_{criteria}()"
        )

        getattr(selection_builder, _RESULT_ATTR[entity_type]).items[:] = [
            item for group in groups for item in group.items
        ]
        app_context.command_history.append(
            f"selection_builder.{_RESULT_ATTR[entity_type]}.items[:] = "
            "[item for group in groups for item in group.items]"
        )
        logger.info(f"Grouped {entity_type} entities into {len(groups)} groups by '{criteria}'.")
        return [_identifiers(group) for group in groups]
    except Exception as e:
        logger.error(f"Error grouping {entity_type} entities: {e}")
        return f"Error grouping {entity_type} entities: {e}"


@app.tool()
def extend_selection(
    ctx: Context,
    selection_handle: str,
    entity_type: EntityType,
    criteria: Literal[
        "volume",
        "surface_area",
        "area",
        "number_of_faces",
        "number_of_edges",
        "number_of_loops",
        "color",
        "name",
        "nearby",
        "coincident",
        "coaxial",
        "connected",
        "tangent_chain",
    ],
    scope: Literal["all", "visible", "body"] = "all",
    distance: float | None = None,
) -> list[str] | str:
    """Extend a selection with additional entities related to the ones already selected.

    The current selection is kept and matching entities from the specified scope
    are added to it.
    Use this when a request asks to include entities related to an existing selection.
    Use ``filter_entities`` instead when it asks to keep only matching entities, and
    ``create_named_selection`` when it asks to save the final selection under a name.

    Criteria by ``entity_type``:

    - ``"body"``: ``volume``, ``surface_area``, ``number_of_faces``,
      ``number_of_edges``, ``color``, ``name``, ``nearby``
    - ``"face"``: ``area``, ``number_of_edges``, ``number_of_loops``, ``color``,
      ``coincident``, ``coaxial``
    - ``"edge"``: ``nearby``, ``connected``, ``tangent_chain``, ``coaxial``

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    selection_handle : str
        Handle of the selection builder to use for this query. Reuse the handle
        from the most recent ``create_selection_builder`` call in this
        conversation rather than creating a new one.
    entity_type : str
        Kind of entity to extend. Options are ``"body"``, ``"face"``, and ``"edge"``.
    criteria : str
        Rule used to find additional entities. Property criteria such as
        ``"volume"`` or ``"color"`` add entities sharing that property with any
        entity already selected. ``"nearby"`` adds entities within ``distance``.
        ``"coincident"``, ``"coaxial"``, ``"connected"``, and ``"tangent_chain"``
        add entities related by topology or geometry. Bodies have no dedicated
        "touching"/contact criterion: for bodies in direct contact, use ``"nearby"``
        with a near-zero ``distance`` (e.g. ``0.0``) rather than omitting it.
    scope : str, default: ``"all"``
        Which entities to search when extending: ``"all"``, ``"visible"``, ``"body"``.
    distance : float, default: None
        Maximum proximity distance in metres for the ``"nearby"`` criterion.

    Returns
    -------
    list of str | str
        Body, face, or edge IDs in the extended selection.

        If the selection handle is invalid, the criterion does not apply to the entity type,
        or required arguments are missing, a string error message is returned.

    Examples
    --------
    Add bodies that share the same color:
        ``extend_selection(entity_type="body", criteria="color")``

    Add edges tangent to the selected ones:
        ``extend_selection(entity_type="edge", criteria="tangent_chain")``

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return f"Product backend is not connected. Cannot extend {entity_type} selection."

    try:
        selection_builder = app_context.selection_registry.get(selection_handle)
        app_context.command_history.append(
            f"selection_builder = selection_registry['{selection_handle}']"
        )
        if selection_builder is None:
            return f"Invalid selection handle: {selection_handle}"

        methods = _EXTEND_METHODS[entity_type]
        method_name = methods.get(criteria)
        if method_name is None:
            return _unsupported(criteria, entity_type, methods)

        attr = _SELECTION_ATTR[entity_type]
        method = getattr(getattr(selection_builder, attr), method_name)
        scope_val = _SCOPE_MAP[scope]

        if criteria == "nearby":
            if distance is None:
                return "distance must be provided for 'nearby' criterion."
            extended = method(distance, scope_val)
            call = f"{method_name}({distance}, '{scope}')"
        else:
            extended = method(scope_val)
            call = f"{method_name}('{scope}')"

        app_context.command_history.append(f"extended = selection_builder.{attr}.{call}")
        getattr(selection_builder, _RESULT_ATTR[entity_type]).items[:] = extended.items
        app_context.command_history.append(
            f"selection_builder.{_RESULT_ATTR[entity_type]}.items[:] = extended.items"
        )
        logger.info(
            f"Extended selection to {len(extended.items)} {entity_type} entities "
            f"using '{criteria}'."
        )
        return _identifiers(extended)
    except Exception as e:
        logger.error(f"Error extending {entity_type} selection: {e}")
        return f"Error extending {entity_type} selection: {e}"


@app.tool()
def create_named_selection(
    ctx: Context,
    name: str,
    selection_handle: str | None = None,
    body_ids: list[str] | None = None,
    face_ids: list[str] | None = None,
    edge_ids: list[str] | None = None,
    beam_ids: list[str] | None = None,
    design_point_ids: list[str] | None = None,
    component_ids: list[str] | None = None,
    vertex_ids: list[str] | None = None,
    datum_plane_ids: list[str] | None = None,
    coordinate_system_ids: list[str] | None = None,
    datum_point_ids: list[str] | None = None,
) -> str:
    """Create a named selection containing geometry entities.

    A named selection is a labelled group of entities that can later be
    referenced by name (for example, for meshing or boundary conditions). Use this tool
    to save the final result of a selection workflow or call it directly when the
    requested entities are already known by name or ID. It stores the supplied
    entities. It does not discover or refine them. At least one of
    ``selection_handle`` or an entity list must be provided.

    Typical workflows:

    - Use ``list_entities`` with ``entity_type="body"`` or ``"component"`` to find body or component
      IDs. Then use ``entity_type="face"`` or ``"edge"`` on a body to obtain the face and edge IDs
      to pass here.
    - Build a selection with ``create_selection_builder`` followed by
      ``select_entities``/``filter_entities``/``order_entities``/``group_entities``/
      ``extend_selection``. Then pass that builder's ``selection_handle`` here to
      save its currently selected bodies, faces, and edges as a named selection
      (for example, "save the bodies/faces I selected as ..."). The IDs those tools return
      can also be passed directly as ``body_ids``, ``face_ids``, or ``edge_ids``.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    name : str
        Label for the named selection.
    selection_handle : str, default: None
        Handle of a selection builder (from ``create_selection_builder``) whose
        currently selected bodies, faces, and edges should be included. Use this
        when the user refers to entities already picked/selected rather than
        naming them explicitly.
    body_ids : list of str, default: None
        Body IDs to include. Look up a body named by the user with
        ``list_entities(entity_type="body", name=...)``.
    face_ids : list of str, default: None
        Face IDs to include. Use ``list_entities`` to discover face IDs of a body.
    edge_ids : list of str, default: None
        Edge IDs to include. Use ``list_entities`` to discover edge IDs of a body.
    beam_ids : list of str, default: None
        Beam IDs to include.
    design_point_ids : list of str, default: None
        Design point IDs to include.
    component_ids : list of str, default: None
        Component IDs to include. Use ``list_entities`` with
        ``entity_type="component"`` to discover component IDs.
    vertex_ids : list of str, default: None
        Vertex IDs to include (from ``body.vertices``).
    datum_plane_ids : list of str, default: None
        Datum plane IDs to include.
    coordinate_system_ids : list of str, default: None
        Coordinate system IDs to include.
    datum_point_ids : list of str, default: None
        Datum point IDs to include.

    Returns
    -------
    str
        Confirmation message, or an error message.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot create named selection."

    if not any(
        [
            selection_handle,
            body_ids,
            face_ids,
            edge_ids,
            beam_ids,
            design_point_ids,
            component_ids,
            vertex_ids,
            datum_plane_ids,
            coordinate_system_ids,
            datum_point_ids,
        ]
    ):
        return "At least one entity list must be provided."

    try:
        from ansys.geometry.core.misc.auxiliary import (
            get_components_from_ids,
            get_datum_planes_from_ids,
            get_design_points_from_ids,
            get_edges_from_ids,
            get_faces_from_ids,
            get_vertices_from_ids,
        )

        design = app_context.product_instance.get_active_design()
        kwargs: dict = {}
        bodies: list = []
        faces: list = []
        edges: list = []

        if selection_handle:
            selection_builder = app_context.selection_registry.get(selection_handle)
            if selection_builder is None:
                return f"Invalid selection handle: {selection_handle}"
            selected_bodies = getattr(selection_builder, "_bodies", None)
            selected_faces = getattr(selection_builder, "_faces", None)
            selected_edges = getattr(selection_builder, "_edges", None)
            if not any(
                sel is not None and getattr(sel, "items", None)
                for sel in (selected_bodies, selected_faces, selected_edges)
            ):
                return f"Selection '{selection_handle}' has no entities selected."
            if selected_bodies is not None and selected_bodies.items:
                bodies.extend(selected_bodies.items)
            if selected_faces is not None and selected_faces.items:
                faces.extend(selected_faces.items)
            if selected_edges is not None and selected_edges.items:
                edges.extend(selected_edges.items)
            app_context.command_history.append(
                f"selection_builder = selection_registry['{selection_handle}']"
            )

        if body_ids:
            found_bodies, missing = find_bodies_by_id(design, body_ids)
            if missing:
                return (
                    f"Body ID(s) not found: {', '.join(missing)}. "
                    "Use list_entities to see available bodies."
                )
            bodies.extend(found_bodies)

        if bodies:
            kwargs["bodies"] = bodies

        if component_ids:
            components = get_components_from_ids(design, component_ids)
            found_ids = {comp.id for comp in components}
            missing = [cid for cid in component_ids if cid not in found_ids]
            if missing:
                return (
                    f"Component ID(s) not found: {', '.join(missing)}. "
                    "Use list_entities to see available components."
                )
            kwargs["components"] = components

        if face_ids:
            faces.extend(get_faces_from_ids(design, face_ids))

        if faces:
            kwargs["faces"] = faces

        if edge_ids:
            edges.extend(get_edges_from_ids(design, edge_ids))

        if edges:
            kwargs["edges"] = edges

        if vertex_ids:
            kwargs["vertices"] = get_vertices_from_ids(design, vertex_ids)

        if design_point_ids:
            kwargs["design_points"] = get_design_points_from_ids(design, design_point_ids)

        if datum_plane_ids:
            kwargs["datum_planes"] = get_datum_planes_from_ids(design, datum_plane_ids)

        if beam_ids:
            beams = []
            for bid in beam_ids:
                beam = design.search_beam(bid)
                if beam is None:
                    return f"Beam '{bid}' not found."
                beams.append(beam)
            kwargs["beams"] = beams

        if coordinate_system_ids:
            coord_systems = []
            for csid in coordinate_system_ids:
                cs = design.search_coordinate_system(csid)
                if cs is None:
                    return f"Coordinate system '{csid}' not found."
                coord_systems.append(cs)
            kwargs["coordinate_systems"] = coord_systems

        if datum_point_ids:
            d_points = []
            for dpid in datum_point_ids:
                dp = design.search_datum_point(dpid)
                if dp is None:
                    return f"Datum point '{dpid}' not found."
                d_points.append(dp)
            kwargs["datum_points"] = d_points

        named_sel = design.create_named_selection(name, **kwargs)

        # Build fully expanded command history entry
        cmd_parts = []
        if selection_handle:
            if selected_bodies is not None and selected_bodies.items:
                cmd_parts.append("bodies=selection_builder._bodies.items")
            if selected_faces is not None and selected_faces.items:
                cmd_parts.append("faces=selection_builder._faces.items")
            if selected_edges is not None and selected_edges.items:
                cmd_parts.append("edges=selection_builder._edges.items")
        if body_ids:
            cmd_parts.append(f"bodies=get_bodies_from_ids(design, {body_ids!r})")
        if face_ids:
            cmd_parts.append(f"faces=get_faces_from_ids(design, {face_ids!r})")
        if edge_ids:
            cmd_parts.append(f"edges=get_edges_from_ids(design, {edge_ids!r})")
        if beam_ids:
            cmd_parts.append(f"beams=[{', '.join(f'design.search_beam({b!r})' for b in beam_ids)}]")
        if design_point_ids:
            cmd_parts.append(
                f"design_points=get_design_points_from_ids(design, {design_point_ids!r})"
            )
        if component_ids:
            cmd_parts.append(f"components=get_components_from_ids(design, {component_ids!r})")
        if vertex_ids:
            cmd_parts.append(f"vertices=get_vertices_from_ids(design, {vertex_ids!r})")
        if datum_plane_ids:
            cmd_parts.append(f"datum_planes=get_datum_planes_from_ids(design, {datum_plane_ids!r})")
        if coordinate_system_ids:
            coordinate_system_commands = ", ".join(
                f"design.search_coordinate_system({coordinate_system_id!r})"
                for coordinate_system_id in coordinate_system_ids
            )
            cmd_parts.append(f"coordinate_systems=[{coordinate_system_commands}]")
        if datum_point_ids:
            datum_point_commands = ", ".join(
                f"design.search_datum_point({datum_point_id!r})"
                for datum_point_id in datum_point_ids
            )
            cmd_parts.append(f"datum_points=[{datum_point_commands}]")
        kwargs_str = ", ".join(cmd_parts)
        app_context.command_history.append(f"design.create_named_selection({name!r}, {kwargs_str})")

        logger.info(f"create_named_selection: name={name!r}")
        return f"Named selection '{name}' created successfully: {named_sel}"
    except Exception as e:
        logger.error(f"create_named_selection failed: {e}")
        return f"Error creating named selection '{name}': {e}"
