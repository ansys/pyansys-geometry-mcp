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
from unittest.mock import AsyncMock, MagicMock

import pytest

from ansys.geometry.mcp.tools import (
    create_design,
    file_operation,
    get_backend_status,
    get_design_info,
    get_session_script,
    run_iron_python,
    run_python,
    session_tools,
)

from .conftest import FILES_DIR, create_box


def test_get_backend_status_tool(ctx):
    """Test getting the product status."""
    status = get_backend_status(ctx)
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


def test_file_operation_export(ctx, tmp_path_factory: pytest.TempPathFactory):
    """Test exporting the active design to scdocx format."""
    design_name = "test_export_design_001"
    create_design(ctx, design_name)

    # Define the location and expected file location
    location = tmp_path_factory.mktemp("test_export_to_scdocx")
    file_location = location / f"{design_name}.scdocx"

    result = file_operation(
        ctx, operation="export", file_format="scdocx", folder=str(file_location)
    )
    assert "Design exported to SCDOCX file:" in result
    assert file_location.is_file()
    assert str(file_location) in result


@pytest.mark.parametrize(
    ("file_format", "extension"),
    [
        ("fmd", "fmd"),
        ("step", "stp"),
        ("iges", "igs"),
        ("dsco", "dsco"),
        ("parasolid_text", "x_t"),
        ("parasolid_bin", "x_b"),
    ],
)
def test_file_operation_export_formats(
    ctx, file_format: str, extension: str, tmp_path_factory: pytest.TempPathFactory
):
    """Test exporting the active design to each supported file format."""
    design_name = f"test_export_{file_format}_001"
    create_design(ctx, design_name)
    create_box(ctx, name=f"{file_format}_box", width=1.0, depth=1.0, height=1.0)

    # Define the location and expected file location
    location = tmp_path_factory.mktemp(f"test_export_to_{file_format}")
    file_location = location / f"custom_name.{extension}"
    result = file_io(ctx, operation="export", file_format=file_format, file_path=str(file_location))

    assert f"Design exported to {file_format.upper()} file:" in result
    assert file_location.exists()


def test_file_operation_export_path_conflicts():
    """Test that an explicit export path and a folder cannot be combined."""
    mock_ctx = MagicMock()
    result = file_io(
        mock_ctx, operation="export", file_format="dsco", file_path="custom.dsco", folder="other"
    )
    assert "file_path" in result and "folder" in result
    mock_ctx.fastmcp._lifespan_result.product_instance.get_active_design.assert_not_called()


def test_file_operation_export_missing_output(tmp_path):
    """Test that a backend success without the requested file is reported as an error."""
    mock_ctx = MagicMock()
    file_location = tmp_path / "custom.step"
    result = file_io(mock_ctx, operation="export", file_format="step", file_path=str(file_location))
    assert "did not create the requested export file" in result
    assert str(file_location) in result


def test_file_operation_export_dsco_folder(ctx, tmp_path):
    """Test exporting a design-named .dsco file to a directory."""
    design_name = "test_folder_dsco"
    create_design(ctx, design_name)
    create_box(ctx, name="box", width=1.0, depth=1.0, height=1.0)
    file_location = tmp_path / f"{design_name}.dsco"

    result = file_io(ctx, operation="export", file_format="dsco", folder=str(tmp_path))
    assert "Design exported to DSCO file:" in result
    assert file_location.is_file()
    assert str(file_location) in result


def test_file_operation_export_unsupported_format(ctx, tmp_path_factory: pytest.TempPathFactory):
    """Test that an unsupported format returns an error message."""
    design_name = "test_export_unsupported_001"
    create_design(ctx, design_name)

    # Define the location and expected file location
    location = tmp_path_factory.mktemp("test_export_to_scdocx")
    file_location = location / f"{design_name}"

    result = file_operation(
        ctx, operation="export", file_format="xyz_unsupported", folder=str(file_location)
    )
    assert "Unsupported format" in result


def test_file_operation_export_not_connected():
    """Test that exporting when not connected returns an error message."""
    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result.product_instance = None
    result = file_operation(mock_ctx, operation="export", file_format="scdocx")
    assert "not connected" in result


