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

"""MCP session tools for PyAnsys Geometry MCP server.

Each function decorated with ``@app.tool()`` is exposed as an MCP tool.
The ``ctx`` parameter provides access to the application context (and thus
to the live product instance and command history).

How to add a tool
-----------------
1. Define a Python function with type-annotated parameters.
2. Add a NumPy-style docstring — the summary line becomes the tool description
   visible to the AI assistant.
3. Decorate it with ``@app.tool()``.
4. Access the product instance via::

       app_context = ctx.fastmcp._lifespan_result
       instance = app_context.product_instance

Notes
-----
Import this module in ``__main__.py`` (already done) to register all tools
with the server before it starts.

"""

from ansys.common.mcp.logging_config import get_logger
import ansys.common.mcp.tools as shared_tools
from fastmcp.server import Context

from ansys.geometry.mcp import app
from ansys.geometry.mcp.misc.auxiliary import get_geometry_ctx

logger = get_logger(__name__)


@app.tool()
def get_command_history(ctx: Context) -> list[str]:
    """Get the history of commands executed in the product backend.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).

    Returns
    -------
    list of str
        List of command strings that have been executed.

    """
    app_context = get_geometry_ctx(ctx)
    return app_context.command_history


@app.tool()
def get_transcript(ctx: Context) -> str:
    """Get a transcript of the current session, including all executed commands.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).

    Returns
    -------
    str
        A formatted transcript of the session.

    """
    app_context = get_geometry_ctx(ctx)
    commands = "\n".join(app_context.command_history)

    # Format Python script using import sorting and black-style formatting
    try:
        import black
        import isort

        sorted_commands = isort.code(commands)
        formatted_commands = black.format_str(sorted_commands, mode=black.Mode())
        return formatted_commands if formatted_commands else "No commands executed yet."
    except (ImportError, black.InvalidInput):
        return commands if commands else "No commands executed yet."


