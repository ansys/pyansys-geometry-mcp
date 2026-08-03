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

"""String-to-enum resolvers shared by the selection handlers.

MCP tool callers supply plain strings for enum-valued parameters (for example
``"visible"`` instead of ``InvertScope.INVERTSCOPE_VISIBLE``). These helpers
resolve those strings (case-insensitively, with or without the enum's type
prefix) to the actual ``ansys.geometry.core`` enum members.
"""

from enum import Enum
from typing import TypeVar

from ansys.geometry.core.designer.edge import CurveType
from ansys.geometry.core.designer.face import SurfaceType
from ansys.geometry.core.selection_builder.selection_builder import (
    ExtendScope,
    InvertScope,
    InvertTopologyScope,
    RangeType,
    StringFilterType,
)

_EnumT = TypeVar("_EnumT", bound=Enum)


def _resolve_enum(enum_cls: type[_EnumT], value, prefix: str, param_name: str) -> _EnumT:
    """Resolve a user-supplied value to a member of ``enum_cls``.

    Parameters
    ----------
    enum_cls : type[Enum]
        Enum class to resolve against.
    value : Enum | str
        Value supplied by the caller. May already be an ``enum_cls`` member, or a
        string such as ``"visible"``, ``"INVERTSCOPE_VISIBLE"``, or ``"invertscope_visible"``.
    prefix : str
        The enum's member-name prefix (for example ``"INVERTSCOPE"``).
    param_name : str
        Name of the parameter being resolved, used in error messages.

    Returns
    -------
    Enum
        The resolved enum member.

    """
    if isinstance(value, enum_cls):
        return value

    key = str(value).strip().upper().replace("-", "_").replace(" ", "_")
    candidates = (key, f"{prefix}_{key}")
    for candidate in candidates:
        if candidate in enum_cls.__members__:
            return enum_cls.__members__[candidate]

    valid = ", ".join(
        member.name[len(prefix) + 1 :].lower()
        if member.name.startswith(f"{prefix}_")
        else member.name.lower()
        for member in enum_cls
    )
    raise ValueError(f"Invalid {param_name} '{value}'. Valid values: {valid}")


def resolve_string_filter_type(value) -> StringFilterType:
    """Resolve a string filter type (``"text"``, ``"wildcard"``, ``"regex"``, ...)."""
    if isinstance(value, str) and value.strip().upper() in ("REGEX", "REGULAR_EXPRESSION"):
        return StringFilterType.STRINGFILTERTYPE_REGULAREXPRESSION
    return _resolve_enum(StringFilterType, value, "STRINGFILTERTYPE", "filter_type")


def resolve_invert_scope(value) -> InvertScope:
    """Resolve a body-level invert scope (``"visible"``, ``"all"``)."""
    return _resolve_enum(InvertScope, value, "INVERTSCOPE", "scope")


def resolve_invert_topology_scope(value) -> InvertTopologyScope:
    """Resolve a topology-level invert scope (``"all"``, ``"body"``, ``"visible"``)."""
    return _resolve_enum(InvertTopologyScope, value, "INVERTTOPOLOGYSCOPE", "scope")


def resolve_extend_scope(value) -> ExtendScope:
    """Resolve an extend scope (``"all"``, ``"body"``, ``"visible"``)."""
    return _resolve_enum(ExtendScope, value, "EXTENDSCOPE", "scope")


def resolve_range_type(value) -> RangeType:
    """Resolve a location range type (``"intersect"``, ``"contain"``)."""
    return _resolve_enum(RangeType, value, "RANGETYPE", "range_type")


def resolve_surface_type(value) -> SurfaceType:
    """Resolve a surface type.

    Accepts ``"plane"``, ``"cylinder"``, ``"cone"``, ``"torus"``, ``"sphere"``,
    ``"nurbs"``, ``"procedural"``, ``"splinesurface"``, or ``"unknown"``.
    """
    return _resolve_enum(SurfaceType, value, "SURFACETYPE", "surface_type")


def resolve_curve_type(value) -> CurveType:
    """Resolve a curve type.

    Accepts ``"line"``, ``"circle"``, ``"ellipse"``, ``"nurbs"``, ``"procedural"``,
    ``"helix"``, ``"splinecurve"``, or ``"unknown"``.
    """
    return _resolve_enum(CurveType, value, "CURVETYPE", "curve_type")
