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
