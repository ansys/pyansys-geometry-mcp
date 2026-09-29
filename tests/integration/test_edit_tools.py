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

"""Unit tests for the edit tools."""

from ansys.geometry.mcp.tools import (
    create_box,
    create_design,
    intersect_body,
    subtract_body,
    unite_body,
)


def test_boolean_operations(ctx):
    """Test subtract, unite, and intersect boolean operations on overlapping boxes."""
    create_design(ctx, "test_boolean_ops_001")
    for prefix in ("subtract", "unite", "intersect"):
        create_box(ctx, name=f"{prefix}_target", width=2.0, depth=2.0, height=2.0)
        create_box(ctx, name=f"{prefix}_tool", width=1.0, depth=1.0, height=1.0)

    assert "complete" in subtract_body(
        ctx, target_body_name="subtract_target", tool_body_name="subtract_tool"
    )
    assert "complete" in unite_body(
        ctx, target_body_name="unite_target", tool_body_name="unite_tool"
    )
    assert "complete" in intersect_body(
        ctx, target_body_name="intersect_target", tool_body_name="intersect_tool"
    )
