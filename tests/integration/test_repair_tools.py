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
