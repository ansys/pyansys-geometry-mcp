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

"""MCP tools for PyAnsys Geometry MCP server.

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
Import this module in ``__main__.py`` (already done) to register all tools
with the server before it starts.

"""

import time
import uuid

from ansys.common.mcp.logging_config import get_logger
import ansys.common.mcp.tools as shared_tools
from fastmcp.server import Context
from websockets.asyncio.async_timeout import timeout

from ansys.geometry.mcp import PyAnsysGeometryContext, app

logger = get_logger(__name__)


def get_geometry_ctx(ctx: Context) -> "PyAnsysGeometryContext":
    """Access the PyAnsysGeometryContext from the MCP context."""
    return ctx.fastmcp._lifespan_result  # type: ignore[return-value]


@app.tool()
def read_image_in_base64(ctx: Context, image_path: str) -> dict[str, str]:
    """Read an image file and return its contents as a base64-encoded string.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    image_path : str
        Path to the image file to read.

    Returns
    -------
    dict of str
        A dictionary with a single key "base64" containing the base64-encoded
        contents of the image, or an error message if reading fails.

    """
    import base64
    from pathlib import Path

    try:
        with Path(image_path).open("rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            return {"base64": encoded}
    except Exception as e:
        logger.error(f"read_image_in_base64 failed: {e}")
        return {"error": f"Error reading image '{image_path}': {e}"}


@app.tool()
def get_command_history(ctx: Context) -> list[str]:
    """Get the history of commands executed in the product backend.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).

    Returns
    -------
    list of str
        List of command strings that have been executed.

    """
    app_context = get_geometry_ctx(ctx)
    return app_context.command_history


@app.tool()
def get_transcript(ctx: Context) -> str:
    """Get a transcript of the current session, including all executed commands.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).

    Returns
    -------
    str
        A formatted transcript of the session.

    """
    app_context = get_geometry_ctx(ctx)
    commands = "\n".join(app_context.command_history)

    # Format Python script using import sorting and black-style formatting
    try:
        import black
        import isort

        sorted_commands = isort.code(commands)
        formatted_commands = black.format_str(sorted_commands, mode=black.Mode())
        return formatted_commands if formatted_commands else "No commands executed yet."
    except (ImportError, black.InvalidInput):
        return commands if commands else "No commands executed yet."


@app.tool()
def get_product_status(ctx: Context) -> str:
    """Return the current status of the product backend.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).

    Returns
    -------
    str
        Status message describing whether the product is connected.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Check server logs for startup errors."

    return f"Product backend is connected: {app_context.product_instance}"


@app.tool()
async def run_python_code(ctx: Context, code: str) -> str:
    """Execute arbitrary Python code in the product backend's Python session. Session is persistent - variables inside remain available.

    Predefined variables : ``instance`` -> is the instance of ansys.geometry.core.Modeler()
    that should be used.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    code : str
        The Python code to execute.

    Returns
    -------
    str
        The output or result of the executed code, or an error message if execution fails.

    """
    import json

    result = await shared_tools.execute_python_code(ctx, code, timeout=60)
    try:
        parsed = json.loads(result)
        if parsed.get("success"):
            app_context = get_geometry_ctx(ctx)
            app_context.command_history.append(code)
    except (json.JSONDecodeError, AttributeError):
        pass
    return result


@app.tool()
def create_design(ctx: Context, design_name: str) -> str:
    """Create a new design in the product backend.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    design_name : str
        Name of the design to create.

    Returns
    -------
    str
        Result message indicating success or failure.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot create design."

    try:
        app_context.product_instance.create_design(design_name)

        # Perform transcript
        app_context.command_history.append(f"design=instance.create_design({design_name!r})")

        logger.info(f"create_design called with design_name={design_name!r}")
        return f"Design '{design_name}' created successfully."
    except Exception as e:
        logger.error(f"create_design failed: {e}")
        return f"Error creating design '{design_name}': {e}"


@app.tool()
def get_design_info(ctx: Context) -> str:
    """Get information about the current active design.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).

    Returns
    -------
    str
        Information about the design, or an error message if retrieval fails.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot retrieve design info."

    try:
        design = app_context.product_instance.get_active_design()
        logger.info("get_design_info called")
        return str(design)
    except Exception as e:
        logger.error(f"get_design_info failed: {e}")
        return f"Error retrieving info for design: {e}"


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

        logger.info("create_selection_builder called")
        return handle
    except Exception as e:
        logger.error(f"create_selection_builder failed: {e}")
        return f"Error creating selection builder: {e}"


@app.tool()
def create_box(
    ctx: Context,
    name: str,
    width: float,
    depth: float,
    height: float,
    parent_component_name: str | None = None,
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
        added to the root design. Use ``list_components`` to find valid component names.

    Returns
    -------
    str
        Result message indicating success or failure.

    """
    from ansys.geometry.core.math import Point2D
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
            else _find_component(design, parent_component_name)
        )

        sketch = Sketch()
        sketch.box(center=Point2D([0, 0]), width=width, height=depth)
        body = parent.extrude_sketch(
            name=name,
            sketch=sketch,
            distance=Distance(height, unit=Unit("m")),
        )

        # Perform transcript
        app_context.command_history.append("from ansys.geometry.core.math import Point2D")
        app_context.command_history.append("from ansys.geometry.core.misc import Distance")
        app_context.command_history.append("from ansys.geometry.core.sketch import Sketch")
        app_context.command_history.append("from pint import Unit")
        app_context.command_history.append(
            f"sketch = Sketch(); sketch.box(center=Point2D([0, 0]), width={width}, height={depth}); "
            f"{parent_component_name if parent_component_name is not None else 'design'}.extrude_sketch(name={name!r}, sketch=sketch, distance=Distance({height}, unit=Unit('m')))"
        )

        logger.info(
            f"create_box called: name={name!r}, width={width}, depth={depth}, height={height}"
        )
        return f"Box '{name}' ({width}m x {depth}m x {height}m) created successfully: {body}"
    except Exception as e:
        logger.error(f"create_box failed: {e}")
        return f"Error creating box '{name}': {e}"


