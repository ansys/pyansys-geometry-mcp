# Copyright (C) 2026 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
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

"""MCP tools exposing the selection pipeline.

``build_selection`` is the main entry point: it walks a list of steps against
a starting entity type (body, face, or edge), dispatching each step's action
through the corresponding handler's registry (see
:mod:`ansys.geometry.mcp.selection._base`).

``get_child_entities`` moves from a selection of bodies (or faces) to the
faces (or edges) that belong to them, so a pipeline can filter at one entity
type and then continue filtering at a finer-grained child type. For example,
to find only the circular edges of bodies that contain at least one circular
edge: filter bodies with ``filter_containing_curve_types``, call
``get_child_entities`` to get their edges, then filter those edges with
``filter_by_curve_type``.

``combine_selections`` performs set operations (union/difference/intersection)
between two selections of the same entity type. ``select_all_bodies`` /
``select_all_faces`` / ``select_all_edges`` are convenience shortcuts for the
most common first step.

``create_named_selection`` saves a selection's entities under a name on the
active design, persisting it beyond the current tool call (unlike the
transient lists returned by the other tools above).
"""

from ansys.common.mcp.logging_config import get_logger
from fastmcp.server import Context

from ansys.geometry.mcp import PyAnsysGeometryContext, app
from ansys.geometry.mcp.selection import HANDLER_REGISTRY, transition
from ansys.geometry.mcp.tools import get_geometry_ctx

logger = get_logger(__name__)


def _run_pipeline(
    app_context: "PyAnsysGeometryContext",
    entity_type: str,
    steps: list[dict],
    entity_ids: list[str] | None = None,
) -> dict:
    """Shared implementation backing ``build_selection`` and the convenience tools."""
    if app_context.product_instance is None:
        return {"error": "Product backend is not connected. Cannot build selection."}

    handler = HANDLER_REGISTRY.get(entity_type)
    if handler is None:
        return {
            "error": (
                f"Unknown entity_type '{entity_type}'. "
                f"Valid values: {', '.join(sorted(HANDLER_REGISTRY))}"
            )
        }

    try:
        design = app_context.product_instance.get_active_design()
        grpc_client = app_context.product_instance.client

        selection = (
            handler.build_from_ids(design, grpc_client, entity_ids)
            if entity_ids
            else handler.build_initial(design, grpc_client)
        )

        for step in steps:
            selection = handler.apply_step(selection, step)

        items = handler.serialize(selection)
        app_context.command_history.append(
            f"# build_selection(entity_type={entity_type!r}, steps={steps!r}) "
            f"-> {len(items)} {entity_type}(s)"
        )
        return {"entity_type": entity_type, "items": items}
    except Exception as e:
        logger.error(f"build_selection failed: {e}")
        return {"error": f"Error building selection: {e}"}


