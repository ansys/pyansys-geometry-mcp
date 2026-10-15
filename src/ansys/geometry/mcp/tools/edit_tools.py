# Copyright (C) 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""MCP edit tools for PyAnsys Geometry-MCP.

Tools that modify bodies that already exist: Boolean operations and other
in-place edits.

Each function decorated with ``@app.tool()`` is exposed as an MCP tool.
The ``ctx`` parameter provides access to the app context (and thus
to the live product instance and command history).

How to add a tool
-----------------
1. Define a Python function with type-annotated parameters.
2. Add a NumPy-style docstring. The summary line becomes the tool description
   visible to the AI assistant.
3. Decorate it with ``@app.tool()``.
4. Access the product instance::

       app_context = get_geometry_ctx(ctx)
       instance = app_context.product_instance

Notes
-----
Import this module in ``__main__.py`` (already done) to register all tools
with the server before it starts.

"""

from typing import Literal

from ansys.common.mcp.logging_config import get_logger
from fastmcp.server import Context

from ansys.geometry.mcp import app
from ansys.geometry.mcp.misc.auxiliary import find_body, get_geometry_ctx

logger = get_logger(__name__)


@app.tool()
def boolean_operation(
    ctx: Context,
    operation: Literal["subtract", "unite", "intersect"],
    target_body_name: str,
    tool_body_name: str,
) -> str:
    """Perform a Boolean subtract, union, or intersection on two bodies.

    The target body survives the operation and the tool body is consumed.

    - For ``subtract``, the tool body's volume is removed from the target.
    - For ``unite``, the tool is merged into the target.
    - For ``intersect``, the target is reduced to the volume common to both bodies.

    Use ``list_entities`` first to confirm exact body names.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    operation : Literal["subtract", "unite", "intersect"]
        Boolean operation to perform.
    target_body_name : str
        Name of the body to modify (survives the operation).
    tool_body_name : str
        Name of the body used in the operation (consumed afterward).

    Returns
    -------
    str
        Confirmation message, or an error message.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot perform Boolean operation."

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
            return (
                f"Tool body '{tool_body_name}' not found. "
                "Use list_entities to see available bodies."
            )
        operation_methods = {
            "subtract": target.subtract,
            "unite": target.unite,
            "intersect": target.intersect,
        }
        operation_methods[operation](tool)

        app_context.command_history.append(f"target = design.get_body({target_body_name!r})")
        app_context.command_history.append(f"tool = design.get_body({tool_body_name!r})")
        app_context.command_history.append(f"target.{operation}(tool)")

        logger.info(
            f"Boolean_operation: operation={operation!r}, target={target_body_name!r}, "
            f"tool={tool_body_name!r}"
        )
        return (
            f"Boolean {operation} complete for '{target_body_name}' using '{tool_body_name}'. "
            f"'{tool_body_name}' has been consumed."
        )
    except Exception as e:
        logger.error(f"Boolean_operation failed: {e}")
        return (
            f"Error performing Boolean {operation} on '{target_body_name}' "
            f"with '{tool_body_name}': {e}"
        )