@app.tool()
def move_body_to_component(ctx: Context, body_name: str, target_component_name: str) -> str:
    """Move an existing body into a named component.

    Use this tool when asked to move, reassign, or place a body inside a component.
    Use ``list_bodies`` and ``list_components`` first to confirm exact names.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    body_name : str
        Exact name of the body to move (use ``list_bodies`` to find it).
    target_component_name : str
        Exact name of the destination component (use ``list_components`` to find it).

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

        body = _find_body(design, body_name)
        if body is None:
            return f"Body '{body_name}' not found. Use list_bodies to see available bodies."
        comp = _find_component(design, target_component_name)
        if comp is None:
            return f"Component '{target_component_name}' not found. Use list_components to see available components."
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


@app.tool()
def export_design_to(ctx: Context, file_format: str, folder: str | None = None) -> str:
    """Export the current active design to a specified format.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    file_format : str
        The format to export the design to. Options are 'fmd', 'step', 'iges', 'scdocx',
        'disco', 'parasolid_text', 'parasolid_bin'.
    folder : str, optional
        Folder on disk to save the design. If not provided, the file
        is saved in the current working directory.

    Returns
    -------
    str
        The path to the saved design file, or an error message if export fails.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot export design."

    try:
        from ansys.geometry.core.designer import DesignFileFormat

        design = app_context.product_instance.get_active_design()
        # Depending on format... Use DesignFileFormat enum
        if file_format.lower() == DesignFileFormat.FMD.name.lower():
            saved_path = design.export_to_fmd(folder)
            app_context.command_history.append(f"design.export_to_fmd({folder!r})")
        elif file_format.lower() == DesignFileFormat.STEP.name.lower():
            saved_path = design.export_to_step(folder)
            app_context.command_history.append(f"design.export_to_step({folder!r})")
        elif file_format.lower() == DesignFileFormat.IGES.name.lower():
            saved_path = design.export_to_iges(folder)
            app_context.command_history.append(f"design.export_to_iges({folder!r})")
        elif file_format.lower() == DesignFileFormat.SCDOCX.name.lower():
            saved_path = design.export_to_scdocx(folder)
            app_context.command_history.append(f"design.export_to_scdocx({folder!r})")
        elif file_format.lower() == DesignFileFormat.DISCO.name.lower():
            saved_path = design.export_to_disco(folder)
            app_context.command_history.append(f"design.export_to_disco({folder!r})")
        elif file_format.lower() == DesignFileFormat.PARASOLID_TEXT.name.lower():
            saved_path = design.export_to_parasolid_text(folder)
            app_context.command_history.append(f"design.export_to_parasolid_text({folder!r})")
        elif file_format.lower() == DesignFileFormat.PARASOLID_BIN.name.lower():
            saved_path = design.export_to_parasolid_bin(folder)
            app_context.command_history.append(f"design.export_to_parasolid_bin({folder!r})")
        else:
            return f"Unsupported format '{file_format}'. Supported formats are:"
        " fmd, step, iges, scdocx, disco, parasolid_text, parasolid_bin."

        logger.info(f"export_design_to called, saved to {saved_path}")
        return f"Design exported to {file_format.upper()} file: {saved_path}"
    except Exception as e:
        logger.error(f"export_design_to failed: {e}")
        return f"Error exporting design to {file_format.upper()}: {e}"


