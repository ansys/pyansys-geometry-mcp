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

"""Prompt dataset for the LLM evaluation suite.

Most cases exercise MCP tool discoverability (a ``checker`` built with
:func:`checks.expect_tool` or :func:`checks.expect_no_tool`), but the harness
is not limited to that: :func:`checks.expect_text_contains` and
:func:`checks.expect_text_matches` score a plain-text answer instead, so the
same dataset/runner can grow to cover other prompt/response evaluations.
"""

from dataclasses import dataclass

from ._harness import Checker
from .checks import expect_no_tool, expect_text_contains, expect_tool


@dataclass(frozen=True)
class EvalCase:
    """A single prompt, how the response is scored, and what "expected" means."""

    id: str
    prompt: str
    checker: Checker
    expected: str = ""
    #: Attach the MCP tool schemas to the request. Disable for prompts that
    #: are evaluated purely on their text content and shouldn't offer tools.
    tools: bool = True
    note: str = ""


CASES: list[EvalCase] = [
    # -- Session and design lifecycle --------------------------------------
    EvalCase(
        id="product_status",
        prompt="Is the geometry backend up and running right now?",
        checker=expect_tool("get_product_status", arguments={}),
        expected="get_product_status",
    ),
    EvalCase(
        id="create_design",
        prompt="Start a new design called 'bracket' so I can begin modeling.",
        checker=expect_tool("create_design", arguments={"design_name": "bracket"}),
        expected="create_design",
    ),
    EvalCase(
        id="design_info",
        prompt="Give me a summary of the design that is currently open.",
        checker=expect_tool("get_design_info", arguments={}),
        expected="get_design_info",
    ),
    EvalCase(
        id="import_geometry",
        prompt=r"Open the file C:\models\flange.scdocx in the geometry service.",
        checker=expect_tool(
            "import_geometry_file", arguments={"file_path": r"C:\models\flange.scdocx"}
        ),
        expected="import_geometry_file",
    ),
    EvalCase(
        id="export_design",
        prompt=r"Save the current design out as a STEP file at D:\out\flange.stp.",
        checker=expect_tool("export_design_to", arguments={"file_format": "step"}),
        expected="export_design_to",
        note="Confusable with import_geometry_file.",
    ),
    EvalCase(
        id="command_history",
        prompt="Which commands have been run so far in this session?",
        checker=expect_tool("get_command_history", arguments={}),
        expected="get_command_history",
    ),
    EvalCase(
        id="run_python_code",
        prompt=(
            "Run this snippet in the backend Python session for me: "
            "print(sum(b.volume.m for b in design.bodies))"
        ),
        checker=expect_tool(
            "run_python_code",
            arguments={"code": "print(sum(b.volume.m for b in design.bodies))"},
        ),
        expected="run_python_code",
    ),
    # -- Body creation ------------------------------------------------------
    EvalCase(
        id="create_box",
        prompt="Make a rectangular block 10 mm wide, 20 mm long and 5 mm tall named 'base'.",
        checker=expect_tool(
            "create_box",
            arguments={"name": "base", "width": 0.01, "depth": 0.02, "height": 0.005},
        ),
        expected="create_box",
        note="Confusable with extrude_sketch.",
    ),
    EvalCase(
        id="extrude_sketch",
        prompt="Take a 25 mm circle on the XY plane and pull it up 40 mm into a solid cylinder.",
        checker=expect_tool("extrude_sketch", arguments={"distance": 0.04}),
        expected="extrude_sketch",
        note="Only 'distance' is asserted; sketch_primitives shape/name are model's choice.",
    ),
    EvalCase(
        id="revolve_sketch",
        prompt="Spin a profile 360 degrees about the Z axis to produce a body of revolution.",
        checker=expect_tool(
            "revolve_sketch", arguments={"axis_direction": [0, 0, 1], "angle_deg": 360}
        ),
        expected="revolve_sketch",
        note="Confusable with extrude_sketch. rotation_origin is not asserted (ambiguous).",
    ),
    # -- Boolean operations (mutually confusable) ---------------------------
    EvalCase(
        id="subtract_body",
        prompt="Cut the body named 'pin' out of the body named 'block'.",
        checker=expect_tool(
            "subtract_body", arguments={"target_body_name": "block", "tool_body_name": "pin"}
        ),
        expected="subtract_body",
    ),
    EvalCase(
        id="unite_body",
        prompt="Merge 'plate_left' and 'plate_right' together into a single body.",
        checker=expect_tool(
            "unite_body",
            arguments={"target_body_name": "plate_left", "tool_body_name": "plate_right"},
        ),
        expected="unite_body",
        note="Union is symmetric; target/tool role is only a guess at which name survives.",
    ),
    EvalCase(
        id="intersect_body",
        prompt="Keep only the volume that 'sphere_a' and 'sphere_b' have in common.",
        checker=expect_tool(
            "intersect_body",
            arguments={"target_body_name": "sphere_a", "tool_body_name": "sphere_b"},
        ),
        expected="intersect_body",
        note="Intersection is symmetric; target/tool role is only a guess at which name survives.",
    ),
    # -- Components ---------------------------------------------------------
    EvalCase(
        id="add_component",
        prompt="Create a sub-assembly called 'fasteners' in the current design.",
        checker=expect_tool("add_component", arguments={"name": "fasteners"}),
        expected="add_component",
    ),
    EvalCase(
        id="move_body_to_component",
        prompt="Put the body 'bolt_01' inside the 'fasteners' component.",
        checker=expect_tool(
            "move_body_to_component",
            arguments={"body_name": "bolt_01", "target_component_name": "fasteners"},
        ),
        expected="move_body_to_component",
    ),
    EvalCase(
        id="list_bodies",
        prompt="What bodies exist in the active design?",
        checker=expect_tool("list_entities", arguments={"entity_type": "body"}),
        expected="list_entities",
        note="Confusable with select_entities and get_design_info.",
    ),
    # -- Selection workflow -------------------------------------------------
    EvalCase(
        id="create_selection_builder",
        prompt="Set up a new empty selection so I can start collecting bodies into it.",
        checker=expect_tool("create_selection_builder", arguments={}),
        expected="create_selection_builder",
    ),
    EvalCase(
        id="select_entities",
        prompt="Using my selection builder, pick up every solid body in the design.",
        checker=expect_tool(
            "select_entities", arguments={"entity_type": "body", "criteria": "solid"}
        ),
        expected="select_entities",
    ),
    EvalCase(
        id="filter_entities",
        prompt="From the bodies already in my selection, drop everything with a volume below 100.",
        checker=expect_tool(
            "filter_entities",
            arguments={"entity_type": "body", "criteria": "volume", "min_value": 100},
        ),
        expected="filter_entities",
        note="Confusable with select_entities.",
    ),
    EvalCase(
        id="order_entities",
        prompt="Sort the bodies currently in my selection from smallest to largest volume.",
        checker=expect_tool(
            "order_entities", arguments={"entity_type": "body", "criteria": "volume"}
        ),
        expected="order_entities",
    ),
    EvalCase(
        id="group_entities",
        prompt="Bucket the bodies in my selection by the colour they share.",
        checker=expect_tool(
            "group_entities", arguments={"entity_type": "body", "criteria": "color"}
        ),
        expected="group_entities",
    ),
    EvalCase(
        id="extend_selection",
        prompt="Grow my current selection to also include the bodies touching the ones I picked.",
        checker=expect_tool(
            "extend_selection", arguments={"entity_type": "body", "criteria": "nearby"}
        ),
        expected="extend_selection",
    ),
    EvalCase(
        id="create_named_selection",
        prompt="Save the bodies I selected as a named selection called 'inlet_faces'.",
        checker=expect_tool("create_named_selection", arguments={"name": "inlet_faces"}),
        expected="create_named_selection",
    ),
    # -- Visualization ------------------------------------------------------
    EvalCase(
        id="get_screenshot",
        prompt="Show me a picture of what the model looks like right now.",
        checker=expect_tool("get_screenshot", arguments={}),
        expected="get_screenshot",
        note="Confusable with get_design_3d_scene.",
    ),
    EvalCase(
        id="get_design_3d_scene",
        prompt="Open an interactive 3D view of the design that I can rotate.",
        checker=expect_tool("get_design_3d_scene", arguments={}),
        expected="get_design_3d_scene",
    ),
    # -- Negative cases: the model should answer without calling a tool -----
    EvalCase(
        id="no_tool_concept_question",
        prompt="In CAD terms, what is the difference between a solid body and a surface body?",
        checker=expect_no_tool(),
        expected="no tool",
        note="Pure knowledge question; over-triggering is the failure mode.",
    ),
    EvalCase(
        id="no_tool_off_topic",
        prompt="What is the weather like in Lyon today?",
        checker=expect_no_tool(),
        expected="no tool",
    ),
    # -- Plain text-response cases: not tool discoverability at all --------
    EvalCase(
        id="text_explains_brep",
        prompt="In one short sentence, what is a B-rep (boundary representation) solid?",
        checker=expect_text_contains("boundary"),
        expected="text mentions 'boundary'",
        tools=False,
        note="Demonstrates scoring a plain-text answer instead of a tool call.",
    ),
    EvalCase(
        id="text_lists_boolean_ops",
        prompt="Name the three boolean operations you can perform on two solid bodies.",
        checker=expect_text_contains("union", "subtract", "intersect", case_sensitive=False),
        expected="text mentions union/subtract/intersect",
        tools=False,
    ),
]
