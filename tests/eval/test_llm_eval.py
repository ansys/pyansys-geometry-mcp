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

import asyncio

import pytest

from ._harness import API_ERROR, run_case
from .cases import CASES, EvalCase

pytestmark = pytest.mark.llm_eval


def test_schemas_are_model_ready(mcp_tools, openai_tools):
    """The schemas sent to the model must not leak the injected MCP context."""
    for tool in mcp_tools:
        properties = tool.inputSchema.get("properties", {})
        assert "ctx" not in properties, f"{tool.name} exposes the MCP context as a parameter"

    for entry in openai_tools:
        function = entry["function"]
        assert function["description"], f"{function['name']} has no description to select it by"


@pytest.mark.parametrize("case", CASES, ids=[case.id for case in CASES])
def test_llm_response_meets_expectation(
    case: EvalCase,
    azure_config,
    openai_tools,
    tool_schemas,
    llm_eval_repeats,
    llm_eval_threshold,
    eval_results,
):
    """The model's response must satisfy the case's checker often enough."""
    result = asyncio.run(
        run_case(
            config=azure_config,
            prompt=case.prompt,
            checker=case.checker,
            repeats=llm_eval_repeats,
            case_id=case.id,
            expected=case.expected,
            tools=openai_tools if case.tools else None,
            schemas=tool_schemas,
        )
    )
    eval_results.append(result)

    api_errors = [a for a in result.attempts if a.outcome == API_ERROR]
    if len(api_errors) == len(result.attempts):
        pytest.fail(f"Every request to Azure OpenAI failed: {api_errors[0].detail}")

    assert result.pass_rate >= llm_eval_threshold, (
        f"{case.id}: pass rate {result.pass_rate:.0%} is below the "
        f"{llm_eval_threshold:.0%} threshold\n{result.summary()}"
    )
