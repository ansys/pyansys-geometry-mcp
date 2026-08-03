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

"""Edge selection handler for the MCP selection pipeline."""

from typing import TYPE_CHECKING

from ansys.geometry.core.misc.auxiliary import get_edges_from_ids
from ansys.geometry.core.selection_builder.edge_selection import EdgeSelection

from ansys.geometry.mcp.selection._base import ActionSpec, BaseSelectionHandler, register_handler
from ansys.geometry.mcp.selection._resolvers import (
    resolve_curve_type,
    resolve_extend_scope,
    resolve_invert_topology_scope,
    resolve_range_type,
)

if TYPE_CHECKING:
    from ansys.geometry.core.connection.client import GrpcClient
    from ansys.geometry.core.designer.design import Design
    from ansys.geometry.core.designer.edge import Edge


@register_handler
class EdgeSelectionHandler(BaseSelectionHandler):
    """Selection handler for ``Edge`` entities.

    Edge is the leaf entity type in the selection hierarchy: it has no
    ``CHILD_TYPES`` and does not support further downward transitions.
    """

    ENTITY_TYPE = "edge"
    CHILD_TYPES: tuple[str, ...] = ()

    ACTIONS: dict[str, ActionSpec] = {
        # Queries — start a fresh selection from the whole document.
        "get_all": ActionSpec("get_all_edges"),
        "get_all_visible": ActionSpec("get_all_visible_edges"),
        "get_from_named_selection": ActionSpec("get_edges_from_named_selection"),
        "get_with_length": ActionSpec("get_edges_with_length"),
        "get_with_x_location": ActionSpec(
            "get_edges_with_x_location", {"range_type": resolve_range_type}
        ),
        "get_with_y_location": ActionSpec(
            "get_edges_with_y_location", {"range_type": resolve_range_type}
        ),
        "get_with_z_location": ActionSpec(
            "get_edges_with_z_location", {"range_type": resolve_range_type}
        ),
        # Invert.
        "invert": ActionSpec("invert_edge_selection", {"scope": resolve_invert_topology_scope}),
        # Filters.
        "filter_by_length": ActionSpec("filter_edges_by_length"),
        "filter_max_length": ActionSpec("filter_edges_max_length"),
        "filter_min_length": ActionSpec("filter_edges_min_length"),
        "filter_by_curve_type": ActionSpec(
            "filter_edges_by_curve_type", {"curve_type": resolve_curve_type}
        ),
        "filter_length_percentile": ActionSpec("filter_edges_length_percentile"),
        # Extend.
        "extend_nearby": ActionSpec("extend_nearby_edges", {"scope": resolve_extend_scope}),
        "extend_to_connected": ActionSpec("extend_to_connected", {"scope": resolve_extend_scope}),
        "extend_to_tangent_chain": ActionSpec(
            "extend_to_tangent_chain", {"scope": resolve_extend_scope}
        ),
        "extend_to_coaxial": ActionSpec("extend_to_coaxial_edges", {"scope": resolve_extend_scope}),
        # Order.
        "order_by_length": ActionSpec("order_edges_by_length"),
    }

    @classmethod
    def build_initial(cls, design: "Design", grpc_client: "GrpcClient") -> EdgeSelection:  # noqa: D102
        return EdgeSelection(design, grpc_client)

    @classmethod
    def build_from_ids(  # noqa: D102
        cls, design: "Design", grpc_client: "GrpcClient", ids: list[str]
    ) -> EdgeSelection:
        return EdgeSelection(design, grpc_client, get_edges_from_ids(design, ids))

    @classmethod
    def build_from_items(  # noqa: D102
        cls, design: "Design", grpc_client: "GrpcClient", items: list["Edge"]
    ) -> EdgeSelection:
        return EdgeSelection(design, grpc_client, list(items))

    @classmethod
    def serialize(cls, selection: EdgeSelection) -> list[dict]:  # noqa: D102
        return [
            {"id": edge.id, "curve_type": edge.curve_type.name, "length": str(edge.length)}
            for edge in selection.items
        ]
