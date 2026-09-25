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

"""Shared helpers used by the MCP tool modules."""

from typing import TYPE_CHECKING

from fastmcp.server import Context

from ansys.geometry.mcp.context import PyAnsysGeometryContext

if TYPE_CHECKING:
    from ansys.geometry.core.designer.body import Body
    from ansys.geometry.core.designer.component import Component
    from ansys.geometry.core.designer.selection import NamedSelection
    from ansys.geometry.core.sketch import Sketch


def get_geometry_ctx(ctx: Context) -> "PyAnsysGeometryContext":
    """Access the PyAnsysGeometryContext from the MCP context."""
    return ctx.fastmcp._lifespan_result  # type: ignore[return-value]


def find_body(design, body_name: str) -> "Body" | None:
    """Find a body by name across the full design tree.

    Uses ``Component.get_all_bodies()``, which recursively collects every body
    in the component hierarchy.

    Parameters
    ----------
    design : Design
        Active design to search within.
    body_name : str
        Name of the body to find.

    Returns
    -------
    Body | None
        The body with the specified name, or None if not found.

    """
    for body in design.get_all_bodies():
        if body.name == body_name:
            return body
    return None


def find_component(design, component_name: str) -> "Component" | None:
    """Find a component by name across the full design tree.

    Uses ``Design._get_all_components()``, which recursively collects every
    component in the design hierarchy.

    Parameters
    ----------
    design : Design
        Active design to search within.
    component_name : str
        Name of the component to find.

    Returns
    -------
    Component | None
        The component with the specified name, or None if not found.

    """
    for comp in design._get_all_components():
        if comp.name == component_name:
            return comp
    return None


def find_named_selection(design, name: str) -> "NamedSelection" | None:
    """Find a named selection by name in the design.

    Parameters
    ----------
    design : Design
        Active design to search within.
    name : str
        Name of the named selection to find.

    Returns
    -------
    NamedSelection | None
        The named selection with the specified name, or None if not found.

    """
    for named_selection in design.named_selections:
        if named_selection.name == name:
            return named_selection
    return None


def resolve_bodies(
    app_context,
    design,
    body_names: list[str] | None = None,
    named_selection: str | None = None,
    selection_handle: str | None = None,
) -> tuple[list["Body"], str | None]:
    """Resolve the bodies a tool should act on from the ways a caller can name them.

    Precedence is ``selection_handle``, then ``named_selection``, then
    ``body_names``, then every body in the design.

    Parameters
    ----------
    app_context : PyAnsysGeometryContext
        Application state, used to look up ``selection_handle``.
    design : Design
        Active design to resolve against.
    body_names : list of str, optional
        Body names, as reported by ``list_entities``.
    named_selection : str, optional
        Label of a named selection whose bodies should be used.
    selection_handle : str, optional
        Handle of a selection builder from ``create_selection_builder``.

    Returns
    -------
    tuple[list[Body], str | None]
        ``(bodies, error)``. ``error`` is ``None`` on success; otherwise the
        body list is empty and the string is meant to be returned to the caller.

    """
    if selection_handle:
        selection_builder = app_context.selection_registry.get(selection_handle)
        if selection_builder is None:
            return [], f"Invalid selection handle: {selection_handle}"
        selected = getattr(selection_builder, "_bodies", None)
        bodies = list(selected.items) if selected is not None else []
        if not bodies:
            return [], f"Selection '{selection_handle}' has no bodies selected."
        return bodies, None

    if named_selection:
        found = find_named_selection(design, named_selection)
        if found is None:
            available = ", ".join(ns.name for ns in design.named_selections) or "none"
            return [], (f"Named selection '{named_selection}' not found. Available: {available}.")
        bodies = list(found.bodies)
        if not bodies:
            return [], f"Named selection '{named_selection}' contains no bodies."
        return bodies, None

    if body_names:
        bodies = []
        missing = []
        for body_name in body_names:
            body = find_body(design, body_name)
            if body is None:
                missing.append(body_name)
            else:
                bodies.append(body)
        if missing:
            return [], (
                f"Bodies not found: {', '.join(missing)}. "
                "Use list_entities to see available bodies."
            )
        return bodies, None

    bodies = list(design.get_all_bodies())
    if not bodies:
        return [], "The active design contains no bodies."
    return bodies, None


