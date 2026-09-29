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

    context: PyAnsysGeometryContext
    """The application context for the MCP server, containing the product instance and related information."""

    def __init__(self, name: str = "pyansys-geometry-mcp", *args, **kwargs):
        """Initialize the PyAnsys Geometry MCP server."""
        super().__init__(name=name, *args, **kwargs)

    def create_context(self) -> PyAnsysGeometryContext:
        """Create (or return the pre-existing) product-specific context.

        If the context has already been initialised — for example because
        CLI arguments were written to ``app.context`` before ``app.run()``
        was called — this method returns it unchanged so that caller-set
        configuration is preserved.

        Returns
        -------
        PyAnsysGeometryContext
            Context instance with command history.


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
                uds_dir=self.context.uds_dir,
                uds_id=self.context.uds_id,
            )

            self.context.host = instance.client.host
            self.context.port = instance.client.port

            self.context.command_history.append("from ansys.geometry.core import Modeler")
            self.context.command_history.append(
                f"instance=Modeler(host={self.context.host!r}, port={self.context.port}, "
                f"transport_mode={self.context.transport_mode!r}, "
                f"proto_version={self.context.proto_version!r}, "
                f"uds_dir={self.context.uds_dir!r}, "
                f"uds_id={self.context.uds_id!r})"
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
                f"transport_mode={self.context.transport_mode!r}, "
                f"uds_dir={self.context.uds_dir!r}, "
                f"uds_id={self.context.uds_id!r})"
            )

            self.context.host = instance.client.host
            self.context.port = instance.client.port

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


# Create the MCP server instance used by tools and __main__.py.
# CLI arguments set in __main__.py are applied to this instance before app.run().
app = PyAnsysGeometryMCP(
    name="pyansys-geometry-mcp",
)
