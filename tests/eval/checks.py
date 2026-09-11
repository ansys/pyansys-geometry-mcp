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

"""Checker factories: reusable ways to score a model's response.

Each factory returns a :data:`_harness.Checker` -- a function taking the raw
chat-completion message plus the MCP tool schemas (empty if not needed) and
returning an :class:`~_harness.Attempt`. Tool-selection checkers are the main
use case, but plain text checks work through the same :func:`run_once` /
:func:`run_case` machinery.
"""

import json
import re
from typing import Any

import jsonschema

from ._harness import (
    ARGS_MISMATCH,
    CORRECT,
    INVALID_ARGS,
    NO_TOOL,
    TEXT_MISMATCH,
    UNEXPECTED_TOOL,
    WRONG_TOOL,
    Attempt,
    Checker,
)


def expect_tool(name: str, arguments: dict[str, Any]) -> Checker:
    """Require that exactly the tool named ``name`` is called with valid arguments."""

    def _check(message, schemas: dict) -> Attempt:
        calls = message.tool_calls or []
        if not calls:
            return Attempt(outcome=NO_TOOL, detail=f"expected {name!r}, no tool was called")

        call = calls[0]
        called_name = call.function.name

        if len(calls) > 1:
            extra = ", ".join(c.function.name for c in calls[1:])
            return Attempt(
                outcome=UNEXPECTED_TOOL,
                tool_name=called_name,
                detail=f"expected exactly one tool call, got extra call(s): {extra}",
            )
        try:
            parsed = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError as err:
            return Attempt(
                outcome=INVALID_ARGS,
                tool_name=called_name,
                detail=f"arguments are not valid JSON: {err}",
            )

        if called_name != name:
            return Attempt(
                outcome=WRONG_TOOL,
                tool_name=called_name,
                arguments=parsed,
                detail=f"expected {name!r}",
            )

        schema = schemas.get(name)
        if schema is None:
            return Attempt(
                outcome=WRONG_TOOL,
                tool_name=called_name,
                arguments=parsed,
                detail="tool name is not exposed by the MCP server",
            )

        try:
            jsonschema.validate(instance=parsed, schema=schema)
        except jsonschema.ValidationError as err:
            path = ".".join(str(part) for part in err.absolute_path) or "<root>"
            return Attempt(
                outcome=INVALID_ARGS,
                tool_name=called_name,
                arguments=parsed,
                detail=f"{path}: {err.message}",
            )

        mismatches = [
            f"{key}: expected {value!r}, got {parsed.get(key)!r}"
            for key, value in arguments.items()
            if parsed.get(key) != value
        ]
        if mismatches:
            return Attempt(
                outcome=ARGS_MISMATCH,
                tool_name=called_name,
                arguments=parsed,
                detail="; ".join(mismatches),
            )

        return Attempt(outcome=CORRECT, tool_name=called_name, arguments=parsed)

    return _check


def expect_no_tool() -> Checker:
    """Require that the model answers without calling any tool."""

    def _check(message, schemas: dict) -> Attempt:
        calls = message.tool_calls or []
        if calls:
            return Attempt(
                outcome=UNEXPECTED_TOOL,
                tool_name=calls[0].function.name,
                detail="no tool call was expected",
            )
        return Attempt(outcome=CORRECT, text=message.content)

    return _check


def expect_text_contains(*substrings: str, case_sensitive: bool = False) -> Checker:
    """Require the model's plain-text answer to contain every given substring."""

    def _check(message, schemas: dict) -> Attempt:
        calls = message.tool_calls or []
        if calls:
            return Attempt(
                outcome=UNEXPECTED_TOOL,
                tool_name=calls[0].function.name,
                detail="expected a text answer, a tool was called instead",
            )

        content = message.content or ""
        haystack = content if case_sensitive else content.lower()
        missing = [s for s in substrings if (s if case_sensitive else s.lower()) not in haystack]
        if missing:
            return Attempt(outcome=TEXT_MISMATCH, text=content, detail=f"missing: {missing}")
        return Attempt(outcome=CORRECT, text=content)

    return _check


def expect_text_matches(pattern: str, flags: int = re.IGNORECASE) -> Checker:
    """Require the model's plain-text answer to match a regular expression."""
    compiled = re.compile(pattern, flags)

    def _check(message, schemas: dict) -> Attempt:
        calls = message.tool_calls or []
        if calls:
            return Attempt(
                outcome=UNEXPECTED_TOOL,
                tool_name=calls[0].function.name,
                detail="expected a text answer, a tool was called instead",
            )

        content = message.content or ""
        if not compiled.search(content):
            return Attempt(outcome=TEXT_MISMATCH, text=content, detail=f"no match for /{pattern}/")
        return Attempt(outcome=CORRECT, text=content)

    return _check