@app.tool()
def get_screenshot(ctx: Context, path: str | None = None) -> str:
    """Get a 3D scene screenshot of the current active design.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    path : str, optional
        Path to save the 3D scene screenshot. If not provided, a default path is used.

    Returns
    -------
    str
        Path to the saved 3D scene screenshot, or an error message if the operation fails.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot get 3D scene."

    # Path can be provided by user or default to current working directory
    # with a timestamped filename
    path = path or f"design_3d_scene_{int(time.time())}.png"

    try:
        design = app_context.product_instance.get_active_design()
        _ = design.plot(screenshot=path, use_service_colors=True)  # noqa: F841

        # Perform transcript
        app_context.command_history.append(
            f"design.plot(screenshot={path!r}, use_service_colors=True)"
        )

        logger.info(f"get_design_3d_scene called, saved to {path}")
        return f"3D scene screenshot saved: {path}"
    except Exception as e:
        logger.error(f"get_design_3d_scene failed: {e}")
        return f"Error getting 3D scene screenshot: {e}"


@app.tool()
def get_design_3d_scene(ctx: Context) -> None:
    """Get a 3D scene window of the current active design.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot get 3D scene."

    try:
        design = app_context.product_instance.get_active_design()
        _ = design.plot(use_service_colors=True)  # noqa: F841

        return f"3D scene window opened."
    except Exception as e:
        logger.error(f"get_design_3d_scene failed: {e}")
        return f"Error getting 3D scene window: {e}"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _find_body(design, body_name: str):
    """Find a body by name across the full design tree.

    Uses ``Component.get_all_bodies()``, which recursively collects every body
    in the component hierarchy.
    """
    for body in design.get_all_bodies():
        if body.name == body_name:
            return body
    return None


def _find_component(design, component_name: str):
    """Find a component by name across the full design tree.

    Uses ``Design._get_all_components()``, which recursively collects every
    component in the design hierarchy.
    """
    for comp in design._get_all_components():
        if comp.name == component_name:
            return comp
    return None


