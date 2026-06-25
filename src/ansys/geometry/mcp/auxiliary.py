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

"""Auxiliary functions for PyAnsys Geometry MCP server tools."""


def _find_body(design, body_name: str):
    """Find a body by name across the full design tree.

    Uses ``Component.get_all_bodies()``, which recursively collects every body
    in the component hierarchy.
    """
    for body in design.get_all_bodies():
        if body.name == body_name:
            return body
    return None


def _build_sketch(
    sketch_primitives: list[dict],
    plane_origin: list[float] | None = None,
    plane_dir_x: list[float] | None = None,
    plane_dir_y: list[float] | None = None,
):
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
    Sketch
        The populated sketch object.

    """
    from ansys.geometry.core.math import Plane, Point2D, Point3D, UnitVector3D
    from ansys.geometry.core.sketch import Sketch

    accumulated_commands: list[str] = []

    if plane_origin is not None and plane_dir_x is not None and plane_dir_y is not None:
        sketch = Sketch(
            Plane(
                origin=Point3D(plane_origin),
                direction_x=UnitVector3D(plane_dir_x),
                direction_y=UnitVector3D(plane_dir_y),
            )
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
                f"sketch.segment(start=Point2D([{prim['start_x']}, {prim['start_y']}]), end=Point2D([{prim['end_x']}, {prim['end_y']}])"
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