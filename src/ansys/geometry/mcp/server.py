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

"""MCP server for PyAnsys Geometry MCP."""

from ansys.common.mcp import PersistentPythonSession, PyAnsysBaseMCP
from ansys.common.mcp.logging_config import get_logger

from ansys.geometry.mcp.context import PyAnsysGeometryContext

logger = get_logger(__name__)


class PyAnsysGeometryMCP(PyAnsysBaseMCP):
    """MCP server for PyAnsys Geometry MCP.

    This server enables AI assistants to interact with
    ``ansys-geometry-core`` for simulation and analysis workflows.
    """

    def create_context(self) -> PyAnsysGeometryContext:
        """Create product-specific context.

        Returns
        -------
        PyAnsysGeometryContext
            Context instance with Python session and command history.
        """
        return PyAnsysGeometryContext(
            python_session=PersistentPythonSession(
                python_executable=self.python_executable,
                working_directory=self.working_directory,
            ),
            command_history=[],
        )

    def product_startup(self):
        """Launch the product instance when the server starts.

        This method is called automatically during server startup.

        Notes
        -----
        TODO: Replace the placeholder below with code that launches or
        connects to your product. Store the instance on ``self.context``
        so that tools can access it.

        If your product takes time to start (for example, it requires a
        Docker container or a license check), consider launching it in a
        background thread so the MCP handshake can complete immediately.

        Example (synchronous)::

            from my_product import launch_product
            self.context.product_instance = launch_product()

        Example (background thread)::

            import threading

            def _launch():
                from my_product import launch_product
                self.context.product_instance = launch_product()

            t = threading.Thread(target=_launch, daemon=True)
            t.start()
            # Do NOT join — return immediately so the MCP handshake completes.
        """
        logger.info("Starting PyAnsys Geometry MCP backend...")

        # TODO: Implement product startup.
        # Example:
        # from my_product import launch_product
        # self.context.product_instance = launch_product()

        logger.warning(
            "product_startup() is not implemented yet. "
            "Edit server.py to launch your product."
        )

    def product_cleanup(self):
        """Clean up the product instance when the server stops.

        This method is called automatically during server shutdown.

        Notes
        -----
        TODO: Replace the placeholder below with code that gracefully
        shuts down or disconnects from your product.

        Example::

            if self.context.product_instance is not None:
                self.context.product_instance.exit()
        """
        if self.context.product_instance is not None:
            try:
                logger.info("Closing PyAnsys Geometry MCP backend...")
                # TODO: Call the appropriate shutdown method on your product.
                # Example: self.context.product_instance.exit()
                logger.info("PyAnsys Geometry MCP backend closed successfully.")
            except Exception as e:
                logger.error(f"Error during product cleanup: {e}")


# Create the MCP server instance used by tools.py and __main__.py
app = PyAnsysGeometryMCP(
    name="pyansys-geometry-mcp",
)
