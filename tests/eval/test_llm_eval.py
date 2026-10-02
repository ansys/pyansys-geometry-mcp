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