@app.tool()
def build_selection(
    ctx: Context,
    steps: list[dict],
    entity_type: str = "body",
    entity_ids: list[str] | None = None,
) -> dict:
    """Run a selection pipeline over bodies, faces, or edges.

    Each entry in ``steps`` is a dict of the form ``{"action": <name>, **params}``.
    Steps are applied in order, each one narrowing, extending, ordering, or
    inverting the current selection. All steps operate on a single entity type
    (bodies, faces, or edges) for a given call. To filter at a different,
    finer-grained entity type (for example, the edges of bodies matching some
    criterion), call ``get_child_entities`` between two ``build_selection``
    calls -- see the Examples section below.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    steps : list of dict
        Pipeline steps to apply in order. See the action tables below.
    entity_type : str, default: "body"
        Starting entity type: ``"body"``, ``"face"``, or ``"edge"``.
    entity_ids : list of str, optional
        If provided, the pipeline starts from these existing entity IDs
        (of ``entity_type``) instead of an empty selection.

    Returns
    -------
    dict
        ``{"entity_type": str, "items": list[dict]}`` on success, where
        ``items`` is a list of ``{"id": ..., ...}`` summaries. On failure,
        ``{"error": str}``.

    Body actions
    ------------
    Query (start a fresh selection from the whole document):
        ``get_all``, ``get_all_visible``, ``get_all_surface``, ``get_all_solid``,
        ``get_from_named_selection`` (name), ``get_with_name`` (name, filter_type,
        ignore_case), ``get_with_volume`` (min, max), ``get_with_surface_area``
        (min, max), ``get_with_x_location``/``get_with_y_location``/
        ``get_with_z_location`` (range_type, min, max), ``get_with_color`` (color).
    Invert:
        ``invert`` (scope: "visible" | "all").
    Filter:
        ``filter_by_volume``/``filter_max_volume``/``filter_min_volume`` (min, max),
        ``filter_by_surface_area``/``filter_max_surface_area``/
        ``filter_min_surface_area`` (min, max), ``filter_by_face_count``/
        ``filter_max_face_count``/``filter_min_face_count`` (min, max),
        ``filter_by_edge_count``/``filter_max_edge_count``/``filter_min_edge_count``
        (min, max), ``filter_by_loop_count``/``filter_max_loop_count``/
        ``filter_min_loop_count`` (min, max), ``filter_by_number_surfaces``/
        ``filter_max_number_surfaces``/``filter_min_number_surfaces`` (surface_type[,
        min, max]), ``filter_by_number_curves``/``filter_max_number_curves``/
        ``filter_min_number_curves`` (curve_type[, min, max]),
        ``filter_by_number_surfaces_percentile`` (surface_type, min_percentile,
        max_percentile), ``filter_by_number_curves_percentile`` (curve_type,
        min_percentile, max_percentile), ``filter_by_color`` (color),
        ``filter_by_name`` (name, filter_type, ignore_case),
        ``filter_containing_surface_types`` (surface_type, exclusive),
        ``filter_containing_curve_types`` (curve_type, exclusive),
        ``filter_volume_percentile``/``filter_surface_area_percentile``/
        ``filter_face_count_percentile``/``filter_edge_count_percentile``/
        ``filter_loop_count_percentile`` (min_percentile, max_percentile),
        ``filter_surface_bodies``, ``filter_solid_bodies``.
    Extend (scope: "all" | "body" | "visible"):
        ``extend_to_same_volume``, ``extend_to_same_surface_area``,
        ``extend_to_same_number_of_faces``, ``extend_to_same_number_of_edges``,
        ``extend_to_same_color``, ``extend_to_same_name``,
        ``extend_nearby`` (distance, scope).
    Order (no params, ascending):
        ``order_by_volume``, ``order_by_surface_area``, ``order_by_face_count``,
        ``order_by_edge_count``, ``order_by_loop_count``,
        ``order_by_number_of_surfaces``, ``order_by_number_of_curves``.

    Face actions
    ------------
    Query:
        ``get_all``, ``get_all_visible``, ``get_from_named_selection`` (name),
        ``get_with_area`` (min, max), ``get_with_x_location``/
        ``get_with_y_location``/``get_with_z_location`` (range_type, min, max),
        ``get_with_color`` (color).
    Invert:
        ``invert`` (scope: "all" | "body" | "visible").
    Filter:
        ``filter_by_area``/``filter_max_area``/``filter_min_area`` (min, max),
        ``filter_by_perimeter``/``filter_max_perimeter``/``filter_min_perimeter``
        (min, max), ``filter_by_edge_count``/``filter_max_edge_count``/
        ``filter_min_edge_count`` (min, max), ``filter_by_loop_count``/
        ``filter_max_loop_count``/``filter_min_loop_count`` (min, max),
        ``filter_by_number_curves``/``filter_max_number_curves``/
        ``filter_min_number_curves`` (curve_type[, min, max]),
        ``filter_containing_curve_types`` (curve_type, exclusive),
        ``filter_by_color`` (color), ``filter_area_percentile``/
        ``filter_perimeter_percentile``/``filter_edge_count_percentile``/
        ``filter_loop_count_percentile`` (min_percentile, max_percentile),
        ``filter_by_number_curves_percentile`` (curve_type, min_percentile,
        max_percentile).
    Extend (scope: "all" | "body" | "visible"):
        ``extend_to_same_area``, ``extend_to_same_number_of_edges``,
        ``extend_to_same_number_of_loops``, ``extend_to_same_color``,
        ``extend_to_coincident``, ``extend_to_coaxial``.
    Order (no params unless noted, ascending):
        ``order_by_area``, ``order_by_perimeter``, ``order_by_edge_count``,
        ``order_by_loop_count``, ``order_by_number_curves`` (curve_type).

    Edge actions
    ------------
    Query:
        ``get_all``, ``get_all_visible``, ``get_from_named_selection`` (name),
        ``get_with_length`` (min, max), ``get_with_x_location``/
        ``get_with_y_location``/``get_with_z_location`` (range_type, min, max).
    Invert:
        ``invert`` (scope: "all" | "body" | "visible").
    Filter:
        ``filter_by_length``/``filter_max_length``/``filter_min_length`` (min, max),
        ``filter_by_curve_type`` (curve_type), ``filter_length_percentile``
        (min_percentile, max_percentile).
    Extend (scope: "all" | "body" | "visible"):
        ``extend_nearby`` (distance, scope), ``extend_to_connected``,
        ``extend_to_tangent_chain``, ``extend_to_coaxial``.
    Order (no params, ascending):
        ``order_by_length``.

    Notes
    -----
    ``surface_type`` values: "plane", "cylinder", "cone", "torus", "sphere",
    "nurbs", "procedural", "splinesurface", "unknown".
    ``curve_type`` values: "line", "circle", "ellipse", "nurbs", "procedural",
    "helix", "splinecurve", "unknown".
    ``filter_type`` values: "text", "wildcard", "regex".
    ``range_type`` values: "intersect", "contain".
    Length/area/volume/distance parameters are plain numbers in meters, square
    meters, and cubic meters respectively.

    Examples
    --------
    Bodies with volume above 0.001 m3::

        build_selection(
            entity_type="body",
            steps=[
                {"action": "get_all"},
                {"action": "filter_by_volume", "min": 0.001},
            ],
        )

    The circular edges of bodies that contain at least one circular edge --
    chaining ``build_selection`` and ``get_child_entities`` across entity
    types::

        bodies = build_selection(
            entity_type="body",
            steps=[
                {"action": "get_all"},
                {"action": "filter_containing_curve_types", "curve_type": "circle"},
            ],
        )
        edges = get_child_entities(
            parent_entity_type="body",
            parent_entity_ids=[b["id"] for b in bodies["items"]],
            child_entity_type="edge",
        )
        circular_edges = build_selection(
            entity_type="edge",
            entity_ids=[e["id"] for e in edges["items"]],
            steps=[{"action": "filter_by_curve_type", "curve_type": "circle"}],
        )

    """
    app_context = get_geometry_ctx(ctx)
    return _run_pipeline(app_context, entity_type, steps, entity_ids)


