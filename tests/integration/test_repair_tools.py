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

"""Unit tests for the repair tools."""

from ansys.geometry.mcp.tools import (
    create_box,
    create_design,
    create_named_selection,
    inspect_geometry,
    repair_geometry,
)


def test_repair_geometry_rejects_bad_input(ctx):
    """Test the unknown operation, inapplicable parameter, and unknown body error paths."""
    create_design(ctx, "test_repair_validation_001")
    create_box(ctx, name="repair_box", width=2.0, depth=2.0, height=2.0)

    assert "Unknown repair operation" in repair_geometry(ctx, operation="polish")

    rejected = repair_geometry(ctx, operation="extra_edges", angle=5.0)
    assert "not supported by operation 'extra_edges'" in rejected
    assert "angle" in rejected

    assert "comprehensive_result" in repair_geometry(
        ctx, operation="all", comprehensive_result=True
    )
    assert "ghost" in repair_geometry(ctx, operation="extra_edges", body_names=["ghost"])


def test_inspect_and_repair_round_trip(ctx):
    """Test inspecting, repairing, and re-inspecting across each body scoping mode."""
    create_design(ctx, "test_repair_round_trip_001")
    create_box(ctx, name="repair_box", width=2.0, depth=2.0, height=2.0)
    create_box(ctx, name="spare_box", width=1.0, depth=1.0, height=1.0)
    create_named_selection(ctx, name="repair_group", body_names=["repair_box"])

    assert "Inspected 2 bodies" in inspect_geometry(ctx)
    assert "Inspected 1 bodies" in inspect_geometry(ctx, body_names=["repair_box"])

    result = repair_geometry(ctx, operation="extra_edges", named_selection="repair_group")
    assert "Repair 'extra_edges' ran on 1 bodies" in result

    assert "Inspected 1 bodies" in inspect_geometry(ctx, named_selection="repair_group")
