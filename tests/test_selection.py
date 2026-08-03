# Copyright (C) 2026 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
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

"""Tests for the ``ansys.geometry.mcp.selection`` pipeline.

These tests use mocked ``*Selection`` objects and domain entities rather than
a live geometry service, since the handler methods are thin, stateless
forwarding calls (see ``selection/_base.py``). What's under test is the
registry dispatch, enum resolution, transition logic, and the MCP tool
plumbing in ``selection/tools.py`` -- not the underlying gRPC behavior, which
belongs to ``ansys-geometry-core``.
"""

from unittest.mock import MagicMock

from ansys.geometry.core.selection_builder.selection_builder import ExtendScope, InvertScope
import pytest

from ansys.geometry.mcp.selection import HANDLER_REGISTRY, tools as selection_tools, transition
from ansys.geometry.mcp.selection._resolvers import resolve_extend_scope, resolve_invert_scope


class TestResolvers:
    """Tests for the enum string resolvers."""

    def test_resolves_short_name_case_insensitive(self):
        """A short name like "visible" resolves regardless of case."""
        assert resolve_invert_scope("visible") == InvertScope.INVERTSCOPE_VISIBLE
        assert resolve_invert_scope("VISIBLE") == InvertScope.INVERTSCOPE_VISIBLE

    def test_passes_through_existing_enum_member(self):
        """An already-resolved enum member is returned unchanged."""
        assert resolve_invert_scope(InvertScope.INVERTSCOPE_ALL) == InvertScope.INVERTSCOPE_ALL

    def test_resolves_full_prefixed_name(self):
        """A fully prefixed enum member name (e.g. "EXTENDSCOPE_BODY") also resolves."""
        assert resolve_extend_scope("EXTENDSCOPE_BODY") == ExtendScope.EXTENDSCOPE_BODY

    def test_invalid_value_raises_with_valid_options_listed(self):
        """An unresolvable value raises ValueError listing the valid options."""
        with pytest.raises(ValueError, match="Invalid scope 'bogus'"):
            resolve_invert_scope("bogus")


class TestHandlerRegistry:
    """Tests for handler registration."""

    def test_all_three_entity_types_registered(self):
        """Body, face, and edge handlers are all registered."""
        assert set(HANDLER_REGISTRY) == {"body", "face", "edge"}

    def test_body_can_transition_to_face_and_edge(self):
        """Body selections can transition into either faces or edges."""
        assert HANDLER_REGISTRY["body"].CHILD_TYPES == ("face", "edge")

    def test_face_can_transition_to_edge_only(self):
        """Face selections can only transition into edges."""
        assert HANDLER_REGISTRY["face"].CHILD_TYPES == ("edge",)

    def test_edge_is_a_leaf(self):
        """Edge selections have no further downward transitions."""
        assert HANDLER_REGISTRY["edge"].CHILD_TYPES == ()


class TestApplyStep:
    """Tests for ``BaseSelectionHandler.apply_step`` dispatch."""

    def test_dispatches_to_underlying_method_with_params(self):
        """A step's action resolves to the correct underlying method call."""
        handler = HANDLER_REGISTRY["body"]
        selection = MagicMock()
        selection.filter_bodies_by_volume.return_value = "NEW_SELECTION"

        result = handler.apply_step(selection, {"action": "filter_by_volume", "min": 0.001})

        assert result == "NEW_SELECTION"
        selection.filter_bodies_by_volume.assert_called_once_with(min=0.001)

    def test_resolves_enum_params_before_dispatch(self):
        """Enum-valued params are resolved from strings before the call."""
        handler = HANDLER_REGISTRY["body"]
        selection = MagicMock()
        selection.invert_body_selection.return_value = "INVERTED"

        result = handler.apply_step(selection, {"action": "invert", "scope": "all"})

        assert result == "INVERTED"
        selection.invert_body_selection.assert_called_once_with(scope=InvertScope.INVERTSCOPE_ALL)

    def test_unknown_action_raises_value_error(self):
        """An action name not present in the ACTIONS table raises ValueError."""
        handler = HANDLER_REGISTRY["body"]
        with pytest.raises(ValueError, match="Unknown action 'nope'"):
            handler.apply_step(MagicMock(), {"action": "nope"})


