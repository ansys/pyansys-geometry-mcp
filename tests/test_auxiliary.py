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

"""Unit tests for the shared auxiliary helpers."""

import inspect
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ansys.geometry.mcp.misc.auxiliary import (
    build_sketch,
    resolve_bodies,
    serialize_design_access,
)


def test_build_sketch_primitives():
    """Test all build_sketch branches.

    Cover default and custom planes, every primitive type, and invalid types.
    """
    sketch, _ = build_sketch(
        [
            {"type": "circle", "center_x": 0.0, "center_y": 0.0, "radius": 1.0},
            {"type": "box", "center_x": 0.0, "center_y": 0.0, "width": 2.0, "height": 2.0},
            {"type": "polygon", "center_x": 0.0, "center_y": 0.0, "inner_radius": 0.5, "sides": 6},
            {"type": "segment", "start_x": 0.0, "start_y": 0.0, "end_x": 1.0, "end_y": 0.0},
            {
                "type": "arc",
                "center_x": 0.5,
                "center_y": 0.0,
                "start_x": 0.0,
                "start_y": 0.0,
                "end_x": 1.0,
                "end_y": 0.0,
            },
        ]
    )
    assert sketch is not None

    sketch2, _ = build_sketch(
        [{"type": "circle", "center_x": 0.0, "center_y": 0.0, "radius": 1.0}],
        plane_origin=[0.0, 0.0, 1.0],
        plane_dir_x=[1.0, 0.0, 0.0],
        plane_dir_y=[0.0, 1.0, 0.0],
    )
    assert sketch2 is not None

    with pytest.raises(ValueError, match="Unsupported sketch primitive type"):
        build_sketch([{"type": "triangle"}])


def test_resolve_bodies_scoping(design):
    """Test the resolution precedence: handle, then named selection, then IDs, then all."""
    app_context = MagicMock()
    app_context.command_history = []
    app_context.selection_registry = {
        "sel-1": SimpleNamespace(_bodies=SimpleNamespace(items=[design.get_all_bodies()[1]])),
        "sel-empty": SimpleNamespace(_bodies=SimpleNamespace(items=[])),
    }

    bodies, error = resolve_bodies(app_context, design)
    assert error is None
    assert [b.name for b in bodies] == ["box", "cylinder"]
    assert app_context.command_history[-1] == "bodies = design.get_all_bodies()"

    bodies, error = resolve_bodies(app_context, design, body_ids=["0:2"])
    assert error is None
    assert [b.name for b in bodies] == ["cylinder"]
    assert app_context.command_history[-1].endswith("bodies = get_bodies_from_ids(design, ['0:2'])")

    bodies, error = resolve_bodies(app_context, design, named_selection="hot_side")
    assert error is None
    assert [b.name for b in bodies] == ["box"]
    assert "ns.name == 'hot_side'" in app_context.command_history[-1]

    bodies, error = resolve_bodies(app_context, design, selection_handle="sel-1")
    assert error is None
    assert [b.name for b in bodies] == ["cylinder"]
    assert app_context.command_history[-1] == (
        "bodies = list(selection_registry['sel-1']._bodies.items)"
    )

    # A handle wins over the other scoping arguments.
    bodies, error = resolve_bodies(
        app_context,
        design,
        body_ids=["0:1"],
        named_selection="hot_side",
        selection_handle="sel-1",
    )
    assert error is None
    assert [b.name for b in bodies] == ["cylinder"]


def test_resolve_bodies_errors(design):
    """Test every error path returns an empty body list and an explanatory message."""
    app_context = MagicMock()
    app_context.command_history = []
    app_context.selection_registry = {
        "sel-empty": SimpleNamespace(_bodies=SimpleNamespace(items=[])),
    }

    bodies, error = resolve_bodies(app_context, design, selection_handle="nope")
    assert bodies == []
    assert "Invalid selection handle" in error

    bodies, error = resolve_bodies(app_context, design, selection_handle="sel-empty")
    assert bodies == []
    assert "no bodies selected" in error

    bodies, error = resolve_bodies(app_context, design, named_selection="missing")
    assert bodies == []
    assert "hot_side" in error

    bodies, error = resolve_bodies(app_context, design, named_selection="empty_group")
    assert bodies == []
    assert "contains no bodies" in error

    bodies, error = resolve_bodies(app_context, design, body_ids=["0:1", "ghost"])
    assert bodies == []
    assert "ghost" in error
    assert "0:1" not in error

    empty_design = SimpleNamespace(get_all_bodies=lambda: [], named_selections=[])
    bodies, error = resolve_bodies(app_context, empty_design)
    assert bodies == []
    assert "no bodies" in error
    assert app_context.command_history == []


def test_serialize_design_access_runs_calls_one_at_a_time():
    """Test that concurrent calls never overlap, so in-place design syncs cannot interleave."""
    active = 0
    peak = 0
    counter_lock = threading.Lock()

    @serialize_design_access
    def tool(value: int) -> int:
        nonlocal active, peak
        with counter_lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.02)
        with counter_lock:
            active -= 1
        return value * 2

    results = [None] * 5

    def call(i: int) -> None:
        results[i] = tool(i)

    threads = [threading.Thread(target=call, args=(i,)) for i in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert peak == 1
    assert results == [0, 2, 4, 6, 8]


def test_serialize_design_access_is_reentrant_and_preserves_metadata():
    """Test that nested decorated calls do not deadlock and tool metadata is kept."""

    @serialize_design_access
    def inner() -> str:
        """Inner docstring."""
        return "inner"

    @serialize_design_access
    def outer(ctx: object, name: str = "x") -> str:
        """Outer docstring."""
        return inner() + name

    assert outer(None) == "innerx"
    assert outer.__doc__ == "Outer docstring."
    assert list(inspect.signature(outer).parameters) == ["ctx", "name"]


async def test_serialized_tools_keep_their_mcp_schema():
    """Test that decorated tools still register with their parameters and hide ``ctx``."""
    from ansys.geometry.mcp import app
    import ansys.geometry.mcp.tools  # noqa: F401

    tools = {tool.name: tool for tool in await app.list_tools()}
    properties = tools["list_entities"].parameters["properties"]
    assert "ctx" not in properties
    assert {"entity_type", "body_id", "component_id", "name"} <= set(properties)
    assert "discovery tool" in tools["list_entities"].description
