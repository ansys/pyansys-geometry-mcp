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

import threading

from ansys.common.mcp import PersistentPythonSession, PyAnsysBaseMCP
from ansys.common.mcp.logging_config import get_logger

from ansys.geometry.mcp.context import PyAnsysGeometryContext

logger = get_logger(__name__)


class PyAnsysGeometryMCP(PyAnsysBaseMCP):
    """MCP server for PyAnsys Geometry MCP.

    This server enables AI assistants to interact with
    ``ansys-geometry-core`` for simulation and analysis workflows.
    """

    _product_thread: threading.Thread | None = None
    """Private attribute to hold the reference to the product launch thread."""

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
        """
        self.context.product_instance = None
        logger.info("Starting PyAnsys Geometry MCP backend...")

        def _launch():
            from ansys.geometry.core import launch_modeler

            instance = launch_modeler(transport_mode="insecure")
            self.context.product_instance = instance
            # Log the successful launch of the product instance
            logger.info("PyAnsys Geometry MCP backend launched successfully.")
            logger.info(f"Product instance details:\n\n{self.context.product_instance}")

        # Launch the product in a separate thread to avoid blocking the server startup
        t = threading.Thread(target=_launch, daemon=True)
        t.start()

        # Store the thread reference to ensure it stays alive and can be joined if needed
        self._product_thread = t

    def product_cleanup(self):
        """Clean up the product instance when the server stops.

        This method is called automatically during server shutdown.
        """
        if self.context.product_instance is not None:
            try:
                logger.info("Closing PyAnsys Geometry MCP backend...")
                self.context.product_instance.close()
                logger.info("PyAnsys Geometry MCP backend closed successfully.")
            except Exception as e:
                logger.error(f"Error during product cleanup: {e}")

        # Close the threaded product launch if it's still running to ensure clean shutdown
        if self._product_thread is not None and self._product_thread.is_alive():
            logger.info("Waiting for product launch thread to finish...")
            self._product_thread.join(timeout=5)
            if self._product_thread.is_alive():
                logger.warning("Product launch thread did not finish within timeout.")


# Create the MCP server instance used by tools.py and __main__.py
app = PyAnsysGeometryMCP(
    name="pyansys-geometry-mcp",
)
