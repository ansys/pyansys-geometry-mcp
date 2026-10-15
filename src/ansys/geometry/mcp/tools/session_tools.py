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

"""MCP session tools for PyAnsys Geometry-MCP.

Each function decorated with ``@app.tool()`` is exposed as an MCP tool.
The ``ctx`` parameter provides access to the application context (and thus
to the live product instance and command history).

How to add a tool
-----------------
1. Define a Python function with type-annotated parameters.
2. Add a NumPy-style docstring. The summary line becomes the tool description.
   visible to the AI assistant.
3. Decorate it with ``@app.tool()``.
4. Access the product instance::

       app_context = ctx.fastmcp._lifespan_result
       instance = app_context.product_instance

Notes
-----
Import this module in ``__main__.py`` (already done) to register all tools
with the server before it starts.

"""

import json
from typing import Literal

from ansys.common.mcp.logging_config import get_logger
import ansys.common.mcp.tools as shared_tools
from fastmcp.server import Context

from ansys.geometry.mcp import app
from ansys.geometry.mcp.misc.auxiliary import get_geometry_ctx
from ansys.geometry.mcp.misc.helpers import (
    connect_to_modeler_in_persistent_python,
    refresh_design_in_persistent_python,
)

logger = get_logger(__name__)


@app.tool()
def get_session_script(ctx: Context) -> str:
    """Get recorded session commands as a reusable PyAnsys Geometry Python script.

    Includes recorded backend connection setup and commands in execution order.
    Returns Python source, not a list of commands or Markdown. Replay requires
    ansys-geometry-core and access to the recorded backend and referenced files.
    Replaying the script repeats its recorded geometry changes. Only operations
    recorded in command history are included. Backend script-file operations are not
    included.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).

    Returns
    -------
    str
        Formatted Python source, or an empty string if no commands were recorded.

    Raises
    ------
    ValueError
        If recorded commands cannot be formatted as valid Python.

    """
    app_context = get_geometry_ctx(ctx)
    commands = "\n".join(app_context.command_history)

    import black
    import isort

    try:
        sorted_commands = isort.code(commands)
        formatted_commands = black.format_str(sorted_commands, mode=black.Mode())
        return formatted_commands if formatted_commands else "No commands executed yet."
    except black.InvalidInput as error:
        raise ValueError("Recorded session commands are not valid Python.") from error


