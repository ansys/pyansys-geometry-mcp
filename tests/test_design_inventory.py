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

"""Backend-free tests for recursive design inventories and construction-object discovery."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ansys.geometry.mcp import app
from ansys.geometry.mcp.tools import get_design_info, get_session_script, list_entities

CONSTRUCTION_TYPES = [
    "design_curves",
    "datum_points",
    "datum_planes",
    "datum_lines",
    "coordinate_systems",
]
COLLECTIONS = [
    "bodies",
    "beams",
    "design_points",
    "design_curves",
    "datum_points",
    "datum_planes",
    "datum_lines",
    "coordinate_systems",
]


def _component(identifier, name, children=(), alive=True):
    return SimpleNamespace(
        id=identifier,
        name=name,
        is_alive=alive,
        components=list(children),
        **{attribute: [] for attribute in COLLECTIONS},
    )


def _entity(identifier, name="construction", alive=True):
    return SimpleNamespace(id=identifier, name=name, is_alive=alive)


@pytest.fixture
def inventory_ctx():
    grandchild = _component("grandchild", "nested")
    child = _component("child", "assembly", [grandchild])
    sibling = _component("sibling", "assembly")
    deleted = _component("deleted", "deleted", alive=False)
    design = _component("root", "inventory", [child, sibling, deleted])
    design.is_active = True
    design.named_selections = [object()]
    design.materials = [object(), object()]
    design.beam_profiles = [object()]
    for component in (design, child, grandchild, sibling, deleted):
        for attribute in COLLECTIONS:
            component_entities = [_entity(f"{component.id}:{attribute}")]
            if attribute != "design_points":
                component_entities.append(
                    _entity(f"{component.id}:{attribute}:deleted", alive=False)
                )
            setattr(component, attribute, component_entities)
    ctx = MagicMock()
    ctx.fastmcp._lifespan_result.product_instance.get_active_design.return_value = design
    ctx.fastmcp._lifespan_result.command_history = []
    return ctx


def test_recursive_design_inventory(inventory_ctx):
    result = get_design_info(inventory_ctx)
    fields = {
        line.strip().split(":", 1)[0].strip(): line.split(":", 1)[1].strip()
        for line in result.splitlines()[1:]
    }
    assert fields == {
        "Name": "inventory",
        "Is active?": "True",
        "N Bodies": "4",
        "N Components": "3",
        "N Coordinate Systems": "4",
        "N Named Selections": "1",
        "N Materials": "2",
        "N Beams": "4",
        "N Beam Profiles": "1",
        "N Datum Points": "4",
        "N Datum Planes": "4",
        "N Datum Lines": "4",
        "N Design Points": "4",
        "N Design Curves": "4",
    }


def test_empty_design_inventory(inventory_ctx):
    design = inventory_ctx.fastmcp._lifespan_result.product_instance.get_active_design()
    design.components = []
    for attribute in COLLECTIONS + ["named_selections", "materials", "beam_profiles"]:
        setattr(design, attribute, [])
    result = get_design_info(inventory_ctx)
    counts = [
        line.split(":", 1)[1].strip() for line in result.splitlines() if line.startswith("  N ")
    ]
    assert counts == ["0"] * 12


@pytest.mark.parametrize("entity_type", CONSTRUCTION_TYPES)
@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({}, ["root", "child", "grandchild", "sibling"]),
        ({"component_id": "child"}, ["child", "grandchild"]),
        ({"component_id": "sibling"}, ["sibling"]),
        ({"component_id": "deleted"}, []),
        ({"name": "CONSTRUCTION"}, ["root", "child", "grandchild", "sibling"]),
        ({"component_id": "child", "name": "CONSTRUCTION"}, ["child", "grandchild"]),
        ({"name": "missing"}, []),
    ],
)
def test_list_construction_entities_and_replay(inventory_ctx, entity_type, kwargs, expected):
    attribute = entity_type
    result = list_entities(inventory_ctx, entity_type, **kwargs)
    paths = {
        "root": "construction",
        "child": "assembly/construction",
        "grandchild": "assembly/nested/construction",
        "sibling": "assembly/construction",
    }
    if kwargs.get("component_id") == "child":
        paths.update(child="construction", grandchild="nested/construction")
    elif kwargs.get("component_id") == "sibling":
        paths["sibling"] = "construction"
    if expected:
        assert result.splitlines() == [
            f"id={identifier}:{attribute}  path={paths[identifier]}" for identifier in expected
        ]
    else:
        label = attribute.replace("_", " ")
        assert result == (
            f"No {label} named 'missing' found." if "name" in kwargs else f"No {label} found."
        )

    app_context = inventory_ctx.fastmcp._lifespan_result
    assert len(app_context.command_history) == 1
    namespace = {"design": app_context.product_instance.get_active_design()}
    exec(app_context.command_history[-1], namespace)
    assert [entity.id for entity in namespace[attribute]] == [
        f"{identifier}:{attribute}" for identifier in expected
    ]
    assert get_session_script(inventory_ctx)


@pytest.mark.parametrize("entity_type", CONSTRUCTION_TYPES)
def test_empty_and_invalid_construction_scope(inventory_ctx, entity_type):
    design = inventory_ctx.fastmcp._lifespan_result.product_instance.get_active_design()
    attribute = entity_type
    empty = _component("empty", "empty")
    design.components.append(empty)
    assert list_entities(inventory_ctx, entity_type, component_id="empty") == (
        f"No {attribute.replace('_', ' ')} found."
    )
    history = inventory_ctx.fastmcp._lifespan_result.command_history
    assert len(history) == 1
    assert list_entities(inventory_ctx, entity_type, component_id="missing") == (
        "Component ID 'missing' not found."
    )
    assert len(history) == 1


@pytest.mark.parametrize("tool", [get_design_info, list_entities])
def test_inventory_connection_and_backend_errors(inventory_ctx, tool):
    kwargs = {"entity_type": "design_curves"} if tool is list_entities else {}
    instance = inventory_ctx.fastmcp._lifespan_result.product_instance
    instance.get_active_design.side_effect = RuntimeError("inventory unavailable")
    result = tool(inventory_ctx, **kwargs)
    assert result.startswith("Error")
    assert "inventory unavailable" in result
    assert inventory_ctx.fastmcp._lifespan_result.command_history == []
    inventory_ctx.fastmcp._lifespan_result.product_instance = None
    assert "not connected" in tool(inventory_ctx, **kwargs)


@pytest.mark.parametrize("entity_type", ["body", "component", "face", "edge"])
def test_existing_entity_listings_and_replay(inventory_ctx, entity_type):
    app_context = inventory_ctx.fastmcp._lifespan_result
    design = app_context.product_instance.get_active_design()
    child = design.components[0]
    design.components = [child]
    child.components = []
    root_body = _entity("root_body", name="box")
    child_body = _entity("child_body", name="box")
    root_body._template = SimpleNamespace(id="root_body")
    child_body._template = SimpleNamespace(id="child_body")
    root_body.faces = [SimpleNamespace(id="face", surface_type=SimpleNamespace(name="PLANE"))]
    root_body.edges = [SimpleNamespace(id="edge", curve_type=SimpleNamespace(name="LINE"))]
    design.bodies = [root_body]
    child.bodies = [child_body]
    design.get_all_bodies = lambda: [root_body, child_body]
    design._get_all_components = lambda: [child]
    kwargs = {"body_id": root_body.id} if entity_type in ("face", "edge") else {}
    result = list_entities(inventory_ctx, entity_type, **kwargs)
    assert (
        result.splitlines()
        == {
            "body": ["id=root_body  path=box", "id=child_body  path=assembly/box"],
            "component": ["id=child  name=assembly"],
            "face": ["id=face  surface_type=PLANE"],
            "edge": ["id=edge  curve_type=LINE"],
        }[entity_type]
    )
    namespace = {"design": design}
    exec(app_context.command_history[-1], namespace)
    variable = "bodies" if entity_type == "body" else f"{entity_type}s"
    assert {entity.id for entity in namespace[variable]} == {
        line.split()[0].removeprefix("id=") for line in result.splitlines()
    }
    if entity_type == "body":
        assert list_entities(inventory_ctx, "body", name="BOX", component_id="child") == (
            "id=child_body  path=box"
        )


async def test_inventory_tool_discovery_schema():
    registered = {tool.name: tool for tool in await app.list_tools()}
    options = registered["list_entities"].parameters["properties"]["entity_type"]["enum"]
    assert set(options) == {"body", "component", "face", "edge", *CONSTRUCTION_TYPES}
    assert "including objects inside components" in registered["get_design_info"].description
    assert "construction lines" in registered["get_design_info"].description