def test_get_session_script(ctx):
    """Test that the session script contains setup and newly executed commands."""
    initial_script = get_session_script(ctx)
    assert isinstance(initial_script, str)
    assert "selection_registry = {}" in initial_script
    assert "instance = " in initial_script

    create_design(ctx, "test_get_session_script_001")
    script = get_session_script(ctx)
    assert len(script) > len(initial_script)
    assert script.count("test_get_session_script_001") == 1
    assert 'design = instance.create_design("test_get_session_script_001")' in script


def _export_box_design(
    ctx, tmp_path_factory: pytest.TempPathFactory, name: str, fmt: str = "scdocx"
):
    """Create a one-box design, export it, and return the path of the exported file."""
    create_design(ctx, name)
    create_box(ctx, name=f"{name}_box", width=1.0, depth=1.0, height=1.0)

    location = tmp_path_factory.mktemp(name)
    result = file_operation(ctx, operation="export", file_format=fmt, folder=str(location))
    # The written extension is format-dependent (e.g. STEP writes .stp), so read it back.
    return Path(result.split("file: ", 1)[1])


@pytest.mark.parametrize("file_format", ["scdocx", "step"])
def test_file_operation_import_open(
    ctx, file_format: str, tmp_path_factory: pytest.TempPathFactory
):
    """Test round-tripping a design: export it to disk and open it again."""
    exported = _export_box_design(
        ctx, tmp_path_factory, f"test_import_open_{file_format}", file_format
    )
    assert exported.exists()

    result = file_operation(ctx, operation="import", file_path=str(exported), mode="open")
    assert "Imported" in result
    assert exported.name in result
    assert "1 bodies" in result
    assert "open_file(" in get_session_script(ctx)


def test_file_operation_import_insert(ctx, tmp_path_factory: pytest.TempPathFactory):
    """Test inserting an exported file into an existing design as a new component."""
    exported = _export_box_design(ctx, tmp_path_factory, "test_import_insert")

    create_design(ctx, "test_import_insert_host")
    result = file_operation(ctx, operation="import", file_path=str(exported), mode="insert")
    assert "Inserted" in result
    assert "test_import_insert_host" in result
    assert "insert_file(" in get_session_script(ctx)


def test_file_operation_import_with_options(ctx, tmp_path_factory: pytest.TempPathFactory):
    """Test importing with non-default import options."""
    exported = _export_box_design(ctx, tmp_path_factory, "test_import_options")

    result = file_operation(
        ctx,
        operation="import",
        file_path=str(exported),
        import_names=True,
        import_curves=True,
        import_coordinate_systems=True,
        import_named_selections=False,
        cleanup_bodies=True,
    )
    assert "Imported" in result


def test_file_operation_import_errors(tmp_path_factory: pytest.TempPathFactory):
    """Test the import error paths: disconnected, bad mode, bad path, and backend failure."""
    tmp_dir = tmp_path_factory.mktemp("test_import_errors")

    # Not connected
    disconnected_ctx = MagicMock()
    disconnected_ctx.fastmcp._lifespan_result.product_instance = None
    assert "not connected" in file_operation(
        disconnected_ctx, operation="import", file_path="anything.scdocx"
    )

    mock_ctx = MagicMock()

    # Unsupported mode
    assert "Unsupported mode" in file_operation(
        mock_ctx, operation="import", file_path="anything.scdocx", mode="merge"
    )

    # Nonexistent path
    assert "File not found" in file_operation(
        mock_ctx, operation="import", file_path=str(tmp_dir / "nope.scdocx")
    )

    # Directory instead of a file
    assert "directory" in file_operation(mock_ctx, operation="import", file_path=str(tmp_dir))

    # Backend failure
    file = tmp_dir / "broken.scdocx"
    file.write_bytes(b"not a real design")
    mock_ctx.fastmcp._lifespan_result.product_instance.open_file.side_effect = RuntimeError("boom")
    result = file_operation(mock_ctx, operation="import", file_path=str(file))
    assert "Error importing" in result
    assert "boom" in result


def test_run_iron_python(ctx):
    """Test that running a script file with success."""
    result = run_iron_python(ctx, Path(FILES_DIR, "simple_script.py"))
    assert "design" in result
    assert "design_body" in result

    # Test passing in args
    create_design(ctx, "NewDesign")
    create_box(ctx, "Box", 1, 1, 1)
    result = run_iron_python(ctx, Path(FILES_DIR, "integrated_script.py"), {"radius": "1"})
    assert int(result["numBodies"]) == 2


