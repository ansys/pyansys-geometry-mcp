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

"""Unit tests for the shared auxiliary helpers."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ansys.geometry.mcp.misc.auxiliary import build_sketch, resolve_bodies


def test_build_sketch_primitives():
    """Test all build_sketch branches: default plane, custom plane, every primitive type, and invalid type."""
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
    """Test the resolution precedence: handle, then named selection, then names, then all."""
    app_context = MagicMock()
    app_context.selection_registry = {
        "sel-1": SimpleNamespace(_bodies=SimpleNamespace(items=[design.get_all_bodies()[1]])),
        "sel-empty": SimpleNamespace(_bodies=SimpleNamespace(items=[])),
    }

    bodies, error = resolve_bodies(app_context, design)
    assert error is None
    assert [b.name for b in bodies] == ["box", "cylinder"]

    bodies, error = resolve_bodies(app_context, design, body_names=["cylinder"])
    assert error is None
    assert [b.name for b in bodies] == ["cylinder"]

    bodies, error = resolve_bodies(app_context, design, named_selection="hot_side")
    assert error is None
    assert [b.name for b in bodies] == ["box"]

    bodies, error = resolve_bodies(app_context, design, selection_handle="sel-1")
    assert error is None
    assert [b.name for b in bodies] == ["cylinder"]

    # A handle wins over the other scoping arguments.
    bodies, error = resolve_bodies(
        app_context,
        design,
        body_names=["box"],
        named_selection="hot_side",
        selection_handle="sel-1",
    )
    assert error is None
    assert [b.name for b in bodies] == ["cylinder"]


def test_resolve_bodies_errors(design):
    """Test every error path returns an empty body list and an explanatory message."""
    app_context = MagicMock()
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

    bodies, error = resolve_bodies(app_context, design, body_names=["box", "ghost"])
    assert bodies == []
    assert "ghost" in error

    empty_design = SimpleNamespace(get_all_bodies=lambda: [], named_selections=[])
    bodies, error = resolve_bodies(app_context, empty_design)
    assert bodies == []
    assert "no bodies" in error