class TestTransition:
    """Tests for cross-entity-type transitions."""

    def test_body_to_face_dedups_shared_faces(self):
        """Transitioning body -> face collects and de-duplicates child faces."""
        face_1, face_2 = MagicMock(), MagicMock()
        body = MagicMock()
        body.faces = [face_1, face_2, face_1]
        selection = MagicMock(items=[body])

        result = transition(MagicMock(), MagicMock(), "body", selection, "face")

        assert result.items == [face_1, face_2]

    def test_invalid_transition_raises(self):
        """An unsupported transition (e.g. edge -> face) raises ValueError."""
        with pytest.raises(ValueError, match="Cannot transition from 'edge' to 'face'"):
            transition(MagicMock(), MagicMock(), "edge", MagicMock(), "face")

    def test_unknown_entity_type_raises(self):
        """An unregistered source entity type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown source entity type"):
            transition(MagicMock(), MagicMock(), "solid", MagicMock(), "face")


class TestRunPipeline:
    """Tests for the ``_run_pipeline`` helper backing the MCP tools."""

    def test_no_product_instance_returns_error(self):
        """Running the pipeline without a connected product returns an error dict."""
        app_context = MagicMock(product_instance=None)
        result = selection_tools._run_pipeline(app_context, "body", [])
        assert "error" in result

    def test_unknown_entity_type_returns_error(self):
        """An unregistered starting entity type returns an error dict."""
        app_context = MagicMock()
        result = selection_tools._run_pipeline(app_context, "solid", [])
        assert "error" in result
        assert "solid" in result["error"]

    def test_pipeline_applies_steps_and_logs_history(self, mocker):
        """Filtering bodies returns serialized items and logs command history."""
        body = MagicMock()
        body.id = "B1"
        body.name = "Body1"

        initial_selection = MagicMock(items=[body])
        filtered_selection = MagicMock(items=[body])
        initial_selection.filter_bodies_by_volume.return_value = filtered_selection

        body_handler = HANDLER_REGISTRY["body"]
        mocker.patch.object(body_handler, "build_initial", return_value=initial_selection)

        app_context = MagicMock(command_history=[])

        result = selection_tools._run_pipeline(
            app_context,
            "body",
            [{"action": "filter_by_volume", "min": 0.001}],
        )

        assert result == {
            "entity_type": "body",
            "items": [{"id": "B1", "name": "Body1"}],
        }
        assert len(app_context.command_history) == 1


class TestGetChildEntities:
    """Tests for the ``get_child_entities`` MCP tool."""

    def test_no_product_instance_returns_error(self):
        """Running without a connected product returns an error dict."""
        app_context = MagicMock(product_instance=None)
        ctx = MagicMock(fastmcp=MagicMock(_lifespan_result=app_context))
        result = selection_tools.get_child_entities(ctx, "body", ["B1"], "edge")
        assert "error" in result

    def test_unknown_parent_entity_type_returns_error(self):
        """An unregistered parent entity type returns an error dict."""
        app_context = MagicMock()
        ctx = MagicMock(fastmcp=MagicMock(_lifespan_result=app_context))
        result = selection_tools.get_child_entities(ctx, "solid", ["S1"], "edge")
        assert "error" in result
        assert "solid" in result["error"]

    def test_unsupported_child_type_returns_error(self):
        """Requesting a child type not in CHILD_TYPES returns an error dict."""
        app_context = MagicMock()
        ctx = MagicMock(fastmcp=MagicMock(_lifespan_result=app_context))
        result = selection_tools.get_child_entities(ctx, "edge", ["E1"], "face")
        assert "error" in result

    def test_body_to_edge_returns_deduped_child_edges(self, mocker):
        """Getting edges of bodies returns deduplicated, serialized edges."""
        edge = MagicMock()
        edge.id = "E1"
        edge.curve_type.name = "CIRCLE"
        edge.length = "0.1 m"

        body = MagicMock()
        body.edges = [edge, edge]

        body_handler = HANDLER_REGISTRY["body"]
        parent_selection = MagicMock(items=[body])
        mocker.patch.object(body_handler, "build_from_ids", return_value=parent_selection)

        app_context = MagicMock(command_history=[])
        ctx = MagicMock(fastmcp=MagicMock(_lifespan_result=app_context))

        result = selection_tools.get_child_entities(ctx, "body", ["B1"], "edge")

        assert result == {
            "entity_type": "edge",
            "items": [{"id": "E1", "curve_type": "CIRCLE", "length": "0.1 m"}],
        }
        assert len(app_context.command_history) == 1


class TestCreateNamedSelection:
    """Tests for the ``create_named_selection`` MCP tool."""

    def test_no_product_instance_returns_error(self):
        """Running without a connected product returns an error dict."""
        app_context = MagicMock(product_instance=None)
        ctx = MagicMock(fastmcp=MagicMock(_lifespan_result=app_context))
        result = selection_tools.create_named_selection(ctx, "MyNS", "body", ["B1"])
        assert "error" in result

    def test_unknown_entity_type_returns_error(self):
        """An unregistered entity type returns an error dict."""
        app_context = MagicMock()
        ctx = MagicMock(fastmcp=MagicMock(_lifespan_result=app_context))
        result = selection_tools.create_named_selection(ctx, "MyNS", "solid", ["S1"])
        assert "error" in result
        assert "solid" in result["error"]

    def test_empty_entity_ids_returns_error(self):
        """An empty entity_ids list returns an error dict."""
        app_context = MagicMock()
        ctx = MagicMock(fastmcp=MagicMock(_lifespan_result=app_context))
        result = selection_tools.create_named_selection(ctx, "MyNS", "body", [])
        assert "error" in result

    def test_creates_named_selection_from_bodies(self, mocker):
        """Creating a named selection from body IDs passes bodies= to the design."""
        body = MagicMock()
        body_handler = HANDLER_REGISTRY["body"]
        selection = MagicMock(items=[body])
        mocker.patch.object(body_handler, "build_from_ids", return_value=selection)

        named_selection = MagicMock()
        named_selection.name = "MyNS"
        named_selection.id = "NS1"
        design = MagicMock()
        design.create_named_selection.return_value = named_selection

        app_context = MagicMock(command_history=[])
        app_context.product_instance.get_active_design.return_value = design
        ctx = MagicMock(fastmcp=MagicMock(_lifespan_result=app_context))

        result = selection_tools.create_named_selection(ctx, "MyNS", "body", ["B1"])

        design.create_named_selection.assert_called_once_with("MyNS", bodies=[body])
        assert result == {
            "name": "MyNS",
            "id": "NS1",
            "entity_type": "body",
            "count": 1,
        }
        assert len(app_context.command_history) == 1