def test_run_iron_python_text(ctx):
    """Test executing script text with arguments on the geometry backend."""
    result = run_script_file(
        ctx, script='result = {"answer": argsDict["answer"]}', args={"answer": "42"}
    )
    assert result == {"answer": "42"}


def test_iron_python_text_dispatch():
    """Test script text and arguments are passed through to the backend."""
    mock_ctx = MagicMock()
    modeler = mock_ctx.fastmcp._lifespan_result.product_instance
    modeler.run_script.return_value = ({"answer": "42"}, None)
    script = 'result = {"answer": argsDict["answer"]}\n'
    args = {"answer": "42"}

    assert run_script_file(mock_ctx, script=script, args=args) == {"answer": "42"}
    modeler.run_script.assert_called_once_with(script, args)
    modeler.run_script_file.assert_not_called()


@pytest.mark.parametrize(
    ("file_path", "script", "message"),
    [
        (None, None, "exactly one"),
        ("test.py", "print(1)", "exactly one"),
        (None, "  \n", "must not be empty"),
        ("", None, "must not be empty"),
    ],
)
def test_run_iron_python_invalid_inputs(file_path, script, message):
    """Test ambiguous or empty inputs are rejected without executing anything."""
    mock_ctx = MagicMock()
    modeler = mock_ctx.fastmcp._lifespan_result.product_instance

    assert message in run_script_file(mock_ctx, file_path=file_path, script=script)
    modeler.run_script.assert_not_called()
    modeler.run_script_file.assert_not_called()


def test_run_iron_python_text_error():
    """Test backend errors are reported for script text."""
    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result.product_instance.run_script.side_effect = RuntimeError("boom")
    assert "boom" in run_script_file(mock_ctx, script="print(1)")


def test_run_iron_python_dispatch(tmp_path):
    """Test file execution remains available with arguments."""
    mock_ctx = MagicMock()
    modeler = mock_ctx.fastmcp._lifespan_result.product_instance
    modeler.run_script_file.return_value = ({"answer": "42"}, None)
    script_file = tmp_path / "script.py"
    script_file.write_text("pass", encoding="utf-8")
    args = {"answer": "42"}

    assert run_script_file(mock_ctx, script_file, args) == {"answer": "42"}
    modeler.run_script_file.assert_called_once_with(script_file.resolve(), args)
    modeler.run_script.assert_not_called()


def test_run_iron_python_errors(ctx):
    """Test that running a nonexistent script file returns an error message."""
    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result.product_instance = None
    result = run_iron_python(mock_ctx, "anything.py")
    assert "not connected" in result

    result = run_iron_python(ctx, Path(FILES_DIR, "nonexistent.py"))
    assert "File not found" in result

    mock_ctx = MagicMock()
    mock_ctx.fastmcp._lifespan_result.product_instance.run_script_file.side_effect = RuntimeError(
        "boom"
    )

    result = run_iron_python(mock_ctx, Path(FILES_DIR, "simple_script.py"))
    assert "Error running script file" in result
    assert "boom" in result


async def test_run_python_not_connected(ctx, execute_mock, monkeypatch):
    """Test that no code is executed when the product backend is not connected."""
    # The app context is session scoped, so monkeypatch restores it for the next test.
    monkeypatch.setattr(ctx.fastmcp._lifespan_result, "product_instance", None)

    result = json.loads(await run_python(ctx, "print(1)"))

    assert result["success"] is False
    assert result["error"] == "The product backend is not connected."
    execute_mock.assert_not_called()


async def test_success_refreshes_after_execution(ctx, monkeypatch):
    app_context = ctx.fastmcp._lifespan_result
    monkeypatch.setattr(app_context, "product_instance", MagicMock())
    monkeypatch.setattr(app_context, "command_history", [])
    monkeypatch.setitem(app_context.python_session.metadata, "instance", MagicMock())
    cached_design = app_context.product_instance.get_active_design.return_value
    cached_design.bodies = []
    events = []
    result = json.dumps({"success": True, "stdout": "box\n", "stderr": "", "error": None})

    async def execute(*args, **kwargs):
        events.append("execute")
        assert cached_design.bodies == []
        return result

    def refresh():
        events.append("refresh")
        cached_design.bodies = ["box"]
        return cached_design

    monkeypatch.setattr(session_tools.shared_tools, "execute_python_code", execute)
    app_context.product_instance.get_active_design.side_effect = refresh

    returned = await session_tools.run_python(ctx, "create_box()")

    assert returned == result
    assert events == ["execute", "refresh"]
    assert cached_design.bodies == ["box"]
    assert app_context.command_history == ["create_box()"]


