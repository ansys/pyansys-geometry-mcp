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

"""Entry point for running the PyAnsys Geometry MCP server."""

import argparse
import sys

from ansys.common.mcp.logging_config import setup_logging

from ansys.geometry.mcp import app

# Import tools module to register all @app.tool() decorators with the server.
import ansys.geometry.mcp.tools  # noqa: F401


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyansys-geometry-mcp",
        description="PyAnsys Geometry MCP server",
    )
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
            "Options are 'insecure' (plaintext TCP), 'mtls' (mutual TLS), 'wnua' (Windows Named User Authentication), "
            "and 'uds' (Unix Domain Sockets)."
        ),
    )
    parser.add_argument(
        "--proto-version",
        default="v1",
        choices=["v0", "v1"],
        help="Protocol version for an existing geometry service (default: v1).",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host name or IP address of the geometry service (default: localhost).",
    )
    parser.add_argument(
        "--port",
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
            "Connect to an already-running geometry service instead of launching a new one. "
            "Requires --host and --port to point at the running service."
        ),
    )
    parser.add_argument(
        "--mcp-transport",
        default="stdio",
        choices=["stdio", "http", "streamable-http", "sse"],
        help="Transport for the MCP server (default: stdio).",
    )
    parser.add_argument(
        "--mcp-host",
        default="127.0.0.1",
        help="Host address for the MCP HTTP server (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=62000,
        help="Port for the MCP HTTP server (default: 62000).",
    )
    parser.add_argument(
        "--mcp-path",
        default="/mcp",
        help="Path for the MCP HTTP endpoint (default: /mcp).",
    )
    return parser


def main():
    """Run the PyAnsys Geometry MCP MCP server."""
    parser = _build_parser()
    args = parser.parse_args()

    # Pre-create the context and apply CLI configuration before the server
    # starts, so product_startup() picks up the correct values.
    app.context = app.create_context()
    app.context.mode = args.mode
    app.context.transport_mode = args.transport_mode
    app.context.proto_version = args.proto_version
    app.context.host = args.host
    app.context.port = args.port
    app.context.uds_dir = args.uds_dir
    app.context.uds_id = args.uds_id
    app.context.connect_to_existing_service = args.connect_to_existing_service

    setup_logging(level="INFO")
    try:
        if args.mcp_transport == "stdio":
            app.run(transport="stdio")
        else:
            app.run(
                transport=args.mcp_transport,
                host=args.mcp_host,
                port=args.mcp_port,
                path=args.mcp_path,
            )
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
