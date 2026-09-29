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

"""Selection enum tables to help the MCP resolve the correct enum values for selection criteria."""

from ansys.geometry.core.designer.edge import CurveType
from ansys.geometry.core.designer.face import SurfaceType
from ansys.geometry.core.selection_builder.selection_builder import ExtendScope, RangeType

_SURFACE_TYPE_MAP = {
    "plane": SurfaceType.SURFACETYPE_PLANE,
    "cylinder": SurfaceType.SURFACETYPE_CYLINDER,
    "cone": SurfaceType.SURFACETYPE_CONE,
    "torus": SurfaceType.SURFACETYPE_TORUS,
    "sphere": SurfaceType.SURFACETYPE_SPHERE,
    "nurbs": SurfaceType.SURFACETYPE_NURBS,
    "procedural": SurfaceType.SURFACETYPE_PROCEDURAL,
    "spline": SurfaceType.SURFACETYPE_SPLINESURFACE,
}

_CURVE_TYPE_MAP = {
    "line": CurveType.CURVETYPE_LINE,
    "circle": CurveType.CURVETYPE_CIRCLE,
    "ellipse": CurveType.CURVETYPE_ELLIPSE,
    "nurbs": CurveType.CURVETYPE_NURBS,
    "procedural": CurveType.CURVETYPE_PROCEDURAL,
    "helix": CurveType.CURVETYPE_HELIX,
    "spline": CurveType.CURVETYPE_SPLINECURVE,
}

_SCOPE_MAP = {
    "all": ExtendScope.EXTENDSCOPE_ALL,
    "visible": ExtendScope.EXTENDSCOPE_VISIBLE,
    "body": ExtendScope.EXTENDSCOPE_BODY,
}

# Face and edge location queries require an explicit range type; bodies do not take one.
_DEFAULT_RANGE_TYPE = RangeType.RANGETYPE_INTERSECT