@app.tool()
def get_product_status(ctx: Context) -> str:
    """Get the current status of the product backend.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).

    Returns
    -------
    str
        Status message describing whether the product is connected.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Check server logs for startup errors."

    return f"Product backend is connected: {app_context.product_instance}"


@app.tool()
async def run_python_code(
    ctx: Context, code: str, timeout: int = 300, no_output_timeout: int = 300
) -> str:
    """Perform ANY geometry/CAD operation that has no dedicated MCP tool.

    Run PyAnsys Geometry API code to perform the operation.

    This is the general-purpose fallback tool. When the user asks for a modeling,
    query, or modification action (such as fillet, chamfer, shell, measure, pattern) and
    no other tool matches it, do NOT answer that it is unsupported. Write the
    equivalent ``ansys.geometry.core`` code and run it here. Choose a dedicated tool
    whenever one exists. Use ``run_script_file`` for an existing Discovery/SpaceClaim
    script file on disk. Never write a temporary file to run a few statements.

    The session is persistent, so variables defined by one call stay available to the
    next. ``instance`` (the ``Modeler``) and ``design`` are predefined. Import anything
    else explicitly. Bodies, faces, and edges are reached
    through the design tree (``design.bodies[0].faces[0].edges``) and edits are methods
    on those objects. Only stdout is returned, so ``print()`` the values you need. If
    you are unsure of the exact API, introspect it first with ``dir()`` or ``help()``, and then
    issue a second call with the real code.

    The code runs in a separate process that is connected to the same geometry
    service the other tools use, so bodies they created are immediately available
    here, and bodies created here are immediately visible to them.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    code : str
        PyAnsys Geometry Python code to execute in the persistent session.
    timeout : int, default: 300
        Maximum time in seconds the code may run before it is abandoned. Default 300.
    no_output_timeout : int, default: 300
        Maximum time in seconds the code may run without producing output before it
        is abandoned. Default 300.

    Returns
    -------
    str
        JSON string with ``success``, ``stdout``, ``stderr``, and ``error`` keys.
        On failure, read ``error``/``stderr``, correct the code, and retry rather than
        reporting the operation as impossible.

    """
    app_context = get_geometry_ctx(ctx)
    instance = app_context.product_instance
    if instance is None:
        return json.dumps(
            {
                "success": False,
                "stdout": "",
                "stderr": "",
                "error": "The product backend is not connected.",
            },
            ensure_ascii=False,
        )

    # Make sure the persistent Python session holds a Modeler before executing the code.
    session = ctx.request_context.lifespan_context.python_session
    if session.metadata.get("instance", None) is None:
        error = None
        try:
            modeler_instance = connect_to_modeler_in_persistent_python(ctx)
            # The helper returns a message instead of a Modeler when it cannot connect.
            if modeler_instance is None:
                error = "Failed to connect to the modeler in the persistent Python session."
            elif isinstance(modeler_instance, str):
                error = modeler_instance
        except Exception as e:
            error = f"Failed to connect to the modeler in the persistent Python session: {e}"

        if error is not None:
            logger.error(error)
            return json.dumps(
                {"success": False, "stdout": "", "stderr": "", "error": error},
                ensure_ascii=False,
            )

    result = await shared_tools.execute_python_code(
        ctx, code, timeout=timeout, no_output_timeout=no_output_timeout
    )
    try:
        parsed = json.loads(result)
        if parsed.get("success"):
            app_context.command_history.append(code)
    except (json.JSONDecodeError, AttributeError):
        pass

    return result


@app.tool()
def create_design(ctx: Context, design_name: str) -> str:
    """Create a new design in the product backend.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    design_name : str
        Name of the design to create.

    Returns
    -------
    str
        Result message indicating success or failure.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot create design."

    try:
        app_context.product_instance.create_design(design_name)
        refresh_design_in_persistent_python(ctx)

        # Perform transcript
        app_context.command_history.append(f"design=instance.create_design({design_name!r})")

        logger.info(f"create_design called with design_name={design_name!r}")
        return f"Design '{design_name}' created successfully."
    except Exception as e:
        logger.error(f"create_design failed: {e}")
        return f"Error creating design '{design_name}': {e}"