@app.tool()
def get_child_entities(
    ctx: Context,
    parent_entity_type: str,
    parent_entity_ids: list[str],
    child_entity_type: str,
) -> dict:
    """Get the faces or edges that belong to a set of bodies or faces.

    Use this to move from a selection of one entity type to the "child"
    entities that make it up, so a pipeline can filter at one granularity and
    then continue filtering at a finer one. Supported combinations:
    body -> face, body -> edge, face -> edge. There is no way back up
    (edge -> face, face -> body).

    Typical usage: filter bodies/faces with ``build_selection``, pass the
    resulting IDs here to get their child faces/edges, then pass those IDs to
    another ``build_selection`` call to filter the children. See the
    Examples section of ``build_selection`` for a full walkthrough.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    parent_entity_type : str
        Entity type of ``parent_entity_ids``: ``"body"`` or ``"face"``.
    parent_entity_ids : list of str
        IDs of the parent entities to extract children from.
    child_entity_type : str
        Entity type of the children to extract: ``"face"`` or ``"edge"``.

    Returns
    -------
    dict
        ``{"entity_type": str, "items": list[dict]}`` on success -- the
        children are deduplicated across all parents. On failure,
        ``{"error": str}``.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return {"error": "Product backend is not connected. Cannot get child entities."}

    parent_handler = HANDLER_REGISTRY.get(parent_entity_type)
    if parent_handler is None:
        return {
            "error": (
                f"Unknown parent_entity_type '{parent_entity_type}'. "
                f"Valid values: {', '.join(sorted(HANDLER_REGISTRY))}"
            )
        }
    if child_entity_type not in parent_handler.CHILD_TYPES:
        return {
            "error": (
                f"Cannot get '{child_entity_type}' children of '{parent_entity_type}'. "
                f"Supported child types: {', '.join(parent_handler.CHILD_TYPES) or 'none'}."
            )
        }

    try:
        design = app_context.product_instance.get_active_design()
        grpc_client = app_context.product_instance.client

        parent_selection = parent_handler.build_from_ids(design, grpc_client, parent_entity_ids)
        child_selection = transition(
            design, grpc_client, parent_entity_type, parent_selection, child_entity_type
        )
        child_handler = HANDLER_REGISTRY[child_entity_type]
        items = child_handler.serialize(child_selection)

        app_context.command_history.append(
            f"# get_child_entities(parent_entity_type={parent_entity_type!r}, "
            f"child_entity_type={child_entity_type!r}) -> {len(items)} {child_entity_type}(s)"
        )
        return {"entity_type": child_entity_type, "items": items}
    except Exception as e:
        logger.error(f"get_child_entities failed: {e}")
        return {"error": f"Error getting child entities: {e}"}


@app.tool()
def combine_selections(
    ctx: Context,
    entity_type: str,
    ids_a: list[str],
    ids_b: list[str],
    operation: str = "union",
) -> dict:
    """Combine two selections of the same entity type with a set operation.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    entity_type : str
        Entity type of both selections: ``"body"``, ``"face"``, or ``"edge"``.
    ids_a : list of str
        Entity IDs making up the first selection.
    ids_b : list of str
        Entity IDs making up the second selection.
    operation : str, default: "union"
        Set operation to apply: ``"union"``, ``"difference"`` (``ids_a`` minus
        ``ids_b``), or ``"intersection"``.

    Returns
    -------
    dict
        ``{"entity_type": str, "items": list[dict]}`` on success, or
        ``{"error": str}`` on failure.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return {"error": "Product backend is not connected. Cannot combine selections."}

    handler = HANDLER_REGISTRY.get(entity_type)
    if handler is None:
        return {
            "error": (
                f"Unknown entity_type '{entity_type}'. "
                f"Valid values: {', '.join(sorted(HANDLER_REGISTRY))}"
            )
        }

    try:
        design = app_context.product_instance.get_active_design()
        grpc_client = app_context.product_instance.client
        selection_a = handler.build_from_ids(design, grpc_client, ids_a)
        selection_b = handler.build_from_ids(design, grpc_client, ids_b)

        if operation == "union":
            combined = selection_a + selection_b
        elif operation == "difference":
            combined = selection_a - selection_b
        elif operation == "intersection":
            combined = selection_a & selection_b
        else:
            return {
                "error": (
                    f"Unknown operation '{operation}'. "
                    "Valid values: 'union', 'difference', 'intersection'."
                )
            }

        app_context.command_history.append(
            f"# combine_selections(entity_type={entity_type!r}, operation={operation!r})"
        )
        return {"entity_type": entity_type, "items": handler.serialize(combined)}
    except Exception as e:
        logger.error(f"combine_selections failed: {e}")
        return {"error": f"Error combining selections: {e}"}


