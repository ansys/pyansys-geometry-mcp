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
        Predefined variables : 
        instance -> is the instance of ansys.geometry.core.Modeler() that should be used
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
    return await shared_tools.execute_python_code(ctx, code, timeout=60)


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
def export_design_to_fmd(ctx: Context, location: str | None = None) -> str:
    """Export the current active design to an FMD file.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    location : str, optional
        File path on disk to save the FMD file. If not provided, the file
        is saved in the current working directory.

    Returns
    -------
    str
        The path to the saved FMD file, or an error message if export fails.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot export design."

    try:
        design = app_context.product_instance.get_active_design()
        saved_path = design.export_to_fmd(location)
        logger.info(f"export_design_to_fmd called, saved to {saved_path}")
        app_context.command_history.append(f"design.export_to_fmd({location!r})")
        return f"Design exported to FMD file: {saved_path}"
    except Exception as e:
        logger.error(f"export_design_to_fmd failed: {e}")
        return f"Error exporting design to FMD: {e}"