@app.tool()
def get_product_status(ctx: Context) -> str:
    """Return the current status of the product backend.

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
async def run_python_code(ctx: Context, code: str) -> str:
    """Execute arbitrary Python code in the product backend's Python session. Session is persistent - variables inside remain available.

    Predefined variables : ``instance`` -> is the instance of ansys.geometry.core.Modeler()
    that should be used.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    code : str
        The Python code to execute.

    Returns
    -------
    str
        The output or result of the executed code, or an error message if execution fails.

    """
    import json

    result = await shared_tools.execute_python_code(ctx, code, timeout=60)
    try:
        parsed = json.loads(result)
        if parsed.get("success"):
            app_context = get_geometry_ctx(ctx)
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
def export_design_to(ctx: Context, file_format: str, folder: str | None = None) -> str:
    """Export/Save the current active design to a specified format.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    file_format : str
        The format to export the design to. Options are 'fmd', 'step', 'iges', 'scdocx',
        'disco', 'parasolid_text', 'parasolid_bin'.
    folder : str, optional
        Folder on disk to save the design. If not provided, the file
        is saved in the current working directory.

    Returns
    -------
    str
        The path to the saved design file, or an error message if export fails.

    """
    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot export design."

    try:
        from ansys.geometry.core.designer import DesignFileFormat

        design = app_context.product_instance.get_active_design()
        # Depending on format... Use DesignFileFormat enum
        if file_format.lower() == DesignFileFormat.FMD.name.lower():
            saved_path = design.export_to_fmd(folder)
            app_context.command_history.append(f"design.export_to_fmd({folder!r})")
        elif file_format.lower() == DesignFileFormat.STEP.name.lower():
            saved_path = design.export_to_step(folder)
            app_context.command_history.append(f"design.export_to_step({folder!r})")
        elif file_format.lower() == DesignFileFormat.IGES.name.lower():
            saved_path = design.export_to_iges(folder)
            app_context.command_history.append(f"design.export_to_iges({folder!r})")
        elif file_format.lower() == DesignFileFormat.SCDOCX.name.lower():
            saved_path = design.export_to_scdocx(folder)
            app_context.command_history.append(f"design.export_to_scdocx({folder!r})")
        elif file_format.lower() == DesignFileFormat.DISCO.name.lower():
            saved_path = design.export_to_disco(folder)
            app_context.command_history.append(f"design.export_to_disco({folder!r})")
        elif file_format.lower() == DesignFileFormat.PARASOLID_TEXT.name.lower():
            saved_path = design.export_to_parasolid_text(folder)
            app_context.command_history.append(f"design.export_to_parasolid_text({folder!r})")
        elif file_format.lower() == DesignFileFormat.PARASOLID_BIN.name.lower():
            saved_path = design.export_to_parasolid_bin(folder)
            app_context.command_history.append(f"design.export_to_parasolid_bin({folder!r})")
        else:
            return f"Unsupported format '{file_format}'. Supported formats are:"
        " fmd, step, iges, scdocx, disco, parasolid_text, parasolid_bin."

        logger.info(f"export_design_to called, saved to {saved_path}")
        return f"Design exported to {file_format.upper()} file: {saved_path}"
    except Exception as e:
        logger.error(f"export_design_to failed: {e}")
        return f"Error exporting design to {file_format.upper()}: {e}"


@app.tool()
def import_geometry_file(
    ctx: Context,
    file_path: str,
    mode: str = "open",
    import_names: bool = False,
    import_curves: bool = False,
    import_coordinate_systems: bool = False,
    import_named_selections: bool = True,
    cleanup_bodies: bool = False,
) -> str:
    """Import, open, or load a geometry file from disk into the product backend.

    Use this tool when asked to import, open, load, or insert a CAD or geometry file.
    Supported extensions include 'scdocx', 'dsco', 'pmdb', 'step', 'iges', 'x_t', 'xmt_txt',
    'stride', and reader formats such as CATIA, Creo, NX, JT, SOLIDWORKS, Solid Edge,
    Inventor, Rhino, and AutoCAD.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    file_path : str
        Path on disk of the file to import. The extension must be included. For a shattered
        assembly, give the path of the assembly file; the files it references in the same
        folder are included automatically.
    mode : str, optional
        How to import the file. Use 'open' (default) to close the active design and open the
        file as a new design. Use 'insert' to add the file into the current active design as
        a new component.
    import_names : bool, optional
        Whether to import the names of bodies and curves. Default is False.
    import_curves : bool, optional
        Whether to import curves. Default is False.
    import_coordinate_systems : bool, optional
        Whether to import coordinate systems. Default is False.
    import_named_selections : bool, optional
        Whether to import named selections. Default is True.
    cleanup_bodies : bool, optional
        Whether to simplify geometry and clean up topology on import. Default is False.

    Returns
    -------
    str
        Result message describing the imported geometry, or an error message if the
        import fails.

    """
    from pathlib import Path

    from ansys.geometry.core.misc import ImportOptions

    app_context = get_geometry_ctx(ctx)

    if app_context.product_instance is None:
        return "Product backend is not connected. Cannot import geometry file."

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
            logger.info(f"import_geometry_file opened {resolved}")
            return (
                f"Imported '{resolved.name}' into new design '{design.name}' ({body_count} bodies)."
            )

        design = app_context.product_instance.get_active_design()
        component = design.insert_file(resolved, import_options=import_options)
        app_context.command_history.append(
            f"component = design.insert_file({str(resolved)!r}, import_options=import_options)"
        )
        body_count = len(component.get_all_bodies())
        logger.info(f"import_geometry_file inserted {resolved}")
        return (
            f"Inserted '{resolved.name}' into design '{design.name}' as component "
            f"'{component.name}' ({body_count} bodies)."
        )
    except Exception as e:
        logger.error(f"import_geometry_file failed: {e}")
        return f"Error importing '{file_path}': {e}"
