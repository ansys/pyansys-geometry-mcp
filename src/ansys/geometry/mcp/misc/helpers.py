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

"""Helper functions for PyAnsys Geometry MCP."""

from typing import TYPE_CHECKING, Any

from ansys.common.mcp.helpers import logger
from fastmcp.server import Context

from ansys.geometry.mcp.misc.auxiliary import get_geometry_ctx

if TYPE_CHECKING:
    from ansys.geometry.core import Modeler


def connect_to_modeler_in_persistent_python(
    ctx: Context,
) -> Any:
    """Connect to the Modeler instance in the persistent Python session.

    This tool connects to the Modeler instance from within the persistent Python session.
    It assumes that the persistent session has already been created.


    Parameters
    ----------
    ctx : Context
        The MCP context containing server session and application context.

    Returns
    -------
    str
        Connection status message.

    """
    if ctx.request_context is None:
        return "No request context available."

    app_context = get_geometry_ctx(ctx)
    session = ctx.request_context.lifespan_context.python_session
    if session is None:
        return "No Python session available. The persistent Python session was not initialized."

    try:
        # Check if already connected
        if session.metadata.get("instance", None) is not None:
            instance = session.metadata["instance"]
            return (
                f"Already connected to persistent PyAnsys Geometry session with Modeler at "
                f"{instance.client.host}:{instance.client.port}."
            )

        # First, check if Modeler is available in lifespan context
        modeler_instance = ctx.request_context.lifespan_context.product_instance
        if modeler_instance is None:
            return "No Modeler instance available in lifespan context."

        # The session is a separate process, so it needs its own client to the same service.
        connection_code = (
            "from ansys.geometry.core import Modeler\n"
            f"instance = Modeler(host={modeler_instance.client.host!r}, "
            f"port={modeler_instance.client.port!r}, "
            f"transport_mode={app_context.transport_mode!r})\n"
            "design = None\n"
        )
        session.execute(connection_code)

        # Store in persistent session
        session.metadata["instance"] = modeler_instance

        logger.info(
            "Connected to persistent PyAnsys Geometry session successfully at"
            f" {modeler_instance.client.host}:{modeler_instance.client.port}!"
        )

        refresh_design_in_persistent_python(ctx)

    except Exception as e:
        error_msg = (
            f"Failed to connect to Modeler in the persistent PyAnsys Geometry session: {str(e)}"
        )
        logger.error(error_msg)

    return session.metadata.get("instance", None)


def refresh_design_in_persistent_python(ctx: Context) -> None:
    """Rebind ``design`` in the persistent Python session to the active design.

    The persistent session runs in its own process with its own ``Modeler`` client,
    so the design it holds has to be re-read whenever the active design changes.
    Does nothing when the session is not connected yet; the connection step
    refreshes the design itself.

    Parameters
    ----------
    ctx : Context
        The MCP context containing server session and application context.

    """
    if ctx.request_context is None:
        return

    session = ctx.request_context.lifespan_context.python_session
    if session is None or session.metadata.get("instance", None) is None:
        return

    result = session.execute("design = instance.read_existing_design()")
    if isinstance(result, dict) and not result.get("success"):
        logger.warning(
            "Failed to refresh 'design' in the persistent PyAnsys Geometry session: "
            f"{result.get('error')}"
        )