@app.tool()
def get_design_info(ctx: Context) -> str:
    """Get information about the current active design.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).

    Returns
    -------
    str
        Information about the design, or an error message if retrieval fails.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot retrieve design info."

    try:
        design = app_context.product_instance.get_active_design()
        logger.info("get_design_info called")
        return str(design)
    except Exception as e:
        logger.error(f"get_design_info failed: {e}")
        return f"Error retrieving info for design: {e}"


@app.tool()
def file_io(
    ctx: Context,
    operation: Literal["import", "export"],
    file_path: str | None = None,
    file_format: str | None = None,
    folder: str | None = None,
    mode: str = "open",
    import_names: bool = False,
    import_curves: bool = False,
    import_coordinate_systems: bool = False,
    import_named_selections: bool = True,
    cleanup_bodies: bool = False,
) -> str:
    """Import a geometry file or export the active design.

    Use ``operation="import"`` to open a geometry file as a new design or insert it
    into the active design. Supported extensions include ``scdocx``, ``dsco``,
    ``pmdb``, ``step``, ``iges``, ``x_t``, ``xmt_txt``, ``stride``, and reader formats
    such as ``CATIA``, ``Creo``, ``NX``, ``JT``, ``SOLIDWORKS``, ``Solid Edge``,
    ``Inventor``, ``Rhino``, and ``AutoCAD``.

    Use ``operation="export"`` to save the active design in ``fmd``, ``step``,
    ``iges``, ``scdocx``, ``disco``, ``parasolid_text``, or ``parasolid_bin``
    format.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    operation : Literal["import", "export"]
        Whether to import a file or export the active design.
    file_path : str, default: None
        Path of the file to import, including its extension. For a shattered assembly,
        give the path of the assembly file. Referenced files in the same folder are
        included automatically. This parameter is required for import.
    file_format : str, default: None
        Export format. Options are ``"fmd"``, ``"step"``, ``"iges"``, ``"scdocx"``,
        ``"disco"``, ``"parasolid_text"``, and ``"parasolid_bin"``. This parameter
        is required for export.
    folder : str, default: None
        Export destination. If omitted, the file is saved in the current working directory.
    mode : str, default: ``"open"``
        How to import the file. When ``"open"`` is used, the active design is closed
        and the file is opened as a new design.
        Use ``"insert"`` to add the file into the current active design as a new design.
        Use ``"insert"`` to add the file into the current active design as a new component.
    import_names : bool, default: False
        Whether to import the names of bodies and curves.
    import_curves : bool, default: False
        Whether to import curves.
    import_coordinate_systems : bool, default: False
        Whether to import coordinate systems.
    import_named_selections : bool, default: True
        Whether to import named selections.
    cleanup_bodies : bool, default: False
        Whether to simplify geometry and clean up topology on import.

    Returns
    -------
    str
        Result message describing the imported or exported file, or an error message.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot perform file operation."

    if operation == "export":
        if file_format is None:
            return "file_format is required when operation is 'export'."

        try:
            from ansys.geometry.core.designer import DesignFileFormat

            design = app_context.product_instance.get_active_design()
            if file_format.lower() == DesignFileFormat.FMD.name.lower():
                saved_path = design.export_to_fmd(folder)
                command = f"design.export_to_fmd({folder!r})"
            elif file_format.lower() == DesignFileFormat.STEP.name.lower():
                saved_path = design.export_to_step(folder)
                command = f"design.export_to_step({folder!r})"
            elif file_format.lower() == DesignFileFormat.IGES.name.lower():
                saved_path = design.export_to_iges(folder)
                command = f"design.export_to_iges({folder!r})"
            elif file_format.lower() == DesignFileFormat.SCDOCX.name.lower():
                saved_path = design.export_to_scdocx(folder)
                command = f"design.export_to_scdocx({folder!r})"
            elif file_format.lower() == DesignFileFormat.DISCO.name.lower():
                saved_path = design.export_to_disco(folder)
                command = f"design.export_to_disco({folder!r})"
            elif file_format.lower() == DesignFileFormat.PARASOLID_TEXT.name.lower():
                saved_path = design.export_to_parasolid_text(folder)
                command = f"design.export_to_parasolid_text({folder!r})"
            elif file_format.lower() == DesignFileFormat.PARASOLID_BIN.name.lower():
                saved_path = design.export_to_parasolid_bin(folder)
                command = f"design.export_to_parasolid_bin({folder!r})"
            else:
                return (
                    f"Unsupported format '{file_format}'. Supported formats are: fmd, step, "
                    "iges, scdocx, disco, parasolid_text, parasolid_bin."
                )

            app_context.command_history.append(command)
            logger.info(f"file_io export called, saved to {saved_path}")
            return f"Design exported to {file_format.upper()} file: {saved_path}"
        except Exception as e:
            logger.error(f"file_io export failed: {e}")
            return f"Error exporting design to {file_format.upper()}: {e}"

    if operation != "import":
        return (
            f"Unsupported file operation '{operation}'. Supported operations are: import, export."
        )
    if file_path is None:
        return "file_path is required when operation is 'import'."

    from pathlib import Path

    from ansys.geometry.core.misc import ImportOptions

    mode = mode.lower()
    if mode not in ("open", "insert"):
        return f"Unsupported mode '{mode}'. Supported modes are: open, insert."

    resolved = Path(file_path).resolve()
    if not resolved.exists():
        return f"File not found: {resolved}"
    if resolved.is_dir():
        return (
            f"Path is a directory, not a file: {resolved}. For a shattered assembly, point at "
            "the assembly file itself; its referenced files in the same folder are included "
            "automatically."
        )

    try:
        import_options = ImportOptions(
            cleanup_bodies=cleanup_bodies,
            import_coordinate_systems=import_coordinate_systems,
            import_curves=import_curves,
            import_names=import_names,
            import_named_selections=import_named_selections,
        )
        options_repr = (
            f"ImportOptions(cleanup_bodies={cleanup_bodies}, "
            f"import_coordinate_systems={import_coordinate_systems}, "
            f"import_curves={import_curves}, import_names={import_names}, "
            f"import_named_selections={import_named_selections})"
        )
        app_context.command_history.append("from ansys.geometry.core.misc import ImportOptions")
        app_context.command_history.append(f"import_options = {options_repr}")

        if mode == "open":
            design = app_context.product_instance.open_file(resolved, import_options=import_options)
            app_context.command_history.append(
                f"design = instance.open_file({str(resolved)!r}, import_options=import_options)"
            )
            body_count = len(design.get_all_bodies())
            logger.info(f"file_io import opened {resolved}")
            return (
                f"Imported '{resolved.name}' into new design '{design.name}' ({body_count} bodies)."
            )

        design = app_context.product_instance.get_active_design()
        component = design.insert_file(resolved, import_options=import_options)
        app_context.command_history.append(
            f"component = design.insert_file({str(resolved)!r}, import_options=import_options)"
        )
        body_count = len(component.get_all_bodies())
        logger.info(f"file_io import inserted {resolved}")
        return (
            f"Inserted '{resolved.name}' into design '{design.name}' as component "
            f"'{component.name}' ({body_count} bodies)."
        )
    except Exception as e:
        logger.error(f"file_io import failed: {e}")
        return f"Error importing '{file_path}': {e}"


