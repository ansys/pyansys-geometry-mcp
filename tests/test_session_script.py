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

"""Backend-independent tests for session script generation."""

from unittest.mock import MagicMock

import pytest

from ansys.geometry.mcp import app
from ansys.geometry.mcp.tools import get_session_script


def test_session_script_replay():
    """Sort imports and preserve replayed commands without changing history."""
    ctx = MagicMock()
    history = [
        "selection_registry = {}",
        "events = []",
        "events.append('before import')",
        "from math import sqrt, ceil",
        "events.append(sqrt(4))",
    ]
    ctx.fastmcp._lifespan_result.command_history = history.copy()

    script = get_session_script(ctx)
    namespace = {}
    exec(compile(script, "session_script.py", "exec"), namespace)

    assert namespace["events"] == ["before import", 2.0]
    assert namespace["selection_registry"] == {}
    assert "from math import ceil, sqrt" in script
    assert script.index('events.append("before import")') < script.index(
        "from math import ceil, sqrt"
    )
    assert ctx.fastmcp._lifespan_result.command_history == history


def test_session_script_empty():
    """Return valid empty Python source for an empty history."""
    ctx = MagicMock()
    ctx.fastmcp._lifespan_result.command_history = []
    assert get_session_script(ctx) == ""


def test_session_script_invalid():
    """Reject history containing invalid Python rather than return a broken script."""
    ctx = MagicMock()
    ctx.fastmcp._lifespan_result.command_history = ["if"]
    with pytest.raises(ValueError, match="not valid Python"):
        get_session_script(ctx)


async def test_session_script_registration():
    """Expose only the consolidated session script tool."""
    tool_names = {tool.name for tool in await app.list_tools()}
    assert "get_session_script" in tool_names
    assert "get_command_history" not in tool_names
    assert "get_transcript" not in tool_names
