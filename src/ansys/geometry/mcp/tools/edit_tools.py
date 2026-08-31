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

"""MCP edit tools for PyAnsys Geometry MCP server.

Tools that modify bodies that already exist: boolean operations and other
in-place edits.

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
from ansys.geometry.mcp.misc.auxiliary import find_body, get_geometry_ctx

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Boolean operation tools
# ---------------------------------------------------------------------------


@app.tool()
def subtract_body(ctx: Context, target_body_name: str, tool_body_name: str) -> str:
    """Subtract one body from another (boolean subtract).

    Removes the volume of ``tool_body_name`` from ``target_body_name``.
    The tool body is consumed (deleted) after the operation.

    Use ``list_entities`` first to confirm exact body names.

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
        target = find_body(design, target_body_name)
        if target is None:
            return (
                f"Target body '{target_body_name}' not found. "
                "Use list_entities to see available bodies."
            )
        tool = find_body(design, tool_body_name)
        if tool is None:
            return f"Tool body '{tool_body_name}' not found. Use list_entities to see available bodies."
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

    Use ``list_entities`` first to confirm exact body names.

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
        target = find_body(design, target_body_name)
        if target is None:
            return (
                f"Target body '{target_body_name}' not found. "
                "Use list_entities to see available bodies."
            )
        tool = find_body(design, tool_body_name)
        if tool is None:
            return f"Tool body '{tool_body_name}' not found. Use list_entities to see available bodies."
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

    Use ``list_entities`` first to confirm exact body names.

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
        target = find_body(design, target_body_name)
        if target is None:
            return (
                f"Target body '{target_body_name}' not found. "
                "Use list_entities to see available bodies."
            )
        tool = find_body(design, tool_body_name)
        if tool is None:
            return f"Tool body '{tool_body_name}' not found. Use list_entities to see available bodies."
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
