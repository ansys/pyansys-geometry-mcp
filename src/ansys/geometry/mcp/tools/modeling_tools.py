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

"""MCP modeling tools for PyAnsys Geometry MCP server.

Tools that create new bodies (primitives and sketch-based features) and organise
them into components.

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

       app_context = get_geometry_ctx(ctx)
       instance = app_context.product_instance

Notes
-----
Import this module in ``__main__.py`` (already done) to register all tools
with the server before it starts.

"""

from ansys.common.mcp.logging_config import get_logger
from fastmcp.server import Context

from ansys.geometry.mcp import app
from ansys.geometry.mcp.misc.auxiliary import (
    build_sketch,
    find_body,
    find_component,
    get_geometry_ctx,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Primitive body creation tools
# ---------------------------------------------------------------------------


@app.tool()
def create_box(
    ctx: Context,
    name: str,
    width: float,
    depth: float,
    height: float,
    parent_component_name: str | None = None,
    origin: list[float] = [0.0, 0.0, 0.0],
) -> str:
    """Create a 3D box (rectangular solid) body in the active design or inside a named parent component.

    Use this tool when asked to create a box, cuboid, or rectangular solid — with or without
    a parent component. Pass ``parent_component_name`` to place the box inside a specific
    component instead of the root design.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    name : str
        Name for the box body.
    width : float
        Width of the box base in meters (X direction).
    depth : float
        Depth of the box base in meters (Y direction).
    height : float
        Height (extrusion depth) of the box in meters (Z direction).
    parent_component_name : str, optional
        Name of the existing component to place the box inside. If omitted, the box is
        added to the root design. Use ``list_entities`` to find valid component names.
    origin : list[float], optional
        Origin point of the box in meters (X, Y, Z). Default is [0.0, 0.0, 0.0].

    Returns
    -------
    str
        Result message indicating success or failure.

    """
    from ansys.geometry.core.math import Plane, Point2D
    from ansys.geometry.core.misc import Distance
    from ansys.geometry.core.sketch import Sketch
    from pint import Unit

    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot create box."

    try:
        design = app_context.product_instance.get_active_design()
        parent = (
            design
            if parent_component_name is None
            else find_component(design, parent_component_name)
        )

        plane = Plane(origin=[0, 0, origin[2]])
        sketch = Sketch(plane)
        sketch.box(center=Point2D(origin[:2]), width=width, height=depth)
        body = parent.extrude_sketch(
            name=name,
            sketch=sketch,
            distance=Distance(height, unit=Unit("m")),
        )

        # Perform transcript
        # TODO: record the `Plane` import too; the transcript does not run as-is  # noqa: TD002, TD003
        app_context.command_history.append("from ansys.geometry.core.math import Point2D")
        app_context.command_history.append("from ansys.geometry.core.misc import Distance")
        app_context.command_history.append("from ansys.geometry.core.sketch import Sketch")
        app_context.command_history.append("from pint import Unit")
        app_context.command_history.append(f"plane = Plane(origin=[0, 0, {origin[2]}])")
        app_context.command_history.append(
            f"sketch = Sketch(plane); sketch.box(center=Point2D({origin[:2]}), width={width}, height={depth}); "
            f"{parent_component_name if parent_component_name is not None else 'design'}.extrude_sketch(name={name!r}, sketch=sketch, distance=Distance({height}, unit=Unit('m')))"
        )

        logger.info(
            f"create_box called: name={name!r}, width={width}, depth={depth}, height={height}"
        )
        return f"Box '{name}' ({width}m x {depth}m x {height}m) created successfully: {body}"
    except Exception as e:
        logger.error(f"create_box failed: {e}")
        return f"Error creating box '{name}': {e}"


# ---------------------------------------------------------------------------
# Sketch-based body creation tools
# ---------------------------------------------------------------------------


@app.tool()
def extrude_sketch(
    ctx: Context,
    name: str,
    sketch_primitives: list[dict],
    distance: float,
    plane_origin: list[float] | None = None,
    plane_dir_x: list[float] | None = None,
    plane_dir_y: list[float] | None = None,
    component_name: str | None = None,
) -> str:
    """Extrude a 2D sketch into a 3D body.

    Builds a sketch from the given primitives on an optional plane and extrudes
    it by ``distance`` metres along the plane normal (+Z by default).

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    name : str
        Name for the resulting body.
    sketch_primitives : list of dict
        Sketch primitive definitions. Each dict must have a ``"type"`` key.
        Supported types and their required fields (all lengths in metres):

        - ``"circle"``:  ``center_x``, ``center_y``, ``radius``
        - ``"box"``:     ``center_x``, ``center_y``, ``width``, ``height``
        - ``"polygon"``: ``center_x``, ``center_y``, ``inner_radius`` (apothem),
          ``sides``
        - ``"segment"``: ``start_x``, ``start_y``, ``end_x``, ``end_y``
        - ``"arc"``:     ``center_x``, ``center_y``, ``start_x``, ``start_y``,
          ``end_x``, ``end_y``; optional ``clockwise`` (bool, default ``false``)

    distance : float
        Extrusion distance in metres. Positive extrudes along the plane normal;
        negative extrudes in the opposite direction.
    plane_origin : list of float, optional
        ``[x, y, z]`` origin of the sketch plane. Defaults to ``[0, 0, 0]``.
    plane_dir_x : list of float, optional
        ``[x, y, z]`` X direction of the sketch plane. Defaults to ``[1, 0, 0]``.
    plane_dir_y : list of float, optional
        ``[x, y, z]`` Y direction of the sketch plane. Defaults to ``[0, 1, 0]``.
        The extrusion normal is ``plane_dir_x × plane_dir_y``.
    component_name : str, optional
        Name of the component to add the body to. Defaults to the root design.

    Returns
    -------
    str
        Result message with body information, or an error message.

    """
    from pint import Quantity

    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot extrude sketch."

    try:
        design = app_context.product_instance.get_active_design()
        target = design if component_name is None else find_component(design, component_name)
        if target is None:
            return f"Component '{component_name}' not found."

        sketch, commands = build_sketch(sketch_primitives, plane_origin, plane_dir_x, plane_dir_y)
        body = target.extrude_sketch(name=name, sketch=sketch, distance=Quantity(distance, "m"))

        # Perform transcript
        app_context.command_history.append("from pint import Quantity")
        app_context.command_history.append(
            f"target = design if {component_name!r} is None else design.get_component({component_name!r})"
        )
        app_context.command_history.extend(commands)
        app_context.command_history.append(
            f"target.extrude_sketch(name={name!r}, sketch=sketch, distance=Quantity({distance}, 'm'))"
        )
        logger.info(f"extrude_sketch: name={name!r}")
        return f"Body '{name}' extruded successfully: {body}"
    except Exception as e:
        logger.error(f"extrude_sketch failed: {e}")
        return f"Error extruding sketch '{name}': {e}"


@app.tool()
def revolve_sketch(
    ctx: Context,
    name: str,
    sketch_primitives: list[dict],
    axis_direction: list[float],
    rotation_origin: list[float],
    angle_deg: float = 360.0,
    plane_origin: list[float] | None = None,
    plane_dir_x: list[float] | None = None,
    plane_dir_y: list[float] | None = None,
    component_name: str | None = None,
) -> str:
    """Revolve a 2D sketch around an axis to create a body of revolution.

    Preferred over sweep for axisymmetric and curved shapes (torus, pipe,
    flange, fillet) due to higher backend reliability.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    name : str
        Name for the resulting body.
    sketch_primitives : list of dict
        Sketch primitives. Same format as ``extrude_sketch``. All lengths in metres.
    axis_direction : list of float
        ``[x, y, z]`` direction vector of the revolution axis (does not need to
        be normalised).
    rotation_origin : list of float
        ``[x, y, z]`` point the revolution axis passes through. Required by the
        backend — omitting it raises an error.
    angle_deg : float, optional
        Revolution angle in degrees. Default is ``360.0`` (full revolution).
    plane_origin : list of float, optional
        ``[x, y, z]`` origin of the sketch plane. Defaults to ``[0, 0, 0]``.
    plane_dir_x : list of float, optional
        ``[x, y, z]`` X direction of the sketch plane. Defaults to ``[1, 0, 0]``.
    plane_dir_y : list of float, optional
        ``[x, y, z]`` Y direction of the sketch plane. Defaults to ``[0, 1, 0]``.
    component_name : str, optional
        Name of the component to add the body to. Defaults to the root design.

    Returns
    -------
    str
        Result message with body information, or an error message.

    """
    from ansys.geometry.core.math import Point3D, Vector3D
    from pint import Quantity

    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot revolve sketch."

    try:
        design = app_context.product_instance.get_active_design()
        target = design if component_name is None else find_component(design, component_name)
        if target is None:
            return f"Component '{component_name}' not found."

        sketch, commands = build_sketch(sketch_primitives, plane_origin, plane_dir_x, plane_dir_y)
        body = target.revolve_sketch(
            name=name,
            sketch=sketch,
            axis=Vector3D(axis_direction),
            angle=Quantity(angle_deg, "degree"),
            rotation_origin=Point3D(rotation_origin),
        )
        # Perform transcript
        app_context.command_history.append(
            "from ansys.geometry.core.math import Point3D, Vector3D; from pint import Quantity"
        )
        app_context.command_history.append(
            f"target = design if {component_name!r} is None else design.get_component({component_name!r})"
        )
        app_context.command_history.extend(commands)
        app_context.command_history.append(
            f"target.revolve_sketch(name={name!r}, sketch=sketch, axis=Vector3D({axis_direction}), "
            f"angle=Quantity({angle_deg}, 'degree'), rotation_origin=Point3D({rotation_origin}))"
        )
        logger.info(f"revolve_sketch: name={name!r}")
        return f"Body '{name}' revolved successfully: {body}"
    except Exception as e:
        logger.error(f"revolve_sketch failed: {e}")
        return f"Error revolving sketch '{name}': {e}"


# ---------------------------------------------------------------------------
# Component management tools
# ---------------------------------------------------------------------------


@app.tool()
def add_component(ctx: Context, name: str, parent_component_name: str | None = None) -> str:
    """Add a named component to the active design or to a parent component.

    Components group related bodies and support nesting. The guide recommends
    always creating bodies inside components rather than directly on the design.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    name : str
        Name for the new component.
    parent_component_name : str, optional
        Name of an existing component to nest this component inside.
        If omitted, the component is added directly to the root design.

    Returns
    -------
    str
        Result message with component information, or an error message.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot add component."

    try:
        design = app_context.product_instance.get_active_design()

        if parent_component_name:
            parent = find_component(design, parent_component_name)
            if parent is None:
                return f"Parent component '{parent_component_name}' not found in the active design."
            comp = parent.add_component(name)
            app_context.command_history.append(
                f"{name}_comp = {parent_component_name}_comp.add_component({name!r})"
            )
        else:
            comp = design.add_component(name)
            app_context.command_history.append(f"{name}_comp = design.add_component({name!r})")

        logger.info(f"add_component: name={name!r}, parent={parent_component_name!r}")
        return f"Component '{name}' added successfully: {comp}"
    except Exception as e:
        logger.error(f"add_component failed: {e}")
        return f"Error adding component '{name}': {e}"


@app.tool()
def move_body_to_component(ctx: Context, body_name: str, target_component_name: str) -> str:
    """Move an existing body into a named component.

    Use this tool when asked to move, reassign, or place a body inside a component.
    Use ``list_entities`` first to confirm the exact body and component names.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    body_name : str
        Exact name of the body to move.
    target_component_name : str
        Exact name of the destination component.

    Returns
    -------
    str
        Result message indicating success or failure.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot move body."

    try:
        design = app_context.product_instance.get_active_design()

        body = find_body(design, body_name)
        if body is None:
            return f"Body '{body_name}' not found. Use list_entities to see available bodies."
        comp = find_component(design, target_component_name)
        if comp is None:
            return f"Component '{target_component_name}' not found. Use list_entities to see available components."
        comp.move_bodies_to_component([body])

        # Perform transcript
        app_context.command_history.append(
            f"{target_component_name}_comp.move_bodies_to_component([{body_name}_body])"
        )

        logger.info(f"move_body_to_component: body={body_name!r}, target={target_component_name!r}")
        return f"Body '{body_name}' moved to component '{target_component_name}' successfully."
    except Exception as e:
        logger.error(f"move_body_to_component failed: {e}")
        return f"Error moving body '{body_name}': {e}"
