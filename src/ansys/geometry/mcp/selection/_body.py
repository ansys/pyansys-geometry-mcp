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

"""Body selection handler for the MCP selection pipeline."""

from typing import TYPE_CHECKING

from ansys.geometry.core.misc.auxiliary import get_bodies_from_ids
from ansys.geometry.core.selection_builder.body_selection import BodySelection

from ansys.geometry.mcp.selection._base import ActionSpec, BaseSelectionHandler, register_handler
from ansys.geometry.mcp.selection._resolvers import (
    resolve_curve_type,
    resolve_extend_scope,
    resolve_invert_scope,
    resolve_range_type,
    resolve_string_filter_type,
    resolve_surface_type,
)

if TYPE_CHECKING:
    from ansys.geometry.core.connection.client import GrpcClient
    from ansys.geometry.core.designer.body import Body
    from ansys.geometry.core.designer.design import Design


@register_handler
class BodySelectionHandler(BaseSelectionHandler):
    """Selection handler for ``Body`` entities."""

    ENTITY_TYPE = "body"
    CHILD_TYPES = ("face", "edge")

    ACTIONS: dict[str, ActionSpec] = {
        # Queries — start a fresh selection from the whole document.
        "get_all": ActionSpec("get_all_bodies"),
        "get_all_visible": ActionSpec("get_all_visible_bodies"),
        "get_all_surface": ActionSpec("get_all_surface_bodies"),
        "get_all_solid": ActionSpec("get_all_solid_bodies"),
        "get_from_named_selection": ActionSpec("get_bodies_from_named_selection"),
        "get_with_name": ActionSpec(
            "get_bodies_with_name", {"filter_type": resolve_string_filter_type}
        ),
        "get_with_volume": ActionSpec("get_bodies_with_volume"),
        "get_with_surface_area": ActionSpec("get_bodies_with_surface_area"),
        "get_with_x_location": ActionSpec(
            "get_bodies_with_x_location", {"range_type": resolve_range_type}
        ),
        "get_with_y_location": ActionSpec(
            "get_bodies_with_y_location", {"range_type": resolve_range_type}
        ),
        "get_with_z_location": ActionSpec(
            "get_bodies_with_z_location", {"range_type": resolve_range_type}
        ),
        "get_with_color": ActionSpec("get_bodies_with_color"),
        # Invert.
        "invert": ActionSpec("invert_body_selection", {"scope": resolve_invert_scope}),
        # Filters.
        "filter_by_volume": ActionSpec("filter_bodies_by_volume"),
        "filter_max_volume": ActionSpec("filter_bodies_max_volume"),
        "filter_min_volume": ActionSpec("filter_bodies_min_volume"),
        "filter_by_surface_area": ActionSpec("filter_bodies_by_surface_area"),
        "filter_max_surface_area": ActionSpec("filter_bodies_max_surface_area"),
        "filter_min_surface_area": ActionSpec("filter_bodies_min_surface_area"),
        "filter_by_face_count": ActionSpec("filter_bodies_by_face_count"),
        "filter_max_face_count": ActionSpec("filter_bodies_max_face_count"),
        "filter_min_face_count": ActionSpec("filter_bodies_min_face_count"),
        "filter_by_edge_count": ActionSpec("filter_bodies_by_edge_count"),
        "filter_max_edge_count": ActionSpec("filter_bodies_max_edge_count"),
        "filter_min_edge_count": ActionSpec("filter_bodies_min_edge_count"),
        "filter_by_loop_count": ActionSpec("filter_bodies_by_loop_count"),
        "filter_max_loop_count": ActionSpec("filter_bodies_max_loop_count"),
        "filter_min_loop_count": ActionSpec("filter_bodies_min_loop_count"),
        "filter_by_number_surfaces": ActionSpec(
            "filter_bodies_by_number_surfaces", {"surface_type": resolve_surface_type}
        ),
        "filter_max_number_surfaces": ActionSpec(
            "filter_bodies_max_number_surfaces", {"surface_type": resolve_surface_type}
        ),
        "filter_min_number_surfaces": ActionSpec(
            "filter_bodies_min_number_surfaces", {"surface_type": resolve_surface_type}
        ),
        "filter_by_number_curves": ActionSpec(
            "filter_bodies_by_number_curves", {"curve_type": resolve_curve_type}
        ),
        "filter_max_number_curves": ActionSpec(
            "filter_bodies_max_number_curves", {"curve_type": resolve_curve_type}
        ),
        "filter_min_number_curves": ActionSpec(
            "filter_bodies_min_number_curves", {"curve_type": resolve_curve_type}
        ),
        "filter_by_number_surfaces_percentile": ActionSpec(
            "filter_bodies_by_number_surfaces_percentile",
            {"surface_type": resolve_surface_type},
        ),
        "filter_by_number_curves_percentile": ActionSpec(
            "filter_bodies_by_number_curves_percentile", {"curve_type": resolve_curve_type}
        ),
        "filter_by_color": ActionSpec("filter_bodies_by_color"),
        "filter_by_name": ActionSpec(
            "filter_bodies_by_name", {"filter_type": resolve_string_filter_type}
        ),
        "filter_containing_surface_types": ActionSpec(
            "filter_bodies_containing_surface_types", {"surface_type": resolve_surface_type}
        ),
        "filter_containing_curve_types": ActionSpec(
            "filter_bodies_containing_curve_types", {"curve_type": resolve_curve_type}
        ),
        "filter_volume_percentile": ActionSpec("filter_bodies_volume_percentile"),
        "filter_surface_area_percentile": ActionSpec("filter_bodies_surface_area_percentile"),
        "filter_face_count_percentile": ActionSpec("filter_bodies_face_count_percentile"),
        "filter_edge_count_percentile": ActionSpec("filter_bodies_edge_count_percentile"),
        "filter_loop_count_percentile": ActionSpec("filter_bodies_loop_count_percentile"),
        "filter_surface_bodies": ActionSpec("filter_surface_bodies"),
        "filter_solid_bodies": ActionSpec("filter_solid_bodies"),
        # Extend.
        "extend_to_same_volume": ActionSpec(
            "extend_to_same_volume", {"scope": resolve_extend_scope}
        ),
        "extend_to_same_surface_area": ActionSpec(
            "extend_to_same_surface_area", {"scope": resolve_extend_scope}
        ),
        "extend_to_same_number_of_faces": ActionSpec(
            "extend_to_same_number_of_faces", {"scope": resolve_extend_scope}
        ),
        "extend_to_same_number_of_edges": ActionSpec(
            "extend_to_same_number_of_edges", {"scope": resolve_extend_scope}
        ),
        "extend_to_same_color": ActionSpec("extend_to_same_color", {"scope": resolve_extend_scope}),
        "extend_to_same_name": ActionSpec("extend_to_same_name", {"scope": resolve_extend_scope}),
        "extend_nearby": ActionSpec("extend_nearby_bodies", {"scope": resolve_extend_scope}),
        # Order.
        "order_by_volume": ActionSpec("order_bodies_by_volume"),
        "order_by_surface_area": ActionSpec("order_bodies_by_surface_area"),
        "order_by_face_count": ActionSpec("order_bodies_by_face_count"),
        "order_by_edge_count": ActionSpec("order_bodies_by_edge_count"),
        "order_by_loop_count": ActionSpec("order_bodies_by_loop_count"),
        "order_by_number_of_surfaces": ActionSpec("order_bodies_by_number_of_surfaces"),
        "order_by_number_of_curves": ActionSpec("order_bodies_by_number_of_curves"),
    }

    @classmethod
    def build_initial(cls, design: "Design", grpc_client: "GrpcClient") -> BodySelection:  # noqa: D102
        return BodySelection(design, grpc_client)

    @classmethod
    def build_from_ids(  # noqa: D102
        cls, design: "Design", grpc_client: "GrpcClient", ids: list[str]
    ) -> BodySelection:
        return BodySelection(design, grpc_client, get_bodies_from_ids(design, ids))

    @classmethod
    def build_from_items(  # noqa: D102
        cls, design: "Design", grpc_client: "GrpcClient", items: list["Body"]
    ) -> BodySelection:
        return BodySelection(design, grpc_client, list(items))

    @classmethod
    def serialize(cls, selection: BodySelection) -> list[dict]:  # noqa: D102
        return [{"id": body.id, "name": body.name} for body in selection.items]

    @classmethod
    def get_child_entities(cls, selection: BodySelection, target_type: str) -> list:  # noqa: D102
        if target_type == "face":
            return list(dict.fromkeys(face for body in selection.items for face in body.faces))
        if target_type == "edge":
            return list(dict.fromkeys(edge for body in selection.items for edge in body.edges))
        return super().get_child_entities(selection, target_type)
