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

"""Unit tests for the session tools."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ansys.geometry.mcp.tools import (
    create_box,
    create_design,
    export_design_to,
    get_command_history,
    get_design_info,
    get_product_status,
    get_transcript,
    import_geometry_file,
    run_python_code,
    run_script_file,
)

from .conftest import FILES_DIR


def test_get_product_status_tool(ctx):
    """Test getting the product status."""
    status = get_product_status(ctx)
    assert "Product backend is connected:" in status


def test_create_design(ctx):
    """Test creating a new design."""
    result = create_design(ctx, "test_create_design_001")
    assert "test_create_design_001" in result
    assert "created successfully" in result


def test_get_design_info(ctx):
    """Test retrieving information about the active design."""
    create_design(ctx, "test_get_design_info_001")
    result = get_design_info(ctx)
    assert isinstance(result, str)
    assert len(result) > 0


def test_export_design_to(ctx, tmp_path_factory: pytest.TempPathFactory):
    """Test exporting the active design to scdocx format."""
    design_name = "test_export_design_001"
    create_design(ctx, design_name)

    # Define the location and expected file location
    location = tmp_path_factory.mktemp("test_export_to_scdocx")
    file_location = location / f"{design_name}.scdocx"

    result = export_design_to(ctx, file_format="scdocx", folder=str(file_location))
    assert "Design exported to SCDOCX file:" in result


@pytest.mark.parametrize(
    "file_format",
    ["fmd", "step", "iges", "disco", "parasolid_text", "parasolid_bin"],
)
def test_export_design_to_formats(ctx, file_format: str, tmp_path_factory: pytest.TempPathFactory):
    """Test exporting the active design to each supported file format."""
    design_name = f"test_export_{file_format}_001"
    create_design(ctx, design_name)
    create_box(ctx, name=f"{file_format}_box", width=1.0, depth=1.0, height=1.0)

    # Define the location and expected file location
    location = tmp_path_factory.mktemp(f"test_export_to_{file_format}")
    file_location = location / f"{design_name}.{file_format}"
    result = export_design_to(ctx, file_format=file_format, folder=str(file_location))

    assert f"Design exported to {file_format.upper()} file:" in result
    assert file_location.exists()


def test_export_design_to_unsupported_format(ctx, tmp_path_factory: pytest.TempPathFactory):
    """Test that an unsupported format returns an error message."""
    design_name = "test_export_unsupported_001"
    create_design(ctx, design_name)

    # Define the location and expected file location
    location = tmp_path_factory.mktemp("test_export_to_scdocx")
    file_location = location / f"{design_name}"

    result = export_design_to(ctx, file_format="xyz_unsupported", folder=str(file_location))
    assert "Unsupported format" in result


def test_export_design_to_not_connected():
    """Test that exporting when not connected returns an error message."""
    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result.product_instance = None
    result = export_design_to(mock_ctx, file_format="scdocx")
    assert "not connected" in result


def test_get_command_history(ctx):
    """Test that command history returns a list of strings after executing commands."""
    result = get_command_history(ctx)
    assert len(result) == 3
    assert result[0] == "selection_registry = {}"

    create_design(ctx, "test_get_command_history_001")
    result = get_command_history(ctx)
    assert len(result) == 4

    create_box(ctx, name="test_box", width=1.0, depth=1.0, height=1.0)
    result = get_command_history(ctx)
    assert len(result) == 11


def test_get_transcript(ctx):
    """Test that the transcript contains the correct commands after each operation."""
    create_design(ctx, "test_transcript_001")
    result = get_transcript(ctx)
    assert result.count("test_transcript_001") == 1
    assert 'design = instance.create_design("test_transcript_001")' in result

    create_box(ctx, name="transcript_box", width=1.0, depth=1.0, height=1.0)
    result = get_transcript(ctx)
    assert result.count("transcript_box") == 1
    assert "sketch.box(center=Point2D([0.0, 0.0]), width=1.0, height=1.0)" in result


def _export_box_design(
    ctx, tmp_path_factory: pytest.TempPathFactory, name: str, fmt: str = "scdocx"
):
    """Create a one-box design, export it, and return the path of the exported file."""
    create_design(ctx, name)
    create_box(ctx, name=f"{name}_box", width=1.0, depth=1.0, height=1.0)

    location = tmp_path_factory.mktemp(name)
    result = export_design_to(ctx, file_format=fmt, folder=str(location))
    # The written extension is format-dependent (e.g. STEP writes .stp), so read it back.
    return Path(result.split("file: ", 1)[1])


@pytest.mark.parametrize("file_format", ["scdocx", "step"])
def test_import_geometry_file_open(ctx, file_format: str, tmp_path_factory: pytest.TempPathFactory):
    """Test round-tripping a design: export it to disk and open it again."""
    exported = _export_box_design(
        ctx, tmp_path_factory, f"test_import_open_{file_format}", file_format
    )
    assert exported.exists()

    result = import_geometry_file(ctx, file_path=str(exported), mode="open")
    assert "Imported" in result
    assert exported.name in result
    assert "1 bodies" in result
    assert "open_file(" in get_command_history(ctx)[-1]


def test_import_geometry_file_insert(ctx, tmp_path_factory: pytest.TempPathFactory):
    """Test inserting an exported file into an existing design as a new component."""
    exported = _export_box_design(ctx, tmp_path_factory, "test_import_insert")

    create_design(ctx, "test_import_insert_host")
    result = import_geometry_file(ctx, file_path=str(exported), mode="insert")
    assert "Inserted" in result
    assert "test_import_insert_host" in result
    assert "insert_file(" in get_command_history(ctx)[-1]


def test_import_geometry_file_with_options(ctx, tmp_path_factory: pytest.TempPathFactory):
    """Test importing with non-default import options."""
    exported = _export_box_design(ctx, tmp_path_factory, "test_import_options")

    result = import_geometry_file(
        ctx,
        file_path=str(exported),
        import_names=True,
        import_curves=True,
        import_coordinate_systems=True,
        import_named_selections=False,
        cleanup_bodies=True,
    )
    assert "Imported" in result


def test_import_geometry_file_errors(tmp_path_factory: pytest.TempPathFactory):
    """Test the import error paths: disconnected, bad mode, bad path, and backend failure."""
    tmp_dir = tmp_path_factory.mktemp("test_import_errors")

    # Not connected
    disconnected_ctx = MagicMock()
    disconnected_ctx.fastmcp._lifespan_result.product_instance = None
    assert "not connected" in import_geometry_file(disconnected_ctx, file_path="anything.scdocx")

    mock_ctx = MagicMock()

    # Unsupported mode
    assert "Unsupported mode" in import_geometry_file(
        mock_ctx, file_path="anything.scdocx", mode="merge"
    )

    # Nonexistent path
    assert "File not found" in import_geometry_file(
        mock_ctx, file_path=str(tmp_dir / "nope.scdocx")
    )

    # Directory instead of a file
    assert "directory" in import_geometry_file(mock_ctx, file_path=str(tmp_dir))

    # Backend failure
    file = tmp_dir / "broken.scdocx"
    file.write_bytes(b"not a real design")
    mock_ctx.fastmcp._lifespan_result.product_instance.open_file.side_effect = RuntimeError("boom")
    result = import_geometry_file(mock_ctx, file_path=str(file))
    assert "Error importing" in result
    assert "boom" in result


def test_run_script_file(ctx):
    """Test that running a script file with success."""
    result = run_script_file(ctx, Path(FILES_DIR, "simple_script.py"))
    assert "design" in result
    assert "design_body" in result

    # Test passing in args
    create_design(ctx, "NewDesign")
    create_box(ctx, "Box", 1, 1, 1)
    result = run_script_file(ctx, Path(FILES_DIR, "integrated_script.py"), {"radius": "1"})
    assert int(result["numBodies"]) == 2


def test_run_script_file_errors(ctx):
    """Test that running a nonexistent script file returns an error message."""
    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result.product_instance = None
    result = run_script_file(mock_ctx, "anything.py")
    assert "not connected" in result

    result = run_script_file(ctx, Path(FILES_DIR, "nonexistent.py"))
    assert "File not found" in result

    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result.product_instance.run_script_file.side_effect = RuntimeError(
        "boom"
    )

    result = run_script_file(mock_ctx, Path(FILES_DIR, "simple_script.py"))
    assert "Error running script file" in result
    assert "boom" in result


async def test_run_python_code_success(ctx):
    """Test persistence and history bookkeeping when the code succeeds."""
    app_context = ctx.fastmcp._lifespan_result
    app_context.python_globals.pop("answer", None)
    baseline = list(app_context.command_history)

    result = json.loads(await run_python_code(ctx, "answer = 6 * 7\nprint(answer)"))
    assert result["success"] is True
    assert "42" in result["stdout"]
    assert app_context.command_history == [*baseline, "answer = 6 * 7\nprint(answer)"]

    # The namespace is persistent, so earlier variables survive.
    result = json.loads(await run_python_code(ctx, "print(answer * 2)"))
    assert result["success"] is True
    assert "84" in result["stdout"]


async def test_run_python_code_shares_live_objects(ctx):
    """Test that the code runs against the same objects the other tools use."""
    app_context = ctx.fastmcp._lifespan_result

    result = json.loads(await run_python_code(ctx, "print(instance is not None)"))
    assert result["success"] is True
    assert "True" in result["stdout"]
    assert app_context.python_globals["instance"] is app_context.product_instance

    create_design(ctx, "InProcessDesign")
    result = json.loads(await run_python_code(ctx, "print(design.name)"))
    assert result["success"] is True
    assert "InProcessDesign" in result["stdout"]

    # A body created here is immediately visible through the product instance.
    result = json.loads(
        await run_python_code(
            ctx,
            "from ansys.geometry.core.math import Point2D\n"
            "from ansys.geometry.core.misc import Distance\n"
            "from ansys.geometry.core.sketch import Sketch\n"
            "sketch = Sketch()\n"
            "sketch.box(center=Point2D([0, 0]), width=1, height=1)\n"
            "design.extrude_sketch(name='InProcessBody', sketch=sketch, distance=Distance(1))",
        )
    )
    assert result["success"] is True
    bodies = app_context.product_instance.get_active_design().get_all_bodies()
    assert [b.name for b in bodies] == ["InProcessBody"]


async def test_run_python_code_failure_paths(ctx):
    """Test that failures are reported without touching the history or the namespace."""
    app_context = ctx.fastmcp._lifespan_result
    baseline = list(app_context.command_history)

    # Code that raises is reported as a failure and is not recorded.
    result = json.loads(await run_python_code(ctx, "never_defined = 1\nraise ValueError('bad')"))
    assert result["success"] is False
    assert "bad" in result["error"]
    assert "ValueError" in result["error"]
    assert app_context.command_history == baseline

    # Output produced before the exception is still returned.
    result = json.loads(await run_python_code(ctx, "print('partial')\nraise ValueError('bad')"))
    assert result["success"] is False
    assert "partial" in result["stdout"]

    # A disconnected backend is reported instead of executing anything.
    instance = app_context.product_instance
    app_context.product_instance = None
    try:
        result = json.loads(await run_python_code(ctx, "should_not_run = 1"))
    finally:
        app_context.product_instance = instance
    assert result["success"] is False
    assert "not connected" in result["error"]
    assert "should_not_run" not in app_context.python_globals
    assert app_context.command_history == baseline
