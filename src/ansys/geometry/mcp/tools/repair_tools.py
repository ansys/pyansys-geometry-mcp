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

"""MCP repair tools for PyAnsys Geometry MCP server.

Tools that survey and clean up imported or otherwise defective geometry:
``inspect_geometry`` reports issues without touching the model, and
``repair_geometry`` applies one repair operation to a scope of bodies.

Each function decorated with ``@app.tool()`` is exposed as an MCP tool.
The ``ctx`` parameter provides access to the application context (and thus
to the live product instance and command history).

Notes
-----
Import this module in ``tools/__init__.py`` (already done) to register these
tools with the server before it starts.

"""

from typing import Literal

from ansys.common.mcp.logging_config import get_logger
from fastmcp.server import Context

from ansys.geometry.mcp import app
from ansys.geometry.mcp.misc.auxiliary import get_geometry_ctx, resolve_bodies

logger = get_logger(__name__)

RepairOperation = Literal[
    "all",
    "short_edges",
    "extra_edges",
    "split_edges",
    "simplify",
    "stitch_faces",
]

# Operation -> (RepairTools method, tuning parameters that method accepts).
_REPAIR_OPERATIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "all": ("repair_geometry", ()),
    "short_edges": ("find_and_fix_short_edges", ("length",)),
    "extra_edges": ("find_and_fix_extra_edges", ()),
    "split_edges": ("find_and_fix_split_edges", ("angle", "length")),
    "simplify": ("find_and_fix_simplify", ()),
    "stitch_faces": (
        "find_and_fix_stitch_faces",
        (
            "max_distance",
            "allow_multiple_bodies",
            "maintain_components",
            "check_for_coincidence",
        ),
    ),
}


def _bodies_transcript(bodies) -> str:
    """Render the resolved body scope as a replayable transcript line."""
    names = ", ".join(repr(body.name) for body in bodies)
    return f"bodies = [design.get_body(name) for name in [{names}]]"


def _summarize(operation: str, message, body_count: int) -> str:
    """Render a ``RepairToolMessage`` as a single human-readable line."""
    parts = [
        f"Repair '{operation}' ran on {body_count} bodies. Success: {message.success}.",
    ]
    if message.found >= 0 or message.repaired >= 0:
        parts.append(
            f"Problem areas found: {message.found}, repaired: {message.repaired} "
            "(counts are for this call only, not totals for the design)."
        )
    for label, monikers in (
        ("Created", message.created_bodies),
        ("Modified", message.modified_bodies),
        ("Deleted", message.deleted_bodies),
    ):
        if monikers:
            parts.append(f"{label} bodies: {len(monikers)}.")
    return " ".join(parts)


