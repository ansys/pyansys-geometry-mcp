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

        connection_code = f"""
# Connect to the persistent Modeler instance
from ansys.geometry.core import Modeler  # pyright: ignore[reportMissingTypeStubs]

modeler = Modeler(
    host='{modeler_instance.client.ip}',
    port={modeler_instance.client.port},
)
        """
        session.execute(connection_code)

        # Store in persistent session
        session.metadata["instance"] = modeler_instance

        logger.info(
            "Connected to persistent PyAnsys Geometry session successfully at"
            f" {modeler_instance.client.ip}:{modeler_instance.client.port}!"
        )

    except Exception as e:
        error_msg = (
            f"Failed to connect to Modeler in the persistent PyAnsys Geometry session: {str(e)}"
        )
        logger.error(error_msg)

    return session.metadata.get("instance", None)
