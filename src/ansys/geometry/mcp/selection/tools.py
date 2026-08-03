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
:mod:`ansys.geometry.mcp.selection._base`). A special ``"transition"`` action
switches the pipeline to a child entity type (body -> face, body -> edge, or
face -> edge), carrying over the child entities of the current selection.

``combine_selections`` performs set operations (union/difference/intersection)
between two selections of the same entity type. ``select_all_bodies`` /
``select_all_faces`` / ``select_all_edges`` are convenience shortcuts for the
most common first step.
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

        current_type = entity_type
        selection = (
            handler.build_from_ids(design, grpc_client, entity_ids)
            if entity_ids
            else handler.build_initial(design, grpc_client)
        )

        for step in steps:
            if step.get("action") == "transition":
                target_type = step.get("to")
                selection = transition(design, grpc_client, current_type, selection, target_type)
                current_type = target_type
                handler = HANDLER_REGISTRY[current_type]
                continue
            selection = handler.apply_step(selection, step)

        items = handler.serialize(selection)
        app_context.command_history.append(
            f"# build_selection(entity_type={entity_type!r}, steps={steps!r}) "
            f"-> {len(items)} {current_type}(s)"
        )
        return {"entity_type": current_type, "items": items}
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
    inverting the current selection. A step with ``{"action": "transition", "to":
    "face"}`` (or ``"edge"``) switches the pipeline to the child entity type,
    carrying over the child entities (faces or edges) belonging to the bodies
    (or faces) currently selected. Only downward transitions are supported:
    body -> face, body -> edge, face -> edge. There is no way back up.

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
        ``entity_type`` reflects the final entity type after any transitions
        and ``items`` is a list of ``{"id": ..., ...}`` summaries. On failure,
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
    Bodies with volume above 0.001 m3, transitioned to their faces with area
    above 0.0001 m2::

        build_selection(
            steps=[
                {"action": "get_all"},
                {"action": "filter_by_volume", "min": 0.001},
                {"action": "transition", "to": "face"},
                {"action": "filter_by_area", "min": 0.0001},
            ]
        )

    """
    app_context = get_geometry_ctx(ctx)
    return _run_pipeline(app_context, entity_type, steps, entity_ids)


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
