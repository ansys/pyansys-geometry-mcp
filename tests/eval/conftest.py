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

"""Fixtures for the opt-in LLM tool-discoverability evaluation."""

import asyncio
import json
import os
from pathlib import Path
import sys

import pytest

from ._harness import AzureConfig, MissingCredentialsError, schemas_by_name, to_openai_tools

#: Attribute on ``pytest.Config`` accumulating the results for the JSON report.
_RESULTS_ATTR = "_llm_eval_results"

#: Seconds allowed for the MCP server to start; it also launches a geometry backend.
_MCP_INIT_TIMEOUT = 300


@pytest.fixture(scope="session", autouse=True)
def _require_llm_eval_opt_in(request):
    """Skip every evaluation test unless ``--run-llm-eval`` was passed."""
    if not request.config.getoption("--run-llm-eval"):
        pytest.skip("LLM evaluation is opt-in; pass --run-llm-eval to run it")


@pytest.fixture(scope="session")
def azure_config(_require_llm_eval_opt_in) -> AzureConfig:
    """Azure OpenAI settings read from the environment."""
    try:
        return AzureConfig.from_env()
    except MissingCredentialsError as err:
        pytest.skip(f"Azure OpenAI configuration is incomplete; missing: {err}")


async def _fetch_tools(args: list[str]):
    """Start the MCP server over stdio and return its advertised tools."""
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "ansys.geometry.mcp", *args],
        env=dict(os.environ),
    )
    async with Client(transport, init_timeout=_MCP_INIT_TIMEOUT) as client:
        return await client.list_tools()


@pytest.fixture(scope="session")
def mcp_tools(_require_llm_eval_opt_in, use_existing_service):
    """Tool definitions advertised by the MCP server over a real stdio session."""
    args = [
        "--mcp-transport",
        "stdio",
        "--transport-mode",
        os.environ.get("GEOMETRY_TRANSPORT_MODE", "insecure"),
    ]
    if use_existing_service:
        args += [
            "--connect-to-existing-service",
            "--host",
            os.environ.get("GEOMETRY_SERVICE_HOST", "localhost"),
            "--port",
            os.environ.get("GEOMETRY_SERVICE_PORT", "50051"),
        ]

    tools = asyncio.run(_fetch_tools(args))
    if not tools:
        pytest.fail("The MCP server did not advertise any tool")
    return tools


@pytest.fixture(scope="session")
def openai_tools(mcp_tools) -> list[dict]:
    """MCP tools converted to OpenAI chat-completion tool schemas."""
    return to_openai_tools(mcp_tools)


@pytest.fixture(scope="session")
def tool_schemas(mcp_tools) -> dict[str, dict]:
    """Input JSON Schema of every MCP tool, keyed by tool name."""
    return schemas_by_name(mcp_tools)


@pytest.fixture(scope="session")
def llm_eval_repeats(request) -> int:
    """Number of times each prompt is sent to the model."""
    return request.config.getoption("--llm-eval-repeats")


@pytest.fixture(scope="session")
def llm_eval_threshold(request) -> float:
    """Minimum pass rate a case must reach."""
    return request.config.getoption("--llm-eval-threshold")


@pytest.fixture(scope="session")
def eval_results(request) -> list:
    """Accumulator shared by every case, drained by the terminal summary hook."""
    results = getattr(request.config, _RESULTS_ATTR, None)
    if results is None:
        results = []
        setattr(request.config, _RESULTS_ATTR, results)
    return results


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print the per-case pass rates and write the JSON report."""
    results = getattr(config, _RESULTS_ATTR, [])
    if not results:
        return

    threshold = config.getoption("--llm-eval-threshold")
    terminalreporter.write_sep("=", "LLM evaluation")
    for result in sorted(results, key=lambda r: r.pass_rate):
        marker = "PASS" if result.pass_rate >= threshold else "FAIL"
        terminalreporter.write_line(
            f"{marker}  {result.pass_rate:6.0%}  {result.case_id}  (expected: {result.expected})"
        )
    overall = sum(r.pass_rate for r in results) / len(results)
    terminalreporter.write_line(f"overall pass rate: {overall:.1%} over {len(results)} cases")

    report_path = Path(config.getoption("--llm-eval-report"))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "threshold": threshold,
                "overall_pass_rate": overall,
                "cases": [r.as_dict() for r in results],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    terminalreporter.write_line(f"report written to {report_path}")