@pytest.mark.parametrize(
    "result",
    [
        json.dumps({"success": False, "error": "Execution failed"}),
        "invalid JSON",
        "null",
    ],
)
async def test_unsuccessful_execution_does_not_refresh(ctx, monkeypatch, result):
    app_context = ctx.fastmcp._lifespan_result
    monkeypatch.setattr(app_context, "product_instance", MagicMock())
    monkeypatch.setattr(app_context, "command_history", [])
    monkeypatch.setitem(app_context.python_session.metadata, "instance", MagicMock())
    execute = AsyncMock(return_value=result)
    monkeypatch.setattr(session_tools.shared_tools, "execute_python_code", execute)

    assert await session_tools.run_python(ctx, "code") == result
    app_context.product_instance.get_active_design.assert_not_called()
    assert app_context.command_history == []


async def test_refresh_failure_preserves_execution_success(ctx, monkeypatch, caplog):
    execution_result = {
        "success": True,
        "stdout": "box created\n",
        "stderr": "",
        "error": None,
    }
    execute = AsyncMock(return_value=json.dumps(execution_result))
    monkeypatch.setattr(session_tools.shared_tools, "execute_python_code", execute)
    app_context = ctx.fastmcp._lifespan_result
    monkeypatch.setattr(app_context, "product_instance", MagicMock())
    monkeypatch.setattr(app_context, "command_history", [])
    monkeypatch.setitem(app_context.python_session.metadata, "instance", MagicMock())
    app_context.product_instance.get_active_design.side_effect = RuntimeError("service unavailable")

    result = json.loads(await session_tools.run_python(ctx, "create_box()"))

    refresh_error = result.pop("refresh_error")
    assert result == execution_result
    assert "service unavailable" in refresh_error
    assert refresh_error in caplog.text
    assert app_context.command_history == ["create_box()"]
    execute.assert_awaited_once()
    app_context.product_instance.get_active_design.assert_called_once_with()


async def test_run_python_success(ctx, execute_mock, connect_mock):
    """Test that a successful execution is forwarded and appended to the command history."""
    execute_mock.return_value = {
        "success": True,
        "stdout": "42\n",
        "stderr": "",
        "message": "ok",
    }

    result = json.loads(await run_python(ctx, "print(42)"))

    print(result)
    assert result["success"] is True
    assert result["stdout"] == "42\n"
    connect_mock.assert_called_once_with(ctx)
    execute_mock.assert_called_once_with("print(42)", timeout=300, no_output_timeout=300)
    assert "print(42)" in get_session_script(ctx)


async def test_run_python_failure_not_recorded(ctx, execute_mock, connect_mock):
    """Test that a failed execution is returned as-is and left out of the command history."""
    execute_mock.return_value = {
        "success": False,
        "stdout": "",
        "stderr": "boom",
        "error": "NameError: boom",
    }

    result = json.loads(await run_python(ctx, "boom"))

    assert result["success"] is False
    assert result["error"] == "NameError: boom"
    assert "boom" not in get_session_script(ctx)


async def test_run_python_reuses_connected_session(ctx, execute_mock, connect_mock, monkeypatch):
    """Test that no reconnection is attempted when the session already holds a Modeler."""
    session = ctx.request_context.lifespan_context.python_session
    monkeypatch.setitem(session.metadata, "instance", MagicMock())

    result = json.loads(await run_python(ctx, "print(1)"))

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
async def test_run_python_connection_failure(
    ctx, execute_mock, connect_mock, outcome, expected_error
):
    """Test that a failed connection aborts the execution instead of running the code."""
    if isinstance(outcome, Exception):
        connect_mock.side_effect = outcome
    else:
        connect_mock.return_value = outcome

    result = json.loads(await run_python(ctx, "print(1)"))

    assert result["success"] is False
    assert result["error"] == expected_error
    execute_mock.assert_not_called()