def build_sketch(
    sketch_primitives: list[dict],
    plane_origin: list[float] | None = None,
    plane_dir_x: list[float] | None = None,
    plane_dir_y: list[float] | None = None,
) -> tuple["Sketch", list[str]]:
    """Build a Sketch from a list of primitive dicts and an optional plane definition.

    Parameters
    ----------
    sketch_primitives : list of dict
        Each dict must have a ``"type"`` key. See ``extrude_sketch`` for supported types.
    plane_origin : list of float, optional
        ``[x, y, z]`` origin of the sketch plane.
    plane_dir_x : list of float, optional
        ``[x, y, z]`` X direction of the sketch plane.
    plane_dir_y : list of float, optional
        ``[x, y, z]`` Y direction of the sketch plane.

    Returns
    -------
    tuple[Sketch, list[str]]
        The populated sketch object and the list of accumulated commands.

    """
    from ansys.geometry.core.math import Plane, Point2D, Point3D, UnitVector3D
    from ansys.geometry.core.sketch import Sketch

    accumulated_commands: list[str] = [
        "from ansys.geometry.core.sketch import Sketch",
        "from ansys.geometry.core.math import Point2D",
    ]

    if plane_origin is not None and plane_dir_x is not None and plane_dir_y is not None:
        sketch = Sketch(
            Plane(
                origin=Point3D(plane_origin),
                direction_x=UnitVector3D(plane_dir_x),
                direction_y=UnitVector3D(plane_dir_y),
            )
        )
        accumulated_commands.append(
            "from ansys.geometry.core.math import Plane, Point3D, UnitVector3D"
        )
        accumulated_commands.append(
            f"sketch = Sketch(Plane(origin=Point3D({plane_origin}), "
            f"direction_x=UnitVector3D({plane_dir_x}), "
            f"direction_y=UnitVector3D({plane_dir_y})))"
        )
    else:
        sketch = Sketch()
        accumulated_commands.append("sketch = Sketch()")

    for prim in sketch_primitives:
        prim_type = prim.get("type", "").lower()
        center = Point2D([prim.get("center_x", 0.0), prim.get("center_y", 0.0)])

        if prim_type == "circle":
            sketch.circle(center=center, radius=prim["radius"])
            accumulated_commands.append(
                f"sketch.circle(center=Point2D({[prim.get('center_x', 0.0), prim.get('center_y', 0.0)]}), radius={prim['radius']})"
            )
        elif prim_type == "box":
            sketch.box(center=center, width=prim["width"], height=prim["height"])
            accumulated_commands.append(
                f"sketch.box(center=Point2D({[prim.get('center_x', 0.0), prim.get('center_y', 0.0)]}), width={prim['width']}, height={prim['height']})"
            )
        elif prim_type == "polygon":
            # inner_radius is the apothem (distance from centre to midpoint of a side)
            sketch.polygon(
                center=center,
                inner_radius=prim["inner_radius"],
                sides=int(prim["sides"]),
            )
            accumulated_commands.append(
                f"sketch.polygon(center=Point2D({[prim.get('center_x', 0.0), prim.get('center_y', 0.0)]}), inner_radius={prim['inner_radius']}, sides={int(prim['sides'])})"
            )
        elif prim_type == "segment":
            sketch.segment(
                start=Point2D([prim["start_x"], prim["start_y"]]),
                end=Point2D([prim["end_x"], prim["end_y"]]),
            )
            accumulated_commands.append(
                f"sketch.segment(start=Point2D([{prim['start_x']}, {prim['start_y']}]), end=Point2D([{prim['end_x']}, {prim['end_y']}]))"
            )
        elif prim_type == "arc":
            # arc requires start, end, and center points
            sketch.arc(
                start=Point2D([prim["start_x"], prim["start_y"]]),
                end=Point2D([prim["end_x"], prim["end_y"]]),
                center=center,
                clockwise=prim.get("clockwise", False),
            )
            accumulated_commands.append(
                f"sketch.arc(start=Point2D([{prim['start_x']}, {prim['start_y']}]), end=Point2D([{prim['end_x']}, {prim['end_y']}]), center=Point2D({[prim.get('center_x', 0.0), prim.get('center_y', 0.0)]}), clockwise={prim.get('clockwise', False)})"
            )
        else:
            raise ValueError(
                f"Unsupported sketch primitive type: {prim_type!r}. "
                "Supported types: circle, box, polygon, segment, arc."
            )

    return sketch, accumulated_commands