#: Maps a selection entity type to the plural keyword argument accepted by
#: ``Design.create_named_selection`` (e.g. "body" -> "bodies").
_NAMED_SELECTION_KWARGS = {"body": "bodies", "face": "faces", "edge": "edges"}


@app.tool()
def create_named_selection(
    ctx: Context,
    name: str,
    entity_type: str,
    entity_ids: list[str],
) -> dict:
    """Create a persistent named selection in the active design.

    Unlike ``build_selection``/``get_child_entities``, which return transient,
    in-memory lists of entities, a named selection is saved on the design
    itself -- it survives across tool calls, shows up in the Geometry
    service and any exported file, and can later be recalled by name (for
    example with the ``get_from_named_selection`` action in
    ``build_selection``).

    Typical usage: build up a selection of bodies/faces/edges with
    ``build_selection`` (and optionally ``get_child_entities`` /
    ``combine_selections``), then pass the resulting IDs here to save it
    under a name.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    name : str
        Name to give the new named selection.
    entity_type : str
        Entity type of ``entity_ids``: ``"body"``, ``"face"``, or ``"edge"``.
    entity_ids : list of str
        IDs of the entities to include, typically the IDs of the ``items``
        returned by a prior ``build_selection``, ``get_child_entities``, or
        ``combine_selections`` call.

    Returns
    -------
    dict
        ``{"name": str, "id": str, "entity_type": str, "count": int}`` on
        success. On failure, ``{"error": str}``.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return {"error": "Product backend is not connected. Cannot create named selection."}

    handler = HANDLER_REGISTRY.get(entity_type)
    if handler is None:
        return {
            "error": (
                f"Unknown entity_type '{entity_type}'. "
                f"Valid values: {', '.join(sorted(HANDLER_REGISTRY))}"
            )
        }
    if not entity_ids:
        return {"error": "entity_ids must contain at least one ID."}

    try:
        design = app_context.product_instance.get_active_design()
        grpc_client = app_context.product_instance.client
        selection = handler.build_from_ids(design, grpc_client, entity_ids)

        named_selection = design.create_named_selection(
            name, **{_NAMED_SELECTION_KWARGS[entity_type]: selection.items}
        )

        app_context.command_history.append(
            f"# create_named_selection(name={name!r}, entity_type={entity_type!r}) "
            f"-> {len(selection.items)} {entity_type}(s)"
        )
        return {
            "name": named_selection.name,
            "id": named_selection.id,
            "entity_type": entity_type,
            "count": len(selection.items),
        }
    except Exception as e:
        logger.error(f"create_named_selection failed: {e}")
        return {"error": f"Error creating named selection: {e}"}


@app.tool()
def select_all_bodies(ctx: Context) -> dict:
    """Select all bodies in the active design.

    Shortcut for ``build_selection(entity_type="body", steps=[{"action": "get_all"}])``.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).

    Returns
    -------
    dict
        ``{"entity_type": "body", "items": list[dict]}`` on success, or
        ``{"error": str}`` on failure.

    """
    return _run_pipeline(get_geometry_ctx(ctx), "body", [{"action": "get_all"}])


@app.tool()
def select_all_faces(ctx: Context) -> dict:
    """Select all faces in the active design.

    Shortcut for ``build_selection(entity_type="face", steps=[{"action": "get_all"}])``.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).

    Returns
    -------
    dict
        ``{"entity_type": "face", "items": list[dict]}`` on success, or
        ``{"error": str}`` on failure.

    """
    return _run_pipeline(get_geometry_ctx(ctx), "face", [{"action": "get_all"}])


@app.tool()
def select_all_edges(ctx: Context) -> dict:
    """Select all edges in the active design.

    Shortcut for ``build_selection(entity_type="edge", steps=[{"action": "get_all"}])``.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).

    Returns
    -------
    dict
        ``{"entity_type": "edge", "items": list[dict]}`` on success, or
        ``{"error": str}`` on failure.

    """
    return _run_pipeline(get_geometry_ctx(ctx), "edge", [{"action": "get_all"}])
