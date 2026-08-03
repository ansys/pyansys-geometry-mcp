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

"""Face selection handler for the MCP selection pipeline."""

from typing import TYPE_CHECKING

from ansys.geometry.core.misc.auxiliary import get_faces_from_ids
from ansys.geometry.core.selection_builder.face_selection import FaceSelection

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
    from ansys.geometry.core.designer.face import Face


@register_handler
class FaceSelectionHandler(BaseSelectionHandler):
    """Selection handler for ``Face`` entities."""

    ENTITY_TYPE = "face"
    CHILD_TYPES = ("edge",)

    ACTIONS: dict[str, ActionSpec] = {
        # Queries — start a fresh selection from the whole document.
        "get_all": ActionSpec("get_all_faces"),
        "get_all_visible": ActionSpec("get_all_visible_faces"),
        "get_from_named_selection": ActionSpec("get_faces_from_named_selection"),
        "get_with_area": ActionSpec("get_faces_with_area"),
        "get_with_x_location": ActionSpec(
            "get_faces_with_x_location", {"range_type": resolve_range_type}
        ),
        "get_with_y_location": ActionSpec(
            "get_faces_with_y_location", {"range_type": resolve_range_type}
        ),
        "get_with_z_location": ActionSpec(
            "get_faces_with_z_location", {"range_type": resolve_range_type}
        ),
        "get_with_color": ActionSpec("get_faces_with_color"),
        # Invert.
        "invert": ActionSpec("invert_face_selection", {"scope": resolve_invert_topology_scope}),
        # Filters.
        "filter_by_area": ActionSpec("filter_faces_by_area"),
        "filter_max_area": ActionSpec("filter_faces_max_area"),
        "filter_min_area": ActionSpec("filter_faces_min_area"),
        "filter_by_perimeter": ActionSpec("filter_faces_by_perimeter"),
        "filter_max_perimeter": ActionSpec("filter_faces_max_perimeter"),
        "filter_min_perimeter": ActionSpec("filter_faces_min_perimeter"),
        "filter_by_edge_count": ActionSpec("filter_faces_by_edge_count"),
        "filter_max_edge_count": ActionSpec("filter_faces_max_edge_count"),
        "filter_min_edge_count": ActionSpec("filter_faces_min_edge_count"),
        "filter_by_loop_count": ActionSpec("filter_faces_by_loop_count"),
        "filter_max_loop_count": ActionSpec("filter_faces_max_loop_count"),
        "filter_min_loop_count": ActionSpec("filter_faces_min_loop_count"),
        "filter_by_number_curves": ActionSpec(
            "filter_faces_by_number_curves", {"curve_type": resolve_curve_type}
        ),
        "filter_max_number_curves": ActionSpec(
            "filter_faces_max_number_curves", {"curve_type": resolve_curve_type}
        ),
        "filter_min_number_curves": ActionSpec(
            "filter_faces_min_number_curves", {"curve_type": resolve_curve_type}
        ),
        "filter_containing_curve_types": ActionSpec(
            "filter_faces_containing_curve_types", {"curve_type": resolve_curve_type}
        ),
        "filter_by_color": ActionSpec("filter_faces_by_color"),
        "filter_area_percentile": ActionSpec("filter_faces_area_percentile"),
        "filter_perimeter_percentile": ActionSpec("filter_faces_perimeter_percentile"),
        "filter_edge_count_percentile": ActionSpec("filter_faces_edge_count_percentile"),
        "filter_loop_count_percentile": ActionSpec("filter_faces_loop_count_percentile"),
        "filter_by_number_curves_percentile": ActionSpec(
            "filter_faces_by_number_curves_percentile", {"curve_type": resolve_curve_type}
        ),
        # Extend.
        "extend_to_same_area": ActionSpec("extend_to_same_area", {"scope": resolve_extend_scope}),
        "extend_to_same_number_of_edges": ActionSpec(
            "extend_to_same_number_of_edges", {"scope": resolve_extend_scope}
        ),
        "extend_to_same_number_of_loops": ActionSpec(
            "extend_to_same_number_of_loops", {"scope": resolve_extend_scope}
        ),
        "extend_to_same_color": ActionSpec("extend_to_same_color", {"scope": resolve_extend_scope}),
        "extend_to_coincident": ActionSpec("extend_to_coincident", {"scope": resolve_extend_scope}),
        "extend_to_coaxial": ActionSpec("extend_to_coaxial_faces", {"scope": resolve_extend_scope}),
        # Order.
        "order_by_area": ActionSpec("order_faces_by_area"),
        "order_by_perimeter": ActionSpec("order_faces_by_perimeter"),
        "order_by_edge_count": ActionSpec("order_faces_by_edge_count"),
        "order_by_loop_count": ActionSpec("order_faces_by_loop_count"),
        "order_by_number_curves": ActionSpec(
            "order_faces_by_number_curves", {"curve_type": resolve_curve_type}
        ),
    }

    @classmethod
    def build_initial(cls, design: "Design", grpc_client: "GrpcClient") -> FaceSelection:  # noqa: D102
        return FaceSelection(design, grpc_client)

    @classmethod
    def build_from_ids(  # noqa: D102
        cls, design: "Design", grpc_client: "GrpcClient", ids: list[str]
    ) -> FaceSelection:
        return FaceSelection(design, grpc_client, get_faces_from_ids(design, ids))

    @classmethod
    def build_from_items(  # noqa: D102
        cls, design: "Design", grpc_client: "GrpcClient", items: list["Face"]
    ) -> FaceSelection:
        return FaceSelection(design, grpc_client, list(items))

    @classmethod
    def serialize(cls, selection: FaceSelection) -> list[dict]:  # noqa: D102
        return [
            {"id": face.id, "surface_type": face.surface_type.name, "area": str(face.area)}
            for face in selection.items
        ]

    @classmethod
    def get_child_entities(cls, selection: FaceSelection, target_type: str) -> list:  # noqa: D102
        if target_type == "edge":
            return list(dict.fromkeys(edge for face in selection.items for edge in face.edges))
        return super().get_child_entities(selection, target_type)
