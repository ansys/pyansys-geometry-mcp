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

"""Entry point for running the PyAnsys Geometry MCP server."""

import argparse
import sys

# Import tools module to register all @app.tool() decorators with the server.
import ansys.geometry.mcp.tools  # noqa: F401
from ansys.geometry.mcp import app

from ansys.common.mcp.logging_config import setup_logging


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyansys-geometry-mcp",
        description="PyAnsys Geometry MCP server",
    )
    parser.add_argument(
        "--transport-mode",
        default="insecure",
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
    return parser


def main():
    """Run the PyAnsys Geometry MCP MCP server."""
    parser = _build_parser()
    args = parser.parse_args()

    # Pre-create the context and apply CLI configuration before the server
    # starts, so product_startup() picks up the correct values.
    app.context = app.create_context()
    app.context.transport_mode = args.transport_mode
    app.context.host = args.host
    app.context.port = args.port
    app.context.connect_to_existing_service = args.connect_to_existing_service

    setup_logging(level="INFO")
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
