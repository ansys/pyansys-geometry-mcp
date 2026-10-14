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

import argparse

from ansys.common.mcp import PersistentPythonSession, PyAnsysBaseMCP
from ansys.common.mcp.logging_config import get_logger, setup_logging

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

        cli_config = self._cli_config
        setup_logging(
            level=cli_config.get("log_level", "INFO"),
            log_file=cli_config.get("log_file"),
        )
        setup_commands = ["selection_registry = {}"]

        return PyAnsysGeometryContext(
            python_session=PersistentPythonSession(
                python_executable=self.python_executable, working_directory=self.working_directory
            ),
            command_history=setup_commands,
            mode=cli_config.get("mode"),
            transport_mode=cli_config.get("transport_mode"),
            proto_version=cli_config.get("proto_version", "v1"),
            geometry_host=cli_config.get("geometry_host", "localhost"),
            geometry_port=cli_config.get("geometry_port", 50051),
            uds_dir=cli_config.get("uds_dir"),
            uds_id=cli_config.get("uds_id"),
            connect_to_existing_service=cli_config.get("connect_to_existing_service", False),
            log_level=cli_config.get("log_level", "INFO"),
            log_file=cli_config.get("log_file"),
        )

    def _add_cli_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add geometry-service CLI arguments on top of the common transport ones."""
        parser.add_argument(
            "--mode",
            default=None,
            choices=[
                "docker",
                "core_service",
                "geometry_service",
                "discovery",
            ],
            help=(
                "Launch mode for the geometry service (default: auto-detect). "
                "'docker' (local Docker), "
                "'core_service' (local Ansys Geometry Core Service), "
                "'geometry_service' (local Ansys Geometry Service), "
                "'discovery' (local Ansys Discovery)."
            ),
        )
        parser.add_argument(
            "--transport-mode",
            default=None,
            choices=["insecure", "mtls", "wnua", "uds"],
            help=(
                "Transport mode for the geometry service connection (default: insecure). "
                "Options are 'insecure' (plaintext TCP), 'mtls' (mutual TLS), "
                "'wnua' (Windows Named User Authentication), and 'uds' (Unix Domain Sockets)."
            ),
        )
        parser.add_argument(
            "--proto-version",
            default="v1",
            choices=["v0", "v1"],
            help="Protocol version for an existing geometry service (default: v1).",
        )
        parser.add_argument(
            "--geometry-host",
            dest="geometry_host",
            default="localhost",
            help="Host name or IP address of the geometry service (default: localhost).",
        )
        parser.add_argument(
            "--geometry-port",
            dest="geometry_port",
            type=int,
            default=50051,
            help="Port number of the geometry service (default: 50051).",
        )
        parser.add_argument(
            "--uds-dir",
            default=None,
            help="Directory for the UDS socket (default: None).",
        )
        parser.add_argument(
            "--uds-id",
            default=None,
            help="Optional UDS socket identifier (default: None).",
        )
        parser.add_argument(
            "--connect-to-existing-service",
            action="store_true",
            default=False,
            help=(
                "Connect to an already-running geometry service instead of launching a new "
                "one. Requires --geometry-host and --geometry-port to point at the running "
                "service."
            ),
        )
        parser.add_argument(
            "--log-level",
            default="INFO",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Log level for the geometry service (default: INFO).",
        )
        parser.add_argument(
            "--log-file",
            default=None,
            help="Log file for the geometry service (default: None).",
        )

    def _configure_from_cli(self, args: argparse.Namespace) -> None:
        """Stash the parsed geometry-service arguments for create_context to read."""
        self._cli_config = {
            "mode": args.mode,
            "transport_mode": args.transport_mode,
            "proto_version": args.proto_version,
            "geometry_host": args.geometry_host,
            "geometry_port": args.geometry_port,
            "uds_dir": args.uds_dir,
            "uds_id": args.uds_id,
            "connect_to_existing_service": args.connect_to_existing_service,
            "log_level": args.log_level,
            "log_file": args.log_file,
        }

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
                f"{self.context.geometry_host}:{self.context.geometry_port}..."
            )
            instance = Modeler(
                host=self.context.geometry_host,
                port=self.context.geometry_port,
                transport_mode=self.context.transport_mode,
                proto_version=self.context.proto_version,
                uds_dir=self.context.uds_dir,
                uds_id=self.context.uds_id,
            )

            self.context.geometry_host = instance.client.host
            self.context.geometry_port = instance.client.port

            self.context.command_history.append("from ansys.geometry.core import Modeler")
            self.context.command_history.append(
                f"instance=Modeler(host={self.context.geometry_host!r}, "
                f"port={self.context.geometry_port}, "
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

            self.context.geometry_host = instance.client.host
            self.context.geometry_port = instance.client.port

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