def _build_sketch(
    sketch_primitives: list[dict],
    plane_origin: list[float] | None = None,
    plane_dir_x: list[float] | None = None,
    plane_dir_y: list[float] | None = None,
):
    """Build a Sketch from a list of primitive dicts and an optional plane definition.

    Parameters
    ----------
    sketch_primitives : list of dict
        Each dict must have a ``"type"`` key. See ``extrude_sketch`` for supported types.
    plane_origin : list of float, optional
        ``[x, y, z]`` origin of the sketch plane.
    plane_dir_x : list of float, optional
        ``[x, y, z]`` X direction of the sketch plane.
    plane_dir_y : list of float, optional
        ``[x, y, z]`` Y direction of the sketch plane.

    Returns
    -------
    Sketch
        The populated sketch object.

    """
    from ansys.geometry.core.math import Plane, Point2D, Point3D, UnitVector3D
    from ansys.geometry.core.sketch import Sketch

    accumulated_commands: list[str] = []

    if plane_origin is not None and plane_dir_x is not None and plane_dir_y is not None:
        sketch = Sketch(
            Plane(
                origin=Point3D(plane_origin),
                direction_x=UnitVector3D(plane_dir_x),
                direction_y=UnitVector3D(plane_dir_y),
            )
        )
        accumulated_commands.append(
            f"sketch = Sketch(Plane(origin=Point3D({plane_origin}), "
            f"direction_x=UnitVector3D({plane_dir_x}), "
            f"direction_y=UnitVector3D({plane_dir_y})))"
        )
    else:
        sketch = Sketch()
        accumulated_commands.append("sketch = Sketch()")

    for prim in sketch_primitives:
        prim_type = prim.get("type", "").lower()
        center = Point2D([prim.get("center_x", 0.0), prim.get("center_y", 0.0)])

        if prim_type == "circle":
            sketch.circle(center=center, radius=prim["radius"])
            accumulated_commands.append(
                f"sketch.circle(center=Point2D({[prim.get('center_x', 0.0), prim.get('center_y', 0.0)]}), radius={prim['radius']})"
            )
        elif prim_type == "box":
            sketch.box(center=center, width=prim["width"], height=prim["height"])
            accumulated_commands.append(
                f"sketch.box(center=Point2D({[prim.get('center_x', 0.0), prim.get('center_y', 0.0)]}), width={prim['width']}, height={prim['height']})"
            )
        elif prim_type == "polygon":
            # inner_radius is the apothem (distance from centre to midpoint of a side)
            sketch.polygon(
                center=center,
                inner_radius=prim["inner_radius"],
                sides=int(prim["sides"]),
            )
            accumulated_commands.append(
                f"sketch.polygon(center=Point2D({[prim.get('center_x', 0.0), prim.get('center_y', 0.0)]}), inner_radius={prim['inner_radius']}, sides={int(prim['sides'])})"
            )
        elif prim_type == "segment":
            sketch.segment(
                start=Point2D([prim["start_x"], prim["start_y"]]),
                end=Point2D([prim["end_x"], prim["end_y"]]),
            )
            accumulated_commands.append(
                f"sketch.segment(start=Point2D([{prim['start_x']}, {prim['start_y']}]), end=Point2D([{prim['end_x']}, {prim['end_y']}])"
            )
        elif prim_type == "arc":
            # arc requires start, end, and center points
            sketch.arc(
                start=Point2D([prim["start_x"], prim["start_y"]]),
                end=Point2D([prim["end_x"], prim["end_y"]]),
                center=center,
                clockwise=prim.get("clockwise", False),
            )
            accumulated_commands.append(
                f"sketch.arc(start=Point2D([{prim['start_x']}, {prim['start_y']}]), end=Point2D([{prim['end_x']}, {prim['end_y']}]), center=Point2D({[prim.get('center_x', 0.0), prim.get('center_y', 0.0)]}), clockwise={prim.get('clockwise', False)})"
            )
        else:
            raise ValueError(
                f"Unsupported sketch primitive type: {prim_type!r}. "
                "Supported types: circle, box, polygon, segment, arc."
            )

    return sketch, accumulated_commands


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
            parent = _find_component(design, parent_component_name)
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
def list_components(ctx: Context) -> str:
    """List all components in the active design as an indented tree.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).

    Returns
    -------
    str
        Indented tree of component names, or an error message.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot list components."

    try:
        design = app_context.product_instance.get_active_design()

        def _collect(node, indent: int) -> list[str]:
            lines = []
            for comp in node.components:
                lines.append("  " * indent + comp.name)
                lines.extend(_collect(comp, indent + 1))
            return lines

        lines = _collect(design, 0)
        logger.info("list_components called")
        return "\n".join(lines) if lines else "No components found in the active design."
    except Exception as e:
        logger.error(f"list_components failed: {e}")
        return f"Error listing components: {e}"


@app.tool()
def list_bodies(ctx: Context, component_name: str | None = None) -> str:
    """List all bodies in the active design or a specific component.

    Returns each body's name prefixed with its component path, e.g.
    ``MainComponent/Cylinder``. Use this before boolean operations to
    discover the exact body names required.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    component_name : str, optional
        Restrict the listing to a specific component and its children.
        Lists the full design tree if omitted.

    Returns
    -------
    str
        Newline-separated list of body paths, or an error message.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot list bodies."

    try:
        design = app_context.product_instance.get_active_design()
        root = design if component_name is None else _find_component(design, component_name)
        if root is None:
            return f"Component '{component_name}' not found."

        def _collect(node, prefix: str) -> list[str]:
            lines = [f"{prefix}{body.name}" for body in node.bodies]
            for comp in node.components:
                lines.extend(_collect(comp, f"{prefix}{comp.name}/"))
            return lines

        lines = _collect(root, "")
        logger.info("list_bodies called")
        return "\n".join(lines) if lines else "No bodies found."
    except Exception as e:
        logger.error(f"list_bodies failed: {e}")
        return f"Error listing bodies: {e}"


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
        target = design if component_name is None else _find_component(design, component_name)
        if target is None:
            return f"Component '{component_name}' not found."

        sketch, commands = _build_sketch(sketch_primitives, plane_origin, plane_dir_x, plane_dir_y)
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
        target = design if component_name is None else _find_component(design, component_name)
        if target is None:
            return f"Component '{component_name}' not found."

        sketch, commands = _build_sketch(sketch_primitives, plane_origin, plane_dir_x, plane_dir_y)
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
# Boolean operation tools
# ---------------------------------------------------------------------------


