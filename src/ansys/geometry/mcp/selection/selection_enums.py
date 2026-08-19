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

"""Selection enum tables to help the MCP resolve the correct enum values for selection criteria."""

from ansys.geometry.core.designer.edge import CurveType
from ansys.geometry.core.designer.face import SurfaceType
from ansys.geometry.core.selection_builder.selection_builder import ExtendScope

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
