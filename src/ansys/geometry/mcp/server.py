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

"""MCP server for PyAnsys Geometry MCP."""

from ansys.common.mcp import PersistentPythonSession, PyAnsysBaseMCP
from ansys.common.mcp.logging_config import get_logger
import ansys.common.mcp.tools as shared_tools

from ansys.geometry.mcp.context import PyAnsysGeometryContext

logger = get_logger(__name__)


class PyAnsysGeometryMCP(PyAnsysBaseMCP):
    """MCP server for PyAnsys Geometry MCP.

    This server enables AI assistants to interact with
    ``ansys-geometry-core`` for simulation and analysis workflows.
    """

    context: PyAnsysGeometryContext
    """The application context for the MCP server, containing the product instance and related information."""

    def create_context(self) -> PyAnsysGeometryContext:
        """Create (or return the pre-existing) product-specific context.

        If the context has already been initialised — for example because
        CLI arguments were written to ``app.context`` before ``app.run()``
        was called — this method returns it unchanged so that caller-set
        configuration is preserved.

        Returns
        -------
        PyAnsysGeometryContext
            Context instance with Python session and command history.


        """
        if getattr(self, "context", None) is not None:
            return self.context

        setup_commands = ["selection_registry = {}"]

        return PyAnsysGeometryContext(
            python_session=PersistentPythonSession(
                python_executable=self.python_executable, working_directory=self.working_directory
            ),
            command_history=setup_commands,
        )

    def product_startup(self):
        """Launch the product instance when the server starts.

        This method is called automatically during server startup.
        """
        self.context.product_instance = None
        logger.info("Starting PyAnsys Geometry MCP backend...")

        if self.context.connect_to_existing_service:
            from ansys.geometry.core import Modeler

            logger.info(
                f"Connecting to existing geometry service at "
                f"{self.context.host}:{self.context.port}..."
            )
            instance = Modeler(
                host=self.context.host,
                port=self.context.port,
                transport_mode=self.context.transport_mode,
                proto_version=self.context.proto_version,
            )

            # creates the background instance of the modeler to be used when running python scripts in the interpreter
            host, port = (
                instance.client.get_name().split(":")
                if instance.client
                else (self.context.host, str(self.context.port))
            )
            self.context.host = host
            self.context.port = int(port)
            background_python_instance_creation = f"""
from ansys.geometry.core import Modeler

instance = Modeler(
    host='{host}',
    port={port},
    transport_mode='{self.context.transport_mode}',
    proto_version={self.context.proto_version!r})
"""
            self.context.python_session.execute(background_python_instance_creation)

            self.context.command_history.append("from ansys.geometry.core import Modeler")
            self.context.command_history.append(
                f"instance=Modeler(host={self.context.host!r}, port={self.context.port}, "
                f"transport_mode={self.context.transport_mode!r}, "
                f"proto_version={self.context.proto_version!r})"
            )
        else:
            from ansys.geometry.core import launch_modeler

            instance = launch_modeler(
                mode=self.context.mode,
                transport_mode=self.context.transport_mode,
            )
            self.context.command_history.append("from ansys.geometry.core import launch_modeler")
            self.context.command_history.append(
                f"instance=launch_modeler(mode={self.context.mode!r}, "
                f"transport_mode={self.context.transport_mode!r})"
            )

            # Mirror instance into the persistent Python session so that
            # run_python_code() can reference it via the 'instance' variable.
            host, port = (
                instance.client.get_name().split(":")
                if instance.client
                else (self.context.host, str(self.context.port))
            )
            self.context.host = host
            self.context.port = int(port)
            background_python_instance_creation = f"""
from ansys.geometry.core import Modeler

instance = Modeler(
    host='{host}',
    port={port},
    transport_mode='{self.context.transport_mode}')
"""
            self.context.python_session.execute(background_python_instance_creation)

        self.context.product_instance = instance
        # Log the successful launch of the product instance
        logger.info("PyAnsys Geometry MCP backend launched successfully.")
        logger.info(f"Product instance details:\n\n{self.context.product_instance}")

    def product_cleanup(self):
        """Clean up the product instance when the server stops.

        This method is called automatically during server shutdown.
        """
        if self.context.product_instance is not None:
            try:
                logger.info("Closing PyAnsys Geometry MCP backend...")
                self.context.product_instance.close()
                self.context.command_history.append("instance.close()")
                logger.info("PyAnsys Geometry MCP backend closed successfully.")
            except Exception as e:
                logger.error(f"Error during product cleanup: {e}")


# Create the MCP server instance used by tools.py and __main__.py.
# CLI arguments set in __main__.py are applied to this instance before app.run().
app = PyAnsysGeometryMCP(
    name="pyansys-geometry-mcp",
)