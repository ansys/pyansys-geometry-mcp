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

"""Selection MCP tools for PyAnsys Geometry MCP server.

Each function decorated with ``@app.tool()`` is exposed as an MCP tool.
The ``ctx`` parameter provides access to the application context (and thus
to the live product instance and command history).

How to add a tool
-----------------
1. Define a Python function with type-annotated parameters.
2. Add a NumPy-style docstring — the summary line becomes the tool description
   visible to the AI assistant.
3. Decorate it with ``@app.tool()``.
4. Access the product instance via::

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
from ansys.geometry.mcp.misc.auxiliary import find_body, find_component, get_geometry_ctx
from ansys.geometry.mcp.misc.selection_enums import (
    _CURVE_TYPE_MAP,
    _SCOPE_MAP,
    _SURFACE_TYPE_MAP,
)

logger = get_logger(__name__)


def _component_tree(node, indent: int) -> list[str]:
    lines = []
    for comp in node.components:
        lines.append("  " * indent + comp.name)
        lines.extend(_component_tree(comp, indent + 1))
    return lines


def _body_paths(node, prefix: str) -> list[str]:
    lines = [f"{prefix}{body.name}" for body in node.bodies]
    for comp in node.components:
        lines.extend(_body_paths(comp, f"{prefix}{comp.name}/"))
    return lines


@app.tool()
def list_entities(
    ctx: Context,
    entity_type: Literal["bodies", "components", "faces", "edges"],
    body_name: str | None = None,
    component_name: str | None = None,
) -> str:
    """List the entities of a given type in the active design.

    This is the discovery tool: use it to find the exact body names, component
    names, face IDs, and edge IDs that every other tool expects as input.

    Behaviour per ``entity_type``:

    - ``"bodies"``: body names prefixed with their component path, e.g.
      ``MainComponent/Cylinder``. Pass ``component_name`` to restrict the
      listing to one component and its children.
    - ``"components"``: the component hierarchy as an indented tree.
    - ``"faces"``: ``id=<face id>  surface_type=<type>`` for every face of
      ``body_name``. Use it whenever a face ID is needed, or to answer
      questions about how many faces a body has or which faces are planes,
      cylinders, cones, and so on.
    - ``"edges"``: ``id=<edge id>  curve_type=<type>`` for every edge of
      ``body_name``. Use it whenever an edge ID is needed, or to answer
      questions about how many edges a body has or which edges are lines,
      circles, arcs, and so on.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    entity_type : str
        One of ``"bodies"``, ``"components"``, ``"faces"``, ``"edges"``.
    body_name : str, optional
        Body to inspect. Required for ``"faces"`` and ``"edges"``, ignored
        otherwise. List the bodies first to discover valid names.
    component_name : str, optional
        Restrict a ``"bodies"`` listing to this component and its children.
        Ignored for the other entity types.

    Returns
    -------
    str
        Newline-separated listing, or an error message.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return f"Product backend is not connected. Cannot list {entity_type}."

    if entity_type in ("faces", "edges") and body_name is None:
        return f"'body_name' is required when listing {entity_type}."

    try:
        design = app_context.product_instance.get_active_design()
        logger.info(f"list_entities: entity_type={entity_type!r}, body_name={body_name!r}")

        if entity_type == "components":
            lines = _component_tree(design, 0)
            return "\n".join(lines) if lines else "No components found in the active design."

        if entity_type == "bodies":
            root = design if component_name is None else find_component(design, component_name)
            if root is None:
                return f"Component '{component_name}' not found."
            lines = _body_paths(root, "")
            return "\n".join(lines) if lines else "No bodies found."

        body = find_body(design, body_name)
        if body is None:
            return (
                f"Body '{body_name}' not found. "
                "Use list_entities with entity_type='bodies' to see available bodies."
            )

        if entity_type == "faces":
            lines = [f"id={face.id}  surface_type={face.surface_type.name}" for face in body.faces]
            return "\n".join(lines) if lines else f"Body '{body_name}' has no faces."

        lines = [f"id={edge.id}  curve_type={edge.curve_type.name}" for edge in body.edges]
        return "\n".join(lines) if lines else f"Body '{body_name}' has no edges."
    except Exception as e:
        logger.error(f"list_entities failed: {e}")
        return f"Error listing {entity_type}: {e}"