@app.tool()
def inspect_geometry(
    ctx: Context,
    body_names: list[str] | None = None,
    named_selection: str | None = None,
    selection_handle: str | None = None,
) -> str:
    """Report geometry issues (defects) found in the design, without modifying it.

    This is the read-only diagnosis step, for when the defect is not yet known:
    run it to find out what is wrong with imported or defective geometry. It
    does not change the model, so it is always safe to call. It is also the way
    to confirm what a repair actually changed.

    If the user has already said what is wrong ("fix the short edges under
    0.5 mm"), skip this tool and call ``repair_geometry`` directly.

    By default every body in the active design is inspected. Narrow the scope
    with exactly one of ``body_names``, ``named_selection``, or
    ``selection_handle``.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    body_names : list of str, optional
        Names of the bodies to inspect. Use ``list_entities`` to discover names.
    named_selection : str, optional
        Label of a named selection whose bodies should be inspected.
    selection_handle : str, optional
        Handle of a selection builder (from ``create_selection_builder``) whose
        selected bodies should be inspected.

    Returns
    -------
    str
        Issues grouped by body, or an error message.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot inspect geometry."

    try:
        design = app_context.product_instance.get_active_design()
        bodies, error = resolve_bodies(
            app_context, design, body_names, named_selection, selection_handle
        )
        if error is not None:
            return error

        results = app_context.product_instance.repair_tools.inspect_geometry(bodies)
        app_context.command_history.append(_bodies_transcript(bodies))
        app_context.command_history.append("instance.repair_tools.inspect_geometry(bodies)")
        logger.info(f"inspect_geometry: {len(bodies)} bodies, {len(results)} with issues.")

        if not results:
            return f"Inspected {len(bodies)} bodies. No geometry issues found."

        lines = [f"Inspected {len(bodies)} bodies. Issues found on {len(results)}:"]
        for result in results:
            lines.append(f"{result.body.name}: {len(result.issues)} issues")
            for issue in result.issues:
                scope = []
                if issue.faces:
                    scope.append(f"{len(issue.faces)} faces")
                if issue.edges:
                    scope.append(f"{len(issue.edges)} edges")
                suffix = f" ({', '.join(scope)})" if scope else ""
                lines.append(f"  [{issue.message_type}] {issue.message}{suffix}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"inspect_geometry failed: {e}")
        return f"Error inspecting geometry: {e}"


@app.tool()
def repair_geometry(
    ctx: Context,
    operation: RepairOperation,
    body_names: list[str] | None = None,
    named_selection: str | None = None,
    selection_handle: str | None = None,
    length: float | None = None,
    angle: float | None = None,
    max_distance: float | None = None,
    allow_multiple_bodies: bool | None = None,
    maintain_components: bool | None = None,
    check_for_coincidence: bool | None = None,
    comprehensive_result: bool = False,
) -> str:
    """Repair defective geometry by finding and fixing one class of problem area.

    Use this to clean up imported or faulty CAD: remove slivers, merge
    fragmented edges, simplify over-complex faces, or stitch surfaces into
    solids.

    When the user has already named the defect ("fix the short edges under
    0.5 mm", "stitch these surfaces"), call this tool directly — running
    ``inspect_geometry`` first is unnecessary. Reach for ``inspect_geometry``
    only when the defect is unknown and needs diagnosing first.

    ``operation`` selects what to repair:

    - ``"all"``
        Run the backend's blanket repair, letting it inspect and fix everything
        it can across the scope. Use it when the user explicitly asks for an
        automatic whole-design repair; an undiagnosed problem should go to
        ``inspect_geometry`` first. Accepts no tuning parameters, and supplying
        one (including ``comprehensive_result``) is rejected.
    - ``"short_edges"``
        Remove edges shorter than ``length``. Accepts ``length``.
    - ``"extra_edges"``
        Remove redundant edges that do not bound a real feature.
    - ``"split_edges"``
        Merge edges that were needlessly split. Accepts ``angle`` and ``length``.
    - ``"simplify"``
        Replace over-complex (spline) faces with analytic ones where possible.
    - ``"stitch_faces"``
        Join adjacent surface bodies into solids. Accepts ``max_distance``,
        ``allow_multiple_bodies``, ``maintain_components``, and
        ``check_for_coincidence``.

    Passing a tuning parameter that the chosen operation does not accept is
    rejected rather than silently ignored.

    By default every body in the active design is repaired. Narrow the scope
    with exactly one of ``body_names``, ``named_selection``, or
    ``selection_handle``.

    Partial repair is a normal outcome: the modeling kernel legitimately
    declines work that would invalidate adjacent topology, so problem areas can
    remain afterwards. The reported ``found``/``repaired`` counts are results
    for this call only, not totals for the design; report them as such rather
    than measuring the model to confirm them. If the user asks what state the
    design is actually in, re-run ``inspect_geometry`` scoped to the bodies
    this call modified — do not count edges or faces by hand.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    operation : str
        Which repair to apply: ``"all"``, ``"short_edges"``, ``"extra_edges"``,
        ``"split_edges"``, ``"simplify"``, or ``"stitch_faces"``.
    body_names : list of str, optional
        Names of the bodies to repair. Use ``list_entities`` to discover names.
    named_selection : str, optional
        Label of a named selection whose bodies should be repaired.
    selection_handle : str, optional
        Handle of a selection builder (from ``create_selection_builder``) whose
        selected bodies should be repaired.
    length : float, optional
        Maximum edge length, in metres, for ``"short_edges"`` and ``"split_edges"``.
    angle : float, optional
        Maximum angle between edges, in degrees, for ``"split_edges"``.
    max_distance : float, optional
        Maximum gap between faces to stitch, in metres, for ``"stitch_faces"``.
    allow_multiple_bodies : bool, optional
        Whether ``"stitch_faces"`` may leave more than one resulting body.
    maintain_components : bool, optional
        Whether ``"stitch_faces"`` stitches only within each component.
    check_for_coincidence : bool, optional
        Whether ``"stitch_faces"`` also searches for coincident surfaces.
    comprehensive_result : bool, optional
        Fix each problem area individually. Expensive: it costs one backend
        round trip per problem area. Leave off unless the user asks for it.
        Not supported by ``operation="all"``.

    Returns
    -------
    str
        Summary of what was found and repaired, or an error message.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot repair geometry."

    if operation not in _REPAIR_OPERATIONS:
        return (
            f"Unknown repair operation '{operation}'. "
            f"Supported operations: {', '.join(sorted(_REPAIR_OPERATIONS))}."
        )

    method_name, accepted = _REPAIR_OPERATIONS[operation]
    supplied = {
        "length": length,
        "angle": angle,
        "max_distance": max_distance,
        "allow_multiple_bodies": allow_multiple_bodies,
        "maintain_components": maintain_components,
        "check_for_coincidence": check_for_coincidence,
    }
    rejected = [
        name for name, value in supplied.items() if value is not None and name not in accepted
    ]
    if comprehensive_result and operation == "all":
        rejected.append("comprehensive_result")
    if rejected:
        allowed = ", ".join(accepted) or "none"
        return (
            f"Parameters not supported by operation '{operation}': {', '.join(rejected)}. "
            f"Supported tuning parameters for this operation: {allowed}."
        )

    kwargs = {name: supplied[name] for name in accepted if supplied[name] is not None}
    if operation != "all":
        kwargs["comprehensive_result"] = comprehensive_result

    call_kwargs = dict(kwargs)
    if "angle" in call_kwargs:
        # PyAnsys Geometry reads a bare float as radians; this tool's contract is degrees.
        from ansys.geometry.core.misc import UNITS, Angle

        call_kwargs["angle"] = Angle(call_kwargs["angle"], UNITS.degree)

    try:
        design = app_context.product_instance.get_active_design()
        bodies, error = resolve_bodies(
            app_context, design, body_names, named_selection, selection_handle
        )
        if error is not None:
            return error

        method = getattr(app_context.product_instance.repair_tools, method_name)
        message = method(bodies, **call_kwargs)

        kwargs_str = "".join(
            f", {name}=Angle({value!r}, UNITS.degree)" if name == "angle" else f", {name}={value!r}"
            for name, value in kwargs.items()
        )
        if "angle" in kwargs:
            app_context.command_history.append("from ansys.geometry.core.misc import UNITS, Angle")
        app_context.command_history.append(_bodies_transcript(bodies))
        app_context.command_history.append(
            f"instance.repair_tools.{method_name}(bodies{kwargs_str})"
        )
        logger.info(f"repair_geometry: operation={operation!r}, bodies={len(bodies)}")

        return _summarize(operation, message, len(bodies))
    except Exception as e:
        logger.error(f"repair_geometry failed: {e}")
        return f"Error repairing geometry with operation '{operation}': {e}"
