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
            "extend_selection",
            arguments={"entity_type": "body", "criteria": "nearby", "distance": 0.0},
        ),
        expected="extend_selection",
    ),
    EvalCase(
        id="create_named_selection",
        prompt="Save the body 'bolt_01' as a named selection called 'inlet_faces'.",
        checker=expect_tool(
            "create_named_selection",
            arguments={"name": "inlet_faces", "body_names": ["bolt_01"]},
        ),
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
    # -- Repair (inspect vs. fix are mutually confusable) --------------------
    EvalCase(
        id="inspect_geometry",
        prompt="This imported part looks dirty. What is actually wrong with it?",
        checker=expect_tool("inspect_geometry", arguments={}),
        expected="inspect_geometry",
        note="Confusable with repair_geometry; asking what is wrong must not mutate the model.",
    ),
    EvalCase(
        id="repair_geometry_all",
        prompt=(
            "I have already inspected this model and seen the issues. "
            "Now run the automatic repair over the whole thing."
        ),
        checker=expect_tool("repair_geometry", arguments={"operation": "all"}),
        expected="repair_geometry",
        note="Undiagnosed 'just clean it up' prompts steer to inspect_geometry first by design.",
    ),
    EvalCase(
        id="repair_stitch_faces",
        prompt="These surfaces should form a closed solid. Stitch them together.",
        checker=expect_tool("repair_geometry", arguments={"operation": "stitch_faces"}),
        expected="repair_geometry(stitch_faces)",
        note="Confusable with unite_body.",
    ),
    EvalCase(
        id="repair_short_edges",
        prompt="Remove the sliver edges shorter than 0.1 mm from the body named 'housing'.",
        checker=expect_tool(
            "repair_geometry",
            arguments={
                "operation": "short_edges",
                "length": 0.0001,
                "body_names": ["housing"],
            },
        ),
        expected="repair_geometry(short_edges)",
        note="Checks operation dispatch plus mm-to-m conversion and body scoping.",
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