@app.tool()
def create_selection_builder(ctx: Context) -> str:
    """Create an empty selection builder in the product backend.

    The SelectionBuilder is used to build complex selections of geometry entities
    (bodies, faces, edges) via query, filter, order, group, and extend operations.
    Selections can also be combined, subtracted, or intersected.

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
def select_bodies(
    ctx: Context,
    selection_handle: str,
    criteria: Literal[
        "all",
        "visible",
        "solid",
        "surface",
        "named_selection",
        "name",
        "volume",
        "surface_area",
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
    """Select bodies from a selection builder.

    Use this tool whenever you need to find bodies that match a specific
    property. Pass one ``criteria`` value from the table below and supply
    the corresponding extra argument(s).

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    selection_handle : str
        Handle of the selection builder to use for this query.
    criteria : str
        Selection rule to apply. Accepted values:

        ``"all"``
            Every body in the design. No extra arguments needed.
        ``"visible"``
            All currently visible bodies. No extra arguments needed.
        ``"solid"``
            All solid (volumetric) bodies. No extra arguments needed.
        ``"surface"``
            All surface (sheet) bodies. No extra arguments needed.
        ``"named_selection"``
            Bodies belonging to a named selection group.
            Requires ``named_selection``.
        ``"name"``
            Bodies whose name matches the given string (exact match).
            Requires ``name``.
        ``"volume"``
            Bodies whose volume falls in [``min_value``, ``max_value``] (m³).
            Requires ``min_value`` (``max_value`` optional).
        ``"surface_area"``
            Bodies whose surface area falls in [``min_value``, ``max_value``] (m²).
            Requires ``min_value`` (``max_value`` optional).
        ``"x_location"``
            Bodies whose centroid X coordinate falls in
            [``min_value``, ``max_value``] (m).
            Requires at least one of ``min_value`` or ``max_value``.
        ``"y_location"``
            Bodies whose centroid Y coordinate falls in
            [``min_value``, ``max_value``] (m).
            Requires at least one of ``min_value`` or ``max_value``.
        ``"z_location"``
            Bodies whose centroid Z coordinate falls in
            [``min_value``, ``max_value``] (m).
            Requires at least one of ``min_value`` or ``max_value``.
        ``"color"``
            Bodies with a specific display color.
            Requires ``color`` as a hex string, e.g. ``"#FF0000"``.
    name : str, optional
        Body name for the ``"name"`` criterion.
    named_selection : str, optional
        Named selection label for the ``"named_selection"`` criterion.
    min_value : float, optional
        Lower bound (inclusive) for range-based criteria
        (``"volume"``, ``"surface_area"``, ``"x_location"``,
        ``"y_location"``, ``"z_location"``).
    max_value : float, optional
        Upper bound (inclusive) for range-based criteria.
        Pass ``None`` to leave the upper bound open.
    color : str, optional
        Hex color string for the ``"color"`` criterion, e.g. ``"#FF0000"``.

    Returns
    -------
    list of str | str
        Names of all matching bodies, or an empty list if none match.
        Returns a string error message if the selection handle is invalid or if required arguments
        are missing.

    Examples
    --------
    All solid bodies:
        ``select_bodies(criteria="solid")``

    Bodies in a named selection called "Fluid":
        ``select_bodies(criteria="named_selection", named_selection="Fluid")``

    Bodies with volume between 1e-6 m³ and 1e-3 m³:
        ``select_bodies(criteria="volume", min_value=1e-6, max_value=1e-3)``

    Bodies at Z > 0.05 m:
        ``select_bodies(criteria="z_location", min_value=0.05)``

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot select bodies."

    try:
        selection_builder = app_context.selection_registry.get(selection_handle)
        app_context.command_history.append(
            f"selection_builder = selection_registry['{selection_handle}']"
        )
        if selection_builder is None:
            return f"Invalid selection handle: {selection_handle}"

        # Perform the selection based on the criteria
        if criteria == "all":
            matching_bodies = selection_builder.bodies.get_all_bodies()
            app_context.command_history.append("selection_builder.bodies.get_all_bodies()")
        elif criteria == "visible":
            matching_bodies = selection_builder.bodies.get_all_visible_bodies()
            app_context.command_history.append("selection_builder.bodies.get_all_visible_bodies()")
        elif criteria == "solid":
            matching_bodies = selection_builder.bodies.get_all_solid_bodies()
            app_context.command_history.append("selection_builder.bodies.get_all_solid_bodies()")
        elif criteria == "surface":
            matching_bodies = selection_builder.bodies.get_all_surface_bodies()
            app_context.command_history.append("selection_builder.bodies.get_all_surface_bodies()")
        elif criteria == "named_selection":
            if not named_selection:
                return "Named selection name must be provided for 'named_selection' criterion."
            matching_bodies = selection_builder.bodies.get_bodies_from_named_selection(
                named_selection
            )
            app_context.command_history.append(
                f"selection_builder.bodies.get_bodies_from_named_selection('{named_selection}')"
            )
        elif criteria == "name":
            if not name:
                return "Body name must be provided for 'name' criterion."
            matching_bodies = selection_builder.bodies.get_bodies_with_name(name)
            app_context.command_history.append(
                f"selection_builder.bodies.get_bodies_with_name('{name}')"
            )
        elif criteria in ["volume", "surface_area"]:
            if min_value is None:
                return f"min_value must be provided for '{criteria}' criterion."
            if criteria == "volume":
                matching_bodies = selection_builder.bodies.get_bodies_with_volume(
                    min_value, max_value
                )
                app_context.command_history.append(
                    f"selection_builder.bodies.get_bodies_with_volume({min_value}, {max_value})"
                )
            elif criteria == "surface_area":
                matching_bodies = selection_builder.bodies.get_bodies_with_surface_area(
                    min_value, max_value
                )
                app_context.command_history.append(
                    f"selection_builder.bodies.get_bodies_with_surface_area({min_value}, {max_value})"
                )
        elif criteria in ["x_location", "y_location", "z_location"]:
            if min_value is None and max_value is None:
                return f"At least one of min_value or max_value must be provided for '{criteria}' criterion."
            elif criteria == "x_location":
                matching_bodies = selection_builder.bodies.get_bodies_with_x_location(
                    min=min_value, max=max_value
                )
                app_context.command_history.append(
                    f"selection_builder.bodies.get_bodies_with_x_location({min_value}, {max_value})"
                )
            elif criteria == "y_location":
                matching_bodies = selection_builder.bodies.get_bodies_with_y_location(
                    min=min_value, max=max_value
                )
                app_context.command_history.append(
                    f"selection_builder.bodies.get_bodies_with_y_location({min_value}, {max_value})"
                )
            elif criteria == "z_location":
                matching_bodies = selection_builder.bodies.get_bodies_with_z_location(
                    min=min_value, max=max_value
                )
                app_context.command_history.append(
                    f"selection_builder.bodies.get_bodies_with_z_location({min_value}, {max_value})"
                )
        elif criteria == "color":
            if not color:
                return "Color must be provided for 'color' criterion."
            matching_bodies = selection_builder.bodies.get_bodies_with_color(color)
            app_context.command_history.append(
                f"selection_builder.bodies.get_bodies_with_color('{color}')"
            )
        else:
            return f"Unknown selection criterion: {criteria}"

        selection_builder._bodies = matching_bodies
        app_context.command_history.append(f"selection_builder._bodies = matching_bodies")
        logger.info(f"Selected {len(matching_bodies.items)} bodies using criterion '{criteria}'.")
        return [body.name for body in matching_bodies.items]
    except Exception as e:
        logger.error(f"Error selecting bodies: {e}")
        return f"Error selecting bodies: {e}"


