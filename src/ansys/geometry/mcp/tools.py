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

from fastmcp.server import Context

from ansys.common.mcp.logging_config import get_logger

from ansys.geometry.mcp import app

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# TODO: Replace the example tool below with your product-specific tools.
# ---------------------------------------------------------------------------


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
    app_context = ctx.fastmcp._lifespan_result

    if app_context.product_instance is None:
        return "Product backend is not connected. Check server logs for startup errors."

    return f"Product backend is connected: {app_context.product_instance}"


# TODO: Add your product-specific tools here.
# Example template:
#
# @app.tool()
# def do_something(ctx: Context, param: str) -> str:
#     """One-line summary shown to the AI assistant.
#
#     Parameters
#     ----------
#     param : str
#         Description of the parameter.
#
#     Returns
#     -------
#     str
#         Description of the return value.
#     """
#     app_context = ctx.fastmcp._lifespan_result
#
#     if app_context.product_instance is None:
#         return "Product is not connected yet. Please try again in a moment."
#
#     try:
#         result = app_context.product_instance.do_something(param)
#         app_context.command_history.append(f"do_something({param!r})")
#         logger.info(f"do_something called with param={param!r}")
#         return str(result)
#     except Exception as e:
#         logger.error(f"do_something failed: {e}")
#         return f"Error: {e}"
