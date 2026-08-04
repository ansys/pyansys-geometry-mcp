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

"""BodySelection MCP tools for PyAnsys Geometry MCP server.

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

from ansys.common.mcp.logging_config import get_logger
from fastmcp.server import Context

from ansys.geometry.mcp import app
from ansys.geometry.mcp.selection.selection_enums import _CURVE_TYPE_MAP, _SURFACE_TYPE_MAP
from ansys.geometry.mcp.tools import get_geometry_ctx

logger = get_logger(__name__)


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
) -> list[str]:
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
            Requires at least one of ``min_value`` or ``max_value``.
        ``"surface_area"``
            Bodies whose surface area falls in [``min_value``, ``max_value``] (m²).
            Requires at least one of ``min_value`` or ``max_value``.
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
    list of str
        Names of all matching bodies, or an empty list if none match.

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
            matching_bodies = selection_builder.bodies.get_bodies_from_named_selection(named_selection)
            app_context.command_history.append(f"selection_builder.bodies.get_bodies_from_named_selection('{named_selection}')")
        elif criteria == "name":
            if not name:
                return "Body name must be provided for 'name' criterion."
            matching_bodies = selection_builder.bodies.get_bodies_with_name(name)
            app_context.command_history.append(f"selection_builder.bodies.get_bodies_with_name('{name}')")
        elif criteria in ["volume", "surface_area", "x_location", "y_location", "z_location"]:
            if min_value is None and max_value is None:
                return f"At least one of min_value or max_value must be provided for '{criteria}' criterion."
            if criteria == "volume":
                matching_bodies = selection_builder.bodies.get_bodies_with_volume(min_value, max_value)
                app_context.command_history.append(f"selection_builder.bodies.get_bodies_with_volume({min_value}, {max_value})")
            elif criteria == "surface_area":
                matching_bodies = selection_builder.bodies.get_bodies_with_surface_area(min_value, max_value)
                app_context.command_history.append(f"selection_builder.bodies.get_bodies_with_surface_area({min_value}, {max_value})")
            elif criteria == "x_location":
                matching_bodies = selection_builder.bodies.get_bodies_with_x_location(min_value, max_value)
                app_context.command_history.append(f"selection_builder.bodies.get_bodies_with_x_location({min_value}, {max_value})")
            elif criteria == "y_location":
                matching_bodies = selection_builder.bodies.get_bodies_with_y_location(min_value, max_value)
                app_context.command_history.append(f"selection_builder.bodies.get_bodies_with_y_location({min_value}, {max_value})")
            elif criteria == "z_location":
                matching_bodies = selection_builder.bodies.get_bodies_with_z_location(min_value, max_value)
                app_context.command_history.append(f"selection_builder.bodies.get_bodies_with_z_location({min_value}, {max_value})")
        elif criteria == "color":
            if not color:
                return "Color must be provided for 'color' criterion."
            matching_bodies = selection_builder.bodies.get_bodies_with_color(color)
            app_context.command_history.append(f"selection_builder.bodies.get_bodies_with_color('{color}')")
        else:
            return f"Unknown selection criterion: {criteria}"

        logger.info(f"Selected {len(matching_bodies.items)} bodies using criterion '{criteria}'.")
        return [body.name for body in matching_bodies.items]
    except Exception as e:
        logger.error(f"Error selecting bodies: {e}")
        return f"Error selecting bodies: {e}"


@app.tool()
def filter_bodies(ctx: Context,
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
    surface_type: Literal["plane", "cylinder", "cone", "torus", "sphere", "nurbs", "procedural", "spline"] | None = None,
    curve_type: Literal["line", "circle", "ellipse", "nurbs", "procedural", "helix", "spline"] | None = None,
    color: str | None = None,
) -> list[str]:
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
    
    Returns
    -------
    list of str
        Names of all bodies that satisfy the filter condition, or an empty list if none match.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot filter bodies."

    try:
        selection_builder = app_context.selection_registry.get(selection_handle)
        if selection_builder is None:
            return f"Invalid selection handle: {selection_handle}"

        if criteria in ("volume", "surface_area", "face_count", "edge_count", "loop_count"):
            if find_max:
                method = getattr(selection_builder.bodies, f"filter_bodies_max_{criteria}")
                matching_bodies = method()
                app_context.command_history.append(f"selection_builder.bodies.filter_bodies_max_{criteria}()")
            elif find_min:
                method = getattr(selection_builder.bodies, f"filter_bodies_min_{criteria}")
                matching_bodies = method()
                app_context.command_history.append(f"selection_builder.bodies.filter_bodies_min_{criteria}()")
            else:
                if min_value is None and max_value is None:
                    return f"At least one of min_value or max_value must be provided for '{criteria}' criterion."
                method = getattr(selection_builder.bodies, f"filter_bodies_by_{criteria}")
                matching_bodies = method(min_value, max_value)
                app_context.command_history.append(
                    f"selection_builder.bodies.filter_bodies_by_{criteria}({min_value}, {max_value})"
                )
        elif criteria in ("number_surfaces", "number_curves"):
            enum_key = "surface_type" if criteria == "number_surfaces" else "curve_type"
            enum_val_str = surface_type if criteria == "number_surfaces" else curve_type
            type_map = _SURFACE_TYPE_MAP if criteria == "number_surfaces" else _CURVE_TYPE_MAP
            if enum_val_str is None:
                return f"{enum_key} must be provided for '{criteria}' criterion."
            enum_val = type_map[enum_val_str]
            if find_max:
                matching_bodies = getattr(selection_builder.bodies, f"filter_bodies_max_{criteria}")(enum_val)
                app_context.command_history.append(
                    f"selection_builder.bodies.filter_bodies_max_{criteria}('{enum_val_str}')"
                )
            elif find_min:
                matching_bodies = getattr(selection_builder.bodies, f"filter_bodies_min_{criteria}")(enum_val)
                app_context.command_history.append(
                    f"selection_builder.bodies.filter_bodies_min_{criteria}('{enum_val_str}')"
                )
            else:
                if min_value is None and max_value is None:
                    return f"At least one of min_value or max_value must be provided for '{criteria}' criterion."
                matching_bodies = getattr(selection_builder.bodies, f"filter_bodies_by_{criteria}")(
                    enum_val, min_value, max_value
                )
                app_context.command_history.append(
                    f"selection_builder.bodies.filter_bodies_by_{criteria}('{enum_val_str}', {min_value}, {max_value})"
                )
        elif criteria == "color":
            if not color:
                return "color must be provided for 'color' criterion."
            matching_bodies = selection_builder.bodies.filter_bodies_by_color(color)
            app_context.command_history.append(f"selection_builder.bodies.filter_bodies_by_color('{color}')")
        elif criteria == "name":
            if not name:
                return "name must be provided for 'name' criterion."
            matching_bodies = selection_builder.bodies.filter_bodies_by_name(name)
            app_context.command_history.append(f"selection_builder.bodies.filter_bodies_by_name('{name}')")
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

        logger.info(f"Filtered {len(matching_bodies.items)} bodies using criterion '{criteria}'.")
        return [body.name for body in matching_bodies.items]
    except Exception as e:
        logger.error(f"Error filtering bodies: {e}")
        return f"Error filtering bodies: {e}"


# @app.tool()
# def order_bodies()


# @app.tool()
# def group_bodies()


# @app.tool()
# def extend_body_selection()