@app.tool()
def filter_bodies(
    ctx: Context,
    selection_handle: str,
    criteria: Literal[
        "volume",
        "surface_area",
        "face_count",
        "edge_count",
        "loop_count",
        "number_surfaces",
        "number_curves",
        "color",
        "name",
        "containing_surface_type",
        "containing_curve_type",
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
    """Filter bodies in a Selection Builder based on a user-defined condition.

    This tool allows users to apply a custom filter function to the bodies
    in the selection builder. Pass one  ``criteria`` value from the table below
    and supply the corresponding extra argument(s).

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    selection_handle : str
        Handle of the selection builder to use for this query.
    criteria : str
        Filter rule to apply. Accepted values:

        ``"volume"``
            Bodies whose volume falls in [``min_value``, ``max_value``] (m³)
            or is the maximum/minimum if ``find_max`` or ``find_min`` is True.
            Requires at least one of ``min_value`` or ``max_value``, or exactly
            one of ``find_max`` or ``find_min``.
        ``"surface_area"``
            Bodies whose surface area falls in [``min_value``, ``max_value``] (m²)
            or is the maximum/minimum if ``find_max`` or ``find_min`` is True.
            Requires at least one of ``min_value`` or ``max_value``, or exactly
            one of ``find_max`` or ``find_min``.
        ``"face_count"``
            Bodies with a specific number of faces or is the maximum/minimum if ``find_max``
            or ``find_min`` is True. Requires ``min_value`` and/or ``max_value``, or exactly one
            of ``find_max`` or ``find_min``.
        ``"edge_count"``
            Bodies with a specific number of edges or is the maximum/minimum if ``find_max``
            or ``find_min`` is True. Requires ``min_value`` and/or ``max_value``, or exactly one
            of ``find_max`` or ``find_min``.
        ``"loop_count"``
            Bodies with a specific number of loops or is the maximum/minimum if ``find_max``
            or ``find_min`` is True. Requires ``min_value`` and/or ``max_value``, or exactly one
            of ``find_max`` or ``find_min``.
        ``"number_surfaces"``
            Bodies with a specific number of surfaces or is the maximum/minimum if ``find_max``
            or ``find_min`` is True. Requires ``min_value`` and/or ``max_value``, or exactly one
            of ``find_max`` or ``find_min``.
        ``"number_curves"``
            Bodies with a specific number of curves or is the maximum/minimum if ``find_max``
            or ``find_min`` is True. Requires ``min_value`` and/or ``max_value``, or exactly one
            of ``find_max`` or ``find_min``.
        ``"color"``
            Bodies with a specific display color.
            Requires ``color`` as a hex string, e.g. ``"#FF0000"``.
        ``"name"``
            Bodies whose name matches the given string (exact match).
            Requires ``name``.
        ``"containing_surface_type"``
            Bodies containing surfaces of a specific type (e.g., "plane", "cylinder").
            Requires ``surface_type``.
        ``"containing_curve_type"``
            Bodies containing curves of a specific type (e.g., "line", "arc").
            Requires ``curve_type``.
        ``"is_surface"``
            Filter for surface bodies only. No extra arguments needed.
        ``"is_solid"``
            Filter for solid bodies only. No extra arguments needed.
    name : str, optional
        Body name for the ``"name"`` criterion.
    find_max : bool, optional
        If True, filter for the body with the maximum value of the specified criterion.
    find_min : bool, optional
        If True, filter for the body with the minimum value of the specified criterion.
    min_value : float, optional
        Lower bound (inclusive) for range-based criteria
        (``"volume"``, ``"surface_area"``, ``"face_count"``,
        ``"edge_count"``, ``"loop_count"``, ``"number_surfaces"``,
        ``"number_curves"``).
    max_value : float, optional
        Upper bound (inclusive) for range-based criteria.
        Pass ``None`` to leave the upper bound open.
    surface_type : str, optional
        Surface type for the ``"containing_surface_type"`` criterion.
    curve_type : str, optional
        Curve type for the ``"containing_curve_type"`` criterion.
    color : str, optional
        Hex color string for the ``"color"`` criterion, e.g. ``"#FF0000"``.

    Returns
    -------
    list of str | str
        Names of all bodies that satisfy the filter condition, or an empty list if none match.
        Returns a string error message if the selection handle is invalid or if required arguments
        are missing.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot filter bodies."

    try:
        selection_builder = app_context.selection_registry.get(selection_handle)
        app_context.command_history.append(
            f"selection_builder = selection_registry['{selection_handle}']"
        )
        if selection_builder is None:
            return f"Invalid selection handle: {selection_handle}"

        if criteria in ("volume", "surface_area", "face_count", "edge_count", "loop_count"):
            if find_max and find_min:
                return "Cannot set both find_max and find_min to True."
            elif find_max:
                method = getattr(selection_builder.bodies, f"filter_bodies_max_{criteria}")
                matching_bodies = method()
                app_context.command_history.append(
                    f"selection_builder.bodies.filter_bodies_max_{criteria}()"
                )
            elif find_min:
                method = getattr(selection_builder.bodies, f"filter_bodies_min_{criteria}")
                matching_bodies = method()
                app_context.command_history.append(
                    f"selection_builder.bodies.filter_bodies_min_{criteria}()"
                )
            else:
                if min_value is None and max_value is None:
                    return f"At least one of min_value or max_value must be provided for '{criteria}' criterion."
                # Count-based criteria require int
                _int_criteria = ("face_count", "edge_count", "loop_count")
                if criteria in _int_criteria:
                    min_val = int(min_value) if min_value is not None else None
                    max_val = int(max_value) if max_value is not None else None
                else:
                    min_val, max_val = min_value, max_value
                method = getattr(selection_builder.bodies, f"filter_bodies_by_{criteria}")
                matching_bodies = method(min_val, max_val)
                app_context.command_history.append(
                    f"selection_builder.bodies.filter_bodies_by_{criteria}({min_val}, {max_val})"
                )
        elif criteria in ("number_surfaces", "number_curves"):
            enum_key = "surface_type" if criteria == "number_surfaces" else "curve_type"
            enum_val_str = surface_type if criteria == "number_surfaces" else curve_type
            type_map = _SURFACE_TYPE_MAP if criteria == "number_surfaces" else _CURVE_TYPE_MAP
            if enum_val_str is None:
                return f"{enum_key} must be provided for '{criteria}' criterion."
            enum_val = type_map[enum_val_str]
            if find_max:
                matching_bodies = getattr(
                    selection_builder.bodies, f"filter_bodies_max_{criteria}"
                )(enum_val)
                app_context.command_history.append(
                    f"selection_builder.bodies.filter_bodies_max_{criteria}('{enum_val_str}')"
                )
            elif find_min:
                matching_bodies = getattr(
                    selection_builder.bodies, f"filter_bodies_min_{criteria}"
                )(enum_val)
                app_context.command_history.append(
                    f"selection_builder.bodies.filter_bodies_min_{criteria}('{enum_val_str}')"
                )
            else:
                if min_value is None and max_value is None:
                    return f"At least one of min_value or max_value must be provided for '{criteria}' criterion."
                # number_surfaces / number_curves also take int counts
                min_val = int(min_value) if min_value is not None else None
                max_val = int(max_value) if max_value is not None else None
                matching_bodies = getattr(selection_builder.bodies, f"filter_bodies_by_{criteria}")(
                    enum_val, min_val, max_val
                )
                app_context.command_history.append(
                    f"selection_builder.bodies.filter_bodies_by_{criteria}('{enum_val_str}', {min_val}, {max_val})"
                )
        elif criteria == "color":
            if not color:
                return "color must be provided for 'color' criterion."
            matching_bodies = selection_builder.bodies.filter_bodies_by_color(color)
            app_context.command_history.append(
                f"selection_builder.bodies.filter_bodies_by_color('{color}')"
            )
        elif criteria == "name":
            if not name:
                return "name must be provided for 'name' criterion."
            matching_bodies = selection_builder.bodies.filter_bodies_by_name(name)
            app_context.command_history.append(
                f"selection_builder.bodies.filter_bodies_by_name('{name}')"
            )
        elif criteria == "containing_surface_type":
            if not surface_type:
                return "surface_type must be provided for 'containing_surface_type' criterion."
            st = _SURFACE_TYPE_MAP[surface_type]
            matching_bodies = selection_builder.bodies.filter_bodies_containing_surface_types(st)
            app_context.command_history.append(
                f"selection_builder.bodies.filter_bodies_containing_surface_types('{surface_type}')"
            )
        elif criteria == "containing_curve_type":
            if not curve_type:
                return "curve_type must be provided for 'containing_curve_type' criterion."
            ct = _CURVE_TYPE_MAP[curve_type]
            matching_bodies = selection_builder.bodies.filter_bodies_containing_curve_types(ct)
            app_context.command_history.append(
                f"selection_builder.bodies.filter_bodies_containing_curve_types('{curve_type}')"
            )
        elif criteria == "is_surface":
            matching_bodies = selection_builder.bodies.filter_surface_bodies()
            app_context.command_history.append("selection_builder.bodies.filter_surface_bodies()")
        elif criteria == "is_solid":
            matching_bodies = selection_builder.bodies.filter_solid_bodies()
            app_context.command_history.append("selection_builder.bodies.filter_solid_bodies()")
        else:
            return f"Unknown filter criterion: {criteria}"

        selection_builder._bodies = matching_bodies
        app_context.command_history.append(f"selection_builder._bodies = matching_bodies")
        logger.info(f"Filtered {len(matching_bodies.items)} bodies using criterion '{criteria}'.")
        return [body.name for body in matching_bodies.items]
    except Exception as e:
        logger.error(f"Error filtering bodies: {e}")
        return f"Error filtering bodies: {e}"


@app.tool()
def order_bodies(
    ctx: Context,
    selection_handle: str,
    criteria: Literal[
        "volume",
        "surface_area",
        "face_count",
        "edge_count",
        "loop_count",
        "number_of_surfaces",
        "number_of_curves",
    ],
) -> list[str] | str:
    """Order bodies in a selection builder by a numeric property (ascending).

    Use this tool when you want to sort bodies based on a specific numeric property.
    Pass one ``criteria`` value from the table below.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    selection_handle : str
        Handle of the selection builder to use for this query.
    criteria : str
        Property to sort by. Accepted values:

        ``"volume"``
            Sort bodies from smallest to largest volume.
        ``"surface_area"``
            Sort bodies from smallest to largest surface area.
        ``"face_count"``
            Sort bodies from fewest to most faces.
        ``"edge_count"``
            Sort bodies from fewest to most edges.
        ``"loop_count"``
            Sort bodies from fewest to most loops.
        ``"number_of_surfaces"``
            Sort bodies from fewest to most surfaces.
        ``"number_of_curves"``
            Sort bodies from fewest to most curves.

    Returns
    -------
    list of str | str
        Body names in ascending order of the specified property.
        Returns a string error message if the selection handle is invalid or if required arguments
        are missing.

    Examples
    --------
    Bodies sorted by volume (smallest first):
        ``order_bodies(criteria="volume")``

    Bodies sorted by face count:
        ``order_bodies(criteria="face_count")``

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot order bodies."

    try:
        selection_builder = app_context.selection_registry.get(selection_handle)
        app_context.command_history.append(
            f"selection_builder = selection_registry['{selection_handle}']"
        )
        if selection_builder is None:
            return f"Invalid selection handle: {selection_handle}"

        method = getattr(selection_builder.bodies, f"order_bodies_by_{criteria}", None)
        if method is None:
            return f"Unknown order criterion: {criteria}"

        ordered_bodies = method()
        app_context.command_history.append(f"selection_builder.bodies.order_bodies_by_{criteria}()")

        selection_builder._bodies = ordered_bodies
        app_context.command_history.append(f"selection_builder._bodies = ordered_bodies")
        logger.info(f"Ordered {len(ordered_bodies.items)} bodies by '{criteria}'.")
        return [body.name for body in ordered_bodies.items]
    except Exception as e:
        logger.error(f"Error ordering bodies: {e}")
        return f"Error ordering bodies: {e}"


@app.tool()
def group_bodies(
    ctx: Context,
    selection_handle: str,
    criteria: Literal[
        "volume",
        "surface_area",
        "face_count",
        "edge_count",
        "loop_count",
        "color",
        "name",
    ],
) -> list[list[str]] | str:
    """Group bodies in a selection builder by a shared property.

    Each returned group contains bodies that are equal in the chosen property.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    selection_handle : str
        Handle of the selection builder to use for this query.
    criteria : str
        Property to group by. Accepted values:

        ``"volume"``
            Group bodies with identical volumes.
        ``"surface_area"``
            Group bodies with identical surface areas.
        ``"face_count"``
            Group bodies with the same number of faces.
        ``"edge_count"``
            Group bodies with the same number of edges.
        ``"loop_count"``
            Group bodies with the same number of loops.
        ``"color"``
            Group bodies that share the same display color.
        ``"name"``
            Group bodies that share the same name.

    Returns
    -------
    list of list of str | str
        Each inner list contains the names of bodies belonging to one group.
        Returns a string error message if the selection handle is invalid or if required arguments
        are missing.

    Examples
    --------
    Group all bodies by color:
        ``group_bodies(criteria="color")``

    Group all bodies by face count:
        ``group_bodies(criteria="face_count")``

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot group bodies."

    try:
        selection_builder = app_context.selection_registry.get(selection_handle)
        app_context.command_history.append(
            f"selection_builder = selection_registry['{selection_handle}']"
        )
        if selection_builder is None:
            return f"Invalid selection handle: {selection_handle}"

        method = getattr(selection_builder.bodies, f"group_bodies_by_{criteria}", None)
        if method is None:
            return f"Unknown group criterion: {criteria}"

        groups = method()
        app_context.command_history.append(f"selection_builder.bodies.group_bodies_by_{criteria}()")

        selection_builder._bodies = groups
        app_context.command_history.append(f"selection_builder._bodies = groups")
        logger.info(f"Grouped bodies into {len(groups)} groups by '{criteria}'.")
        return [[body.name for body in group.items] for group in groups]
    except Exception as e:
        logger.error(f"Error grouping bodies: {e}")
        return f"Error grouping bodies: {e}"


@app.tool()
def extend_body_selection(
    ctx: Context,
    selection_handle: str,
    criteria: Literal[
        "volume",
        "surface_area",
        "number_of_faces",
        "number_of_edges",
        "color",
        "name",
        "nearby",
    ],
    scope: Literal["all", "visible", "body"] = "all",
    distance: float | None = None,
) -> list[str] | str:
    """Extend a body selection with additional bodies sharing a common property.

    The current selection is kept and matching bodies from the specified scope
    are added to it.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    selection_handle : str
        Handle of the selection builder to use for this query.
    criteria : str
        Rule used to find additional bodies. Accepted values:

        ``"volume"``
            Add bodies with the same volume as any body in the selection.
        ``"surface_area"``
            Add bodies with the same surface area.
        ``"number_of_faces"``
            Add bodies with the same number of faces.
        ``"number_of_edges"``
            Add bodies with the same number of edges.
        ``"color"``
            Add bodies sharing the same display color.
        ``"name"``
            Add bodies sharing the same name.
        ``"nearby"``
            Add bodies within a given distance. Requires ``distance``.
    scope : str, default: ``"all"``
        Which bodies to search when extending. Accepted values:
        ``"all"``, ``"visible"``, ``"body"``.
    distance : float, optional
        Maximum proximity distance in metres for the ``"nearby"`` criterion.

    Returns
    -------
    list of str | str
        Names of all bodies in the extended selection.
        Returns a string error message if the selection handle is invalid or if required arguments
        are missing.

    Examples
    --------
    Add bodies that share the same color:
        ``extend_body_selection(criteria="color")``

    Add bodies within 0.01 m:
        ``extend_body_selection(criteria="nearby", distance=0.01)``

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot extend body selection."

    try:
        selection_builder = app_context.selection_registry.get(selection_handle)
        app_context.command_history.append(
            f"selection_builder = selection_registry['{selection_handle}']"
        )
        if selection_builder is None:
            return f"Invalid selection handle: {selection_handle}"

        scope_val = _SCOPE_MAP[scope]

        if criteria == "nearby":
            if distance is None:
                return "distance must be provided for 'nearby' criterion."
            extended = selection_builder.bodies.extend_nearby_bodies(distance, scope_val)
            app_context.command_history.append(
                f"selection_builder.bodies.extend_nearby_bodies({distance}, '{scope}')"
            )
        else:
            method = getattr(selection_builder.bodies, f"extend_to_same_{criteria}", None)
            if method is None:
                return f"Unknown extend criterion: {criteria}"
            extended = method(scope_val)
            app_context.command_history.append(
                f"selection_builder.bodies.extend_to_same_{criteria}('{scope}')"
            )

        selection_builder._bodies = extended
        app_context.command_history.append(f"selection_builder._bodies = extended")
        logger.info(f"Extended body selection to {len(extended.items)} bodies using '{criteria}'.")
        return [body.name for body in extended.items]
    except Exception as e:
        logger.error(f"Error extending body selection: {e}")
        return f"Error extending body selection: {e}"


@app.tool()
def create_named_selection(
    ctx: Context,
    name: str,
    body_names: list[str] | None = None,
    face_ids: list[str] | None = None,
    edge_ids: list[str] | None = None,
    beam_ids: list[str] | None = None,
    design_point_ids: list[str] | None = None,
    component_names: list[str] | None = None,
    vertex_ids: list[str] | None = None,
    datum_plane_ids: list[str] | None = None,
    coordinate_system_ids: list[str] | None = None,
    datum_point_ids: list[str] | None = None,
) -> str:
    """Create a named selection containing geometry entities.

    A named selection is a labelled group of entities that can later be
    referenced by name (e.g. for meshing or boundary conditions).
    At least one entity list must be provided.

    Typical workflow: ``list_entities`` with ``entity_type="bodies"`` to find body
    names, then ``entity_type="faces"`` or ``"edges"`` on a body to obtain the face
    and edge IDs to pass here.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    name : str
        Label for the named selection.
    body_names : list of str, optional
        Body names to include. Use ``list_entities`` to discover names.
    face_ids : list of str, optional
        Face IDs to include. Use ``list_entities`` to discover face IDs of a body.
    edge_ids : list of str, optional
        Edge IDs to include. Use ``list_entities`` to discover edge IDs of a body.
    beam_ids : list of str, optional
        Beam IDs to include.
    design_point_ids : list of str, optional
        Design point IDs to include.
    component_names : list of str, optional
        Component names to include. Use ``list_entities`` to discover names.
    vertex_ids : list of str, optional
        Vertex IDs to include (from ``body.vertices``).
    datum_plane_ids : list of str, optional
        Datum plane IDs to include.
    coordinate_system_ids : list of str, optional
        Coordinate system IDs to include.
    datum_point_ids : list of str, optional
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
            body_names,
            face_ids,
            edge_ids,
            beam_ids,
            design_point_ids,
            component_names,
            vertex_ids,
            datum_plane_ids,
            coordinate_system_ids,
            datum_point_ids,
        ]
    ):
        return "At least one entity list must be provided."

    try:
        from ansys.geometry.core.misc.auxiliary import (
            get_datum_planes_from_ids,
            get_design_points_from_ids,
            get_edges_from_ids,
            get_faces_from_ids,
            get_vertices_from_ids,
        )

        design = app_context.product_instance.get_active_design()
        kwargs: dict = {}

        if body_names:
            bodies = []
            for body_name in body_names:
                body = find_body(design, body_name)
                if body is None:
                    return (
                        f"Body '{body_name}' not found. Use list_entities to see available bodies."
                    )
                bodies.append(body)
            kwargs["bodies"] = bodies

        if component_names:
            components = []
            for comp_name in component_names:
                comp = find_component(design, comp_name)
                if comp is None:
                    return f"Component '{comp_name}' not found. Use list_entities to see available components."
                components.append(comp)
            kwargs["components"] = components

        if face_ids:
            kwargs["faces"] = get_faces_from_ids(design, face_ids)

        if edge_ids:
            kwargs["edges"] = get_edges_from_ids(design, edge_ids)

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
        if body_names:
            cmd_parts.append(f"bodies=[{', '.join(f'design.get_body({b!r})' for b in body_names)}]")
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
        if component_names:
            cmd_parts.append(
                f"components=[{', '.join(f'design.get_component({c!r})' for c in component_names)}]"
            )
        if vertex_ids:
            cmd_parts.append(f"vertices=get_vertices_from_ids(design, {vertex_ids!r})")
        if datum_plane_ids:
            cmd_parts.append(f"datum_planes=get_datum_planes_from_ids(design, {datum_plane_ids!r})")
        if coordinate_system_ids:
            cmd_parts.append(
                f"coordinate_systems=[{', '.join(f'design.search_coordinate_system({c!r})' for c in coordinate_system_ids)}]"
            )
        if datum_point_ids:
            cmd_parts.append(
                f"datum_points=[{', '.join(f'design.search_datum_point({d!r})' for d in datum_point_ids)}]"
            )
        kwargs_str = ", ".join(cmd_parts)
        app_context.command_history.append(f"design.create_named_selection({name!r}, {kwargs_str})")

        logger.info(f"create_named_selection: name={name!r}")
        return f"Named selection '{name}' created successfully: {named_sel}"
    except Exception as e:
        logger.error(f"create_named_selection failed: {e}")
        return f"Error creating named selection '{name}': {e}"
