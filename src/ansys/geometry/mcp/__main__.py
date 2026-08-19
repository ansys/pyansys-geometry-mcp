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

"""Entry point for running the PyAnsys Geometry MCP server."""

import argparse
import sys

from ansys.common.mcp.logging_config import setup_logging

from ansys.geometry.mcp import app

# Import tools module to register all @app.tool() decorators with the server.
import ansys.geometry.mcp.selection  # noqa: F401
import ansys.geometry.mcp.tools  # noqa: F401


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyansys-geometry-mcp",
        description="PyAnsys Geometry MCP server",
    )
    parser.add_argument(
        "--mode",
        default=None,
        choices=["pypim", "docker", "geometry_service", "spaceclaim", "discovery"],
        help=(
            "Launch mode for the geometry service (default: auto-detect). "
            "Options are 'pypim' (remote via PIM API), 'docker' (local Docker), "
            "'geometry_service' (local Ansys Geometry Service), "
            "'spaceclaim' (local Ansys SpaceClaim), and 'discovery' (local Ansys Discovery)."
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
    app.context.host = args.host
    app.context.port = args.port
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
