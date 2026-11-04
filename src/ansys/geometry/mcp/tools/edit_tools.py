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
from ansys.geometry.mcp.misc.auxiliary import (
    find_bodies_by_id,
    get_geometry_ctx,
    serialize_design_access,
)

logger = get_logger(__name__)


@app.tool()
@serialize_design_access
def boolean_operation(
    ctx: Context,
    operation: Literal["subtract", "unite", "intersect"],
    target_body_id: str,
    tool_body_id: str,
) -> str:
    """Perform a Boolean subtract, union, or intersection on two bodies.

    The target body survives the operation and the tool body is consumed.

    - For ``subtract``, the tool body's volume is removed from the target.
    - For ``unite``, the tool is merged into the target.
    - For ``intersect``, the target is reduced to the volume common to both bodies.

    Bodies are addressed by ID. Look up each body named by the user with
    ``list_entities(entity_type="body", name=...)`` first.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    operation : Literal["subtract", "unite", "intersect"]
        Boolean operation to perform.
    target_body_id : str
        ID of the body to modify (survives the operation).
    tool_body_id : str
        ID of the body used in the operation (consumed afterward).

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
        found, missing = find_bodies_by_id(design, [target_body_id])
        if missing:
            return (
                f"Target body ID '{target_body_id}' not found. "
                "Use list_entities to see available bodies."
            )
        target = found[0]
        found, missing = find_bodies_by_id(design, [tool_body_id])
        if missing:
            return (
                f"Tool body ID '{tool_body_id}' not found. "
                "Use list_entities to see available bodies."
            )
        tool = found[0]
        target_label = f"'{target.name}' (id={target_body_id})"
        tool_label = f"'{tool.name}' (id={tool_body_id})"
        operation_methods = {
            "subtract": target.subtract,
            "unite": target.unite,
            "intersect": target.intersect,
        }
        operation_methods[operation](tool)

        app_context.command_history.append(
            "from ansys.geometry.core.misc.auxiliary import get_bodies_from_ids"
        )
        app_context.command_history.append(
            f"target = get_bodies_from_ids(design, [{target_body_id!r}])[0]"
        )
        app_context.command_history.append(
            f"tool = get_bodies_from_ids(design, [{tool_body_id!r}])[0]"
        )
        app_context.command_history.append(f"target.{operation}(tool)")

        logger.info(
            f"boolean_operation: operation={operation!r}, target={target_body_id!r}, "
            f"tool={tool_body_id!r}"
        )
        return (
            f"Boolean {operation} complete for {target_label} using {tool_label}. "
            f"{tool_label} has been consumed."
        )
    except Exception as e:
        logger.error(f"Boolean_operation failed: {e}")
        return (
            f"Error performing boolean {operation} on '{target_body_id}' with '{tool_body_id}': {e}"
        )
