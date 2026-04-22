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
    """Execute arbitrary Python code in the product backend's Python session.

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
        app_context.command_history.append(f"design=modeler.create_design({design_name!r})")
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
def create_box(
    ctx: Context,
    name: str,
    width: float,
    depth: float,
    height: float,
) -> str:
    """Create a 3D box (rectangular solid) body in the active design.

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
        sketch = Sketch()
        sketch.box(center=Point2D([0, 0]), width=width, height=depth)
        body = design.extrude_sketch(
            name=name,
            sketch=sketch,
            distance=Distance(height, unit=Unit("m")),
        )
        app_context.command_history.append(
            f"sketch = Sketch(); sketch.box(center=Point2D([0, 0]), width={width}, height={depth}); "
            f"design.extrude_sketch(name={name!r}, sketch=sketch, distance=Distance({height}, unit=Unit('m')))"
        )
        logger.info(
            f"create_box called: name={name!r}, width={width}, depth={depth}, height={height}"
        )
        return f"Box '{name}' ({width}m x {depth}m x {height}m) created successfully: {body}"
    except Exception as e:
        logger.error(f"create_box failed: {e}")
        return f"Error creating box '{name}': {e}"


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
def get_design_3d_scene(ctx: Context, path: str | None = None) -> str:
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
        _ = design.plot(screenshot=path)
        app_context.command_history.append(f"design.plot(screenshot={path!r})")
        logger.info(f"get_design_3d_scene called, saved to {path}")
        return f"3D scene screenshot saved: {path}"
    except Exception as e:
        logger.error(f"get_design_3d_scene failed: {e}")
        return f"Error getting 3D scene screenshot: {e}"


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
