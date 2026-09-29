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


async def test_run_python_code_not_connected(ctx, execute_mock, monkeypatch):
    """Test that no code is executed when the product backend is not connected."""
    # The app context is session scoped, so monkeypatch restores it for the next test.
    monkeypatch.setattr(ctx.fastmcp._lifespan_result, "product_instance", None)

    result = json.loads(await run_python_code(ctx, "print(1)"))

    assert result["success"] is False
    assert result["error"] == "The product backend is not connected."
    execute_mock.assert_not_awaited()


async def test_run_python_code_success(ctx, execute_mock, connect_mock):
    """Test that a successful execution is forwarded and appended to the command history."""
    execute_mock.return_value = json.dumps(
        {"success": True, "stdout": "42\n", "stderr": "", "message": "ok"}
    )

    result = json.loads(await run_python_code(ctx, "print(42)"))

    assert result["success"] is True
    assert result["stdout"] == "42\n"
    connect_mock.assert_called_once_with(ctx)
    execute_mock.assert_awaited_once_with(ctx, "print(42)")
    assert "print(42)" in get_command_history(ctx)


async def test_run_python_code_failure_not_recorded(ctx, execute_mock, connect_mock):
    """Test that a failed execution is returned as-is and left out of the command history."""
    execute_mock.return_value = json.dumps(
        {"success": False, "stdout": "", "stderr": "boom", "error": "NameError: boom"}
    )

    result = json.loads(await run_python_code(ctx, "boom"))

    assert result["success"] is False
    assert result["error"] == "NameError: boom"
    assert "boom" not in get_command_history(ctx)


async def test_run_python_code_reuses_connected_session(ctx, connect_mock, monkeypatch):
    """Test that no reconnection is attempted when the session already holds a Modeler."""
    session = ctx.request_context.lifespan_context.python_session
    monkeypatch.setitem(session.metadata, "instance", MagicMock())

    result = json.loads(await run_python_code(ctx, "print(1)"))

    assert result["success"] is True
    connect_mock.assert_not_called()


@pytest.mark.parametrize(
    ("outcome", "expected_error"),
    [
        (
            RuntimeError("no route to service"),
            "Failed to connect to the modeler in the persistent Python session:"
            " no route to service",
        ),
        (None, "Failed to connect to the modeler in the persistent Python session."),
        (
            "No Modeler instance available in lifespan context.",
            "No Modeler instance available in lifespan context.",
        ),
    ],
    ids=["raises", "returns_none", "returns_message"],
)
async def test_run_python_code_connection_failure(
    ctx, execute_mock, connect_mock, outcome, expected_error
):
    """Test that a failed connection aborts the execution instead of running the code."""
    if isinstance(outcome, Exception):
        connect_mock.side_effect = outcome
    else:
        connect_mock.return_value = outcome

    result = json.loads(await run_python_code(ctx, "print(1)"))

    assert result["success"] is False
    assert result["error"] == expected_error
    execute_mock.assert_not_awaited()
