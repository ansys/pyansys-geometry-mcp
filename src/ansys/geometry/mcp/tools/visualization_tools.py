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

"""MCP visualization tools for PyAnsys Geometry MCP server.

Tools that render the active design or read the resulting images.

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

import time

from ansys.common.mcp.logging_config import get_logger
from fastmcp.server import Context

from ansys.geometry.mcp import app
from ansys.geometry.mcp.misc.auxiliary import get_geometry_ctx

logger = get_logger(__name__)


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
def visualize(
    ctx: Context,
    path: str | None = None,
    save: bool = False,
    use_service_colors: bool = False,
) -> str:
    """Open a 3D view of the active design or save an image when requested.

    Service colors are disabled by default. Enable them when the design's colors
    convey essential information or the user requests a full-color plot.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    path : str, optional
        Path to save the image. Providing a path saves the image there.
    save : bool, optional
        Save an image using a timestamped filename if no path is provided. Default False.
    use_service_colors : bool, optional
        Plot using service colors. Default False. Enable when colors are essential
        or a full-color plot is requested.

    Returns
    -------
    str
        Result message, or an error message if the operation fails.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot visualize the design."

    try:
        design = app_context.product_instance.get_active_design()
        if path or save:
            screenshot_path = path or f"design_3d_scene_{int(time.time())}.png"
            _ = design.plot(screenshot=screenshot_path, use_service_colors=use_service_colors)
            app_context.command_history.append(
                f"design.plot(screenshot={screenshot_path!r}, "
                f"use_service_colors={use_service_colors})"
            )
            logger.info(f"visualize called, saved image to {screenshot_path}")
            return f"3D scene image saved: {screenshot_path}"

        _ = design.plot(use_service_colors=use_service_colors)
        app_context.command_history.append(f"design.plot(use_service_colors={use_service_colors})")
        logger.info("visualize called, opened 3D scene window")
        return "3D scene window opened."
    except Exception as e:
        logger.error(f"visualize failed: {e}")
        return f"Error visualizing design: {e}"
