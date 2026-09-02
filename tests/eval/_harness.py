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

"""Machinery for evaluating LLM responses to prompts sent through the MCP tools.

The harness sends a prompt to the model and hands the raw response to a
*checker* callable (see ``checks.py``) that scores it as an :class:`Attempt`.
Tool-discoverability is the main use case (did the model call the right tool
with schema-valid arguments?), but a checker can just as well inspect a plain
text answer, so the same machinery works for non-tool-calling evaluations too.

The harness deliberately never raises on a bad model answer: a failed check is
recorded as a failed *attempt* so that a pass rate can be computed over several
repeats of the same prompt.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
import os
from typing import Any

#: Default Azure OpenAI resource used when ``AZURE_OPENAI_ENDPOINT`` is unset.
DEFAULT_ENDPOINT = "https://casebu-chatgpt-eastus-2.openai.azure.com/"

#: Default Azure OpenAI REST API version.
DEFAULT_API_VERSION = "2024-10-21"

SYSTEM_PROMPT = (
    "You are an assistant that drives the Ansys Geometry modeling service through the "
    "tools you have been given. When the user's request can be fulfilled by one of the "
    "tools, call exactly one tool with the arguments it requires. When no tool fits the "
    "request, answer in plain text and do not call any tool."
)

# Attempt outcomes.
CORRECT = "correct"
WRONG_TOOL = "wrong_tool"
NO_TOOL = "no_tool"
UNEXPECTED_TOOL = "unexpected_tool"
INVALID_ARGS = "invalid_args"
ARGS_MISMATCH = "args_mismatch"
TEXT_MISMATCH = "text_mismatch"
API_ERROR = "api_error"

#: Scores a chat-completion message, given the MCP tool schemas keyed by name.
Checker = Callable[[Any, dict[str, dict[str, Any]]], "Attempt"]


class MissingCredentialsError(RuntimeError):
    """Raised when the Azure OpenAI configuration is incomplete."""


@dataclass(frozen=True)
class AzureConfig:
    """Connection settings for the Azure OpenAI deployment under evaluation."""

    endpoint: str
    api_key: str
    deployment: str
    api_version: str
    temperature: float | None
    max_concurrency: int

    @classmethod
    def from_env(cls) -> "AzureConfig":
        """Build the configuration from environment variables.

        Raises
        ------
        MissingCredentialsError
            If the API key or the deployment name is not set.
        """
        api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")
        missing = [
            name
            for name, value in (
                ("AZURE_OPENAI_API_KEY", api_key),
                ("AZURE_OPENAI_DEPLOYMENT", deployment),
            )
            if not value
        ]
        if missing:
            raise MissingCredentialsError(", ".join(missing))

        # Left unset by default: reasoning models reject any value other than 1.
        raw_temperature = os.environ.get("AZURE_OPENAI_TEMPERATURE", "")

        return cls(
            endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT") or DEFAULT_ENDPOINT,
            api_key=api_key,
            deployment=deployment,
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION") or DEFAULT_API_VERSION,
            temperature=float(raw_temperature) if raw_temperature else None,
            max_concurrency=int(os.environ.get("AZURE_OPENAI_MAX_CONCURRENCY") or "4"),
        )


@dataclass
class Attempt:
    """Outcome of a single request to the model, as scored by a :data:`Checker`."""

    outcome: str
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    text: str | None = None
    detail: str | None = None

    @property
    def passed(self) -> bool:
        """Whether the checker considered the model's response correct."""
        return self.outcome == CORRECT


@dataclass
class CaseResult:
    """Aggregated outcome of every repeat of a single evaluation case."""

    case_id: str
    prompt: str
    expected: str = ""
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Fraction of attempts the checker scored as correct."""
        if not self.attempts:
            return 0.0
        return sum(a.passed for a in self.attempts) / len(self.attempts)

    def summary(self) -> str:
        """Human-readable breakdown of the failing attempts."""
        counts: dict[str, int] = {}
        for attempt in self.attempts:
            counts[attempt.outcome] = counts.get(attempt.outcome, 0) + 1
        lines = [f"outcomes: {counts}"]
        for index, attempt in enumerate(self.attempts):
            if attempt.passed:
                continue
            lines.append(
                f"  attempt {index}: {attempt.outcome} tool={attempt.tool_name!r}"
                f" text={attempt.text!r} detail={attempt.detail}"
            )
        return "\n".join(lines)

    def as_dict(self) -> dict[str, Any]:
        """Serialize the result for the JSON report."""
        return {
            "case_id": self.case_id,
            "prompt": self.prompt,
            "expected": self.expected,
            "pass_rate": self.pass_rate,
            "attempts": [
                {
                    "outcome": a.outcome,
                    "tool_name": a.tool_name,
                    "arguments": a.arguments,
                    "text": a.text,
                    "detail": a.detail,
                }
                for a in self.attempts
            ],
        }


def to_openai_tools(mcp_tools) -> list[dict[str, Any]]:
    """Convert MCP tool definitions into OpenAI chat-completion tool schemas.

    Parameters
    ----------
    mcp_tools : list[mcp.types.Tool]
        Tools as returned by an MCP client ``list_tools()`` call.

    Returns
    -------
    list[dict]
        Non-strict function tools; strict mode is avoided because the MCP input
        schemas use ``$ref``/``$defs`` and do not forbid additional properties.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        }
        for tool in mcp_tools
    ]


def schemas_by_name(mcp_tools) -> dict[str, dict[str, Any]]:
    """Map each MCP tool name to its input JSON Schema."""
    return {tool.name: tool.inputSchema for tool in mcp_tools}


async def run_once(
    client,
    config: AzureConfig,
    prompt: str,
    checker: Checker,
    tools: list[dict[str, Any]] | None = None,
    schemas: dict[str, dict[str, Any]] | None = None,
) -> Attempt:
    """Send a single prompt to the model and score the response with ``checker``.

    Parameters
    ----------
    tools
        OpenAI tool schemas to attach to the request, or ``None`` to send a
        plain chat-completion request with no tools available.
    schemas
        MCP input JSON Schemas keyed by tool name, forwarded to ``checker`` for
        argument validation. Only needed by tool-selection checkers.
    """
    request: dict[str, Any] = {
        "model": config.deployment,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    if tools:
        request["tools"] = tools
        request["tool_choice"] = "auto"
    if config.temperature is not None:
        request["temperature"] = config.temperature

    try:
        response = await client.chat.completions.create(**request)
    except Exception as err:  # noqa: BLE001 - transport failures are reported, not raised
        return Attempt(outcome=API_ERROR, detail=f"{type(err).__name__}: {err}")

    return checker(response.choices[0].message, schemas or {})


async def run_case(
    config: AzureConfig,
    prompt: str,
    checker: Checker,
    repeats: int,
    case_id: str = "",
    expected: str = "",
    tools: list[dict[str, Any]] | None = None,
    schemas: dict[str, dict[str, Any]] | None = None,
) -> CaseResult:
    """Run one prompt ``repeats`` times and aggregate the outcomes."""
    from openai import AsyncAzureOpenAI

    semaphore = asyncio.Semaphore(config.max_concurrency)

    async with AsyncAzureOpenAI(
        azure_endpoint=config.endpoint,
        api_key=config.api_key,
        api_version=config.api_version,
    ) as client:

        async def _attempt() -> Attempt:
            async with semaphore:
                return await run_once(client, config, prompt, checker, tools, schemas)

        attempts = await asyncio.gather(*(_attempt() for _ in range(repeats)))

    return CaseResult(
        case_id=case_id,
        prompt=prompt,
        expected=expected,
        attempts=list(attempts),
    )