@app.tool()
def subtract_body(ctx: Context, target_body_name: str, tool_body_name: str) -> str:
    """Subtract one body from another (boolean subtract).

    Removes the volume of ``tool_body_name`` from ``target_body_name``.
    The tool body is consumed (deleted) after the operation.

    Use ``list_bodies`` first to confirm exact body names.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    target_body_name : str
        Name of the body to subtract from (survives the operation).
    tool_body_name : str
        Name of the body whose volume is removed (consumed after the operation).

    Returns
    -------
    str
        Confirmation message, or an error message.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot subtract bodies."

    try:
        design = app_context.product_instance.get_active_design()
        target = _find_body(design, target_body_name)
        if target is None:
            return (
                f"Target body '{target_body_name}' not found. "
                "Use list_bodies to see available bodies."
            )
        tool = _find_body(design, tool_body_name)
        if tool is None:
            return (
                f"Tool body '{tool_body_name}' not found. Use list_bodies to see available bodies."
            )
        target.subtract(tool)
        logger.info(f"subtract_body: target={target_body_name!r}, tool={tool_body_name!r}")

        # Perform transcript
        app_context.command_history.append(f"target = design.get_body({target_body_name!r})")
        app_context.command_history.append(f"tool = design.get_body({tool_body_name!r})")
        app_context.command_history.append("target.subtract(tool)")

        return (
            f"Boolean subtract complete: '{tool_body_name}' subtracted from "
            f"'{target_body_name}'. '{tool_body_name}' has been consumed."
        )
    except Exception as e:
        logger.error(f"subtract_body failed: {e}")
        return f"Error subtracting '{tool_body_name}' from '{target_body_name}': {e}"


@app.tool()
def unite_body(ctx: Context, target_body_name: str, tool_body_name: str) -> str:
    """Merge two bodies into one (boolean union).

    Merges ``tool_body_name`` into ``target_body_name``.
    The tool body is consumed (deleted) after the operation.

    Use ``list_bodies`` first to confirm exact body names.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    target_body_name : str
        Name of the body to merge into (survives the operation).
    tool_body_name : str
        Name of the body to merge from (consumed after the operation).

    Returns
    -------
    str
        Confirmation message, or an error message.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot unite bodies."

    try:
        design = app_context.product_instance.get_active_design()
        target = _find_body(design, target_body_name)
        if target is None:
            return (
                f"Target body '{target_body_name}' not found. "
                "Use list_bodies to see available bodies."
            )
        tool = _find_body(design, tool_body_name)
        if tool is None:
            return (
                f"Tool body '{tool_body_name}' not found. Use list_bodies to see available bodies."
            )
        target.unite(tool)

        # Perform transcript
        app_context.command_history.append(f"target = design.get_body({target_body_name!r})")
        app_context.command_history.append(f"tool = design.get_body({tool_body_name!r})")
        app_context.command_history.append("target.unite(tool)")

        logger.info(f"unite_body: target={target_body_name!r}, tool={tool_body_name!r}")
        return (
            f"Boolean union complete: '{tool_body_name}' merged into "
            f"'{target_body_name}'. '{tool_body_name}' has been consumed."
        )
    except Exception as e:
        logger.error(f"unite_body failed: {e}")
        return f"Error uniting '{tool_body_name}' into '{target_body_name}': {e}"


@app.tool()
def intersect_body(ctx: Context, target_body_name: str, tool_body_name: str) -> str:
    """Keep only the overlapping volume of two bodies (boolean intersection).

    ``target_body_name`` is replaced with the volume common to both bodies.
    The tool body is consumed (deleted) after the operation.

    Use ``list_bodies`` first to confirm exact body names.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    target_body_name : str
        Name of the body to intersect into (survives the operation, modified).
    tool_body_name : str
        Name of the body to intersect with (consumed after the operation).

    Returns
    -------
    str
        Confirmation message, or an error message.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot intersect bodies."

    try:
        design = app_context.product_instance.get_active_design()
        target = _find_body(design, target_body_name)
        if target is None:
            return (
                f"Target body '{target_body_name}' not found. "
                "Use list_bodies to see available bodies."
            )
        tool = _find_body(design, tool_body_name)
        if tool is None:
            return (
                f"Tool body '{tool_body_name}' not found. Use list_bodies to see available bodies."
            )
        target.intersect(tool)

        # Perform transcript
        app_context.command_history.append(f"target = design.get_body({target_body_name!r})")
        app_context.command_history.append(f"tool = design.get_body({tool_body_name!r})")
        app_context.command_history.append("target.intersect(tool)")

        logger.info(f"intersect_body: target={target_body_name!r}, tool={tool_body_name!r}")
        return (
            f"Boolean intersection complete: '{target_body_name}' now contains only the "
            f"overlapping volume. '{tool_body_name}' has been consumed."
        )
    except Exception as e:
        logger.error(f"intersect_body failed: {e}")
        return f"Error intersecting '{tool_body_name}' with '{target_body_name}': {e}"
