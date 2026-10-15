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

"""Unit tests for the MCP server."""

import io
import logging

import pytest

from ansys.geometry.mcp.context import PyAnsysGeometryContext
from ansys.geometry.mcp.server import PyAnsysGeometryMCP


@pytest.fixture
def preserve_root_logging():
    """Restore root logger handlers and level after tests that configure logging."""
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level
    yield

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        if handler not in original_handlers:
            handler.close()
    for handler in original_handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(original_level)


def test_create_context_configures_file_logging(tmp_path, preserve_root_logging):
    """CLI logging options configure the root logger and write messages to a file."""
    server = PyAnsysGeometryMCP()
    log_file = tmp_path / "server.log"
    server._cli_config = {"log_level": "DEBUG", "log_file": str(log_file)}

    context = server.create_context()
    logging.getLogger("test.server").debug("file logging works")
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert context.log_level == "DEBUG"
    assert context.log_file == str(log_file)
    assert logging.getLogger().level == logging.DEBUG
    assert "file logging works" in log_file.read_text(encoding="utf-8")


def test_create_context_preserves_existing_logging(preserve_root_logging):
    """Returning an existing context does not replace host-configured handlers."""
    server = PyAnsysGeometryMCP()
    context = PyAnsysGeometryContext(log_level="DEBUG", log_file="server.log")
    server.context = context
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    handler = logging.StreamHandler(io.StringIO())
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.WARNING)

    assert server.create_context() is context
    assert root_logger.handlers == [handler]
    assert root_logger.level == logging.WARNING