@app.tool()
def run_script_file(
    ctx: Context, file_path: str, args: dict[str, str] | None = None
) -> str | dict[str, str]:
    """Run an existing Discovery/SpaceClaim scripting API file on the geometry backend.

    Use this tool when the user asks to run, execute, or play back a script file that
    already exists on disk (for example "run C:/scripts/make_flange.py", "execute my
    SpaceClaim script", or "replay this .scscript").

    When NOT to use this tool: to execute Python code you are writing yourself, use
    ``run_python_code`` instead -- that tool runs the PyAnsys Geometry API
    (``instance``, ``design``, ...) in a persistent session, while this tool runs a
    different language surface entirely. To load a CAD/geometry file (``.scdocx``,
    ``.step``, ``.iges``, ``.x_t``, ...), use ``file_io`` with ``operation="import"``. Never write a
    temporary script file just to run a few statements. Choose ``run_python_code`` instead.

    Script language: the file must be written against the Discovery/SpaceClaim scripting
    API, not the PyAnsys Geometry API. PyAnsys Geometry objects (``Modeler``, ``Sketch``,
    ``instance``, ``design``) are NOT available inside the script, and script variables do not leak
    into the ``run_python_code`` session (or vice versa).

    Passing arguments: ``args`` values must all be strings. The script receives them as a
    dictionary of strings named ``argsDict`` and is responsible for converting them, for
    example ``radius = MM(int(argsDict["radius"]))``. Pass ``{"radius": "1"}``, never
    ``{"radius": 1}``. Omit ``args`` when the script takes no arguments.

    Returning values: to get values back, the script must assign a dictionary named
    ``result``, for example ``result = {"numBodies": numBodies}``. A script that does not
    define ``result`` returns an empty dictionary even though it ran successfully.

    Side effects: the script may create or modify the active design on the backend. Those
    changes are not mirrored into this server's in-process design state or command
    history, so after a script that edits geometry, refresh your view with
    ``get_design_info``, ``list_entities``, or ``get_screenshot`` before relying on
    previously reported names, IDs, or counts.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    file_path : str
        Path to the script file, including its extension. Must be readable by the
        machine running this MCP server. Use an absolute path when possible, since
        relative paths are resolved against the server's working directory.
    args : dict[str, str], default: None
        String-valued arguments exposed to the script as ``argsDict``. Default ``None``.

    Returns
    -------
    str | dict[str, str]
        On success, the script's ``result`` dictionary with string values (empty if the
        script defined no ``result``). On failure, a plain string message.
        Check the returned type: a ``str`` always means the script did not run, and the
        message should be reported to the user rather than retried unchanged.

    """
    from pathlib import Path

    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot run script file."

    resolved = Path(file_path).resolve()
    if not resolved.exists():
        return f"File not found: {resolved}"

    try:
        return app_context.product_instance.run_script_file(resolved, args)[0]

    except Exception as e:
        logger.error(f"run_script_file failed: {e}")
        return f"Error running script file '{file_path}': {e}"
