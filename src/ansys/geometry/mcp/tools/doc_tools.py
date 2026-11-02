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

"""MCP tools that search the bundled PyAnsys Geometry documentation offline."""

import json
import re

from ansys.common.mcp.logging_config import get_logger
from fastmcp.server import Context

from ansys.geometry.mcp import app
from ansys.geometry.mcp.doc_search import (
    get_api_details as _get_api_details,
    open_bundle,
    suggest_api as _suggest_api,
)

logger = get_logger(__name__)

_DOC_KINDS = ("class", "enumeration", "property", "method", "value")
_MAX_LIMIT = 25
_SUMMARY_LIMIT = 120
_MEMBER_SUMMARY_LIMIT = 80
_XREF_LIMIT = 10
# A dotted ansys.geometry.core type, optionally quoted as a forward reference.
_TYPE_PATH = re.compile(r"(['\"]?)(ansys\.geometry\.core(?:\.[a-z_]\w*)*)\.([A-Z]\w*)\1")
_NEXT_STEP = (
    "Call get_api_details with a hit id for the parameters, return value, and code "
    "examples. Use the signatures and imports as given."
)
_NO_HITS = "No hits. Search again with other or fewer words, or drop the kinds/module filters."


class _Imports:
    """Short type names used in one response, and the import line for each."""

    def __init__(self) -> None:
        self.lines: dict[str, str] = {}

    def add(self, record_id: str) -> None:
        """Record the import line for a class or enumeration id."""
        module, _, name = record_id.split(":", 1)[0].rpartition(".")
        if module:
            self.lines.setdefault(name, f"from {module} import {name}")

    def shorten(self, text: str) -> str:
        """Replace dotted ``ansys.geometry.core`` type paths with their class names."""

        def replace(match: re.Match[str]) -> str:
            module, name = match.group(2), match.group(3)
            line = f"from {module} import {name}"
            if self.lines.setdefault(name, line) != line:
                return match.group(0)
            return name

        return _TYPE_PATH.sub(replace, text) if text else text

    def as_list(self) -> list[str]:
        """Return the import lines in name order."""
        return [self.lines[name] for name in sorted(self.lines)]


def _one_line(text: str, limit: int = _SUMMARY_LIMIT) -> str:
    """Return the first line of ``text``, cut at a word boundary to ``limit`` characters."""
    line = " ".join(next((part for part in text.splitlines() if part.strip()), "").split())
    if len(line) <= limit:
        return line
    return line[: limit - 1].rsplit(" ", 1)[0] + "…"


def _dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _bundle_error(exc: Exception) -> str:
    logger.error(f"Documentation bundle unavailable: {exc}")
    return _dumps({"error": f"Documentation bundle is unavailable: {exc}"})


def _compact_hit(hit: dict, imports: _Imports, verbose: bool) -> dict:
    out: dict[str, object] = {"id": hit["id"], "kind": hit["kind"]}
    if hit["kind"] in ("class", "enumeration"):
        imports.add(hit["id"])
    if "signature" in hit:
        out["signature"] = imports.shorten(str(hit["signature"]))
    summary = str(hit["summary"])
    out["summary"] = summary if verbose else _one_line(summary)
    if verbose:
        out["matched_via"] = hit["matched_via"]
        if hit.get("parent"):
            out["parent"] = hit["parent"]
    return out


def _member_name(member: dict) -> str:
    return str(member["id"]).rsplit(".", 1)[-1]


def _member_line(member: dict, imports: _Imports) -> str:
    signature = imports.shorten(str(member["signature"]))
    summary = _one_line(str(member["summary"]), _MEMBER_SUMMARY_LIMIT)
    return f"{signature} — {summary}" if summary else signature


def _compact_members(members: list[dict], imports: _Imports, full: bool) -> dict:
    """Group class members as own and inherited, by name or as signature lines."""
    own: dict[str, list[str]] = {}
    inherited: dict[str, list[str]] = {}
    for member in members:
        text = _member_line(member, imports) if full else _member_name(member)
        parent = member.get("inherited_from")
        if parent:
            inherited.setdefault(str(parent), []).append(text)
        elif full:
            own.setdefault("members", []).append(text)
        else:
            group = "properties" if member["kind"] == "property" else "methods"
            own.setdefault(group, []).append(text)
    out: dict[str, object] = dict(own)
    if inherited:
        out["inherited"] = inherited
    return out


def _compact_detail(detail: dict, include_members: bool) -> dict:
    if not detail.get("found"):
        return {
            "found": False,
            "id": detail["id"],
            "candidates": [
                {"id": item["id"], "kind": item["kind"], "summary": _one_line(item["summary"])}
                for item in detail.get("candidates", [])
            ],
        }
    imports = _Imports()
    record_id = str(detail["id"])
    kind = detail["kind"]
    imports.add(record_id if kind in ("class", "enumeration") else record_id.rpartition(".")[0])
    out: dict[str, object] = {
        "found": True,
        "id": record_id,
        "kind": kind,
        "summary": detail["summary"],
    }
    for key in ("signature", "description", "body"):
        if key in detail:
            out[key] = imports.shorten(str(detail[key]))
    if kind == "class":
        out["parents"] = detail["parents"]
        out["members"] = _compact_members(detail["members"], imports, include_members)
    if detail.get("fragments"):
        out["fragments"] = detail["fragments"]
    for key in ("returned_by", "accepted_by"):
        items = detail.get(key) or []
        if items:
            out[key] = items[:_XREF_LIMIT]
        if len(items) > _XREF_LIMIT:
            out[f"{key}_total"] = len(items)
    out["imports"] = imports.as_list()
    return out


@app.tool()
def suggest_api(
    ctx: Context,
    words: list[str],
    limit: int = 10,
    kinds: list[str] | None = None,
    module: str | None = None,
    verbose: bool = False,
) -> str:
    """Search the PyAnsys Geometry API reference, examples, and user guide for API identifiers.

    Use this to find which ``ansys.geometry.core`` classes, methods, properties, or
    enumerations perform a task before writing code for ``run_python_code``. The
    bundled documentation is extracted from the ``ansys-geometry-core`` source and is
    authoritative: use the returned signatures and import lines as given, without
    checking them with ``dir()``, ``help()``, or ``inspect``. Unlike introspection, it
    needs no running session and also returns code examples from the official examples
    and user guide. It is a ranked keyword search, not a semantic search: a paraphrase
    matches only when its words appear in the documentation, so search again with other
    words when the results miss. Then call ``get_api_details`` with a hit ``id`` for the
    full parameters, return value, and code examples.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    words : list[str]
        Search words, combined as a disjunction, so more words widen the search.
        CamelCase and dotted names are split into their parts, so
        ``["DesignPoint"]`` also matches ``design`` and ``point``. A single dotted
        or CamelCase name, such as ``["Component.extrude_sketch"]``, is looked up
        as an identifier first.
    limit : int, default: 10
        Maximum number of hits to return, at most 25.
    kinds : list[str], default: None
        Keep only hits of these kinds: ``"class"``, ``"enumeration"``,
        ``"property"``, ``"method"``, or ``"value"`` (an enumeration value).
        ``None`` keeps every kind.
    module : str, default: None
        Keep only records whose dotted id contains this module segment, such as
        ``"designer"``, ``"sketch"``, ``"math"``, or ``"tools"``. ``None`` keeps
        every module.
    verbose : bool, default: False
        Also return the full summary, ``matched_via`` (the record fields and
        attachment sources that matched), and ``parent`` for each hit.

    Returns
    -------
    str
        JSON object with ``hits`` in rank order, ``imports``, and ``next_step``.
        Each hit has ``id``, ``kind``, and a one-line ``summary``; methods,
        properties, and enumeration values also have ``signature``. Types in
        signatures are short class names; ``imports`` gives the import line for
        each.

    """
    logger.info(
        f"Suggesting API for words={words!r} (limit={limit}, kinds={kinds}, module={module})"
    )
    try:
        connection = open_bundle()
    except (OSError, ValueError) as exc:
        return _bundle_error(exc)
    try:
        hits = _suggest_api(
            connection,
            " ".join(words),
            limit=max(1, min(limit, _MAX_LIMIT)),
            kinds=kinds or None,
            module=module,
        )
    except ValueError as exc:
        return _dumps({"error": str(exc), "valid_kinds": list(_DOC_KINDS)})
    finally:
        connection.close()
    imports = _Imports()
    payload: dict[str, object] = {
        "hits": [_compact_hit(hit, imports, verbose) for hit in hits],
        "imports": imports.as_list(),
        "next_step": _NEXT_STEP if hits else _NO_HITS,
    }
    return _dumps(payload)


@app.tool()
def get_api_details(
    ctx: Context,
    identifier: str,
    include_members: bool = False,
    include_body: bool = False,
) -> str:
    """Get the docstring, signature, parameters, return type, and usage examples of an API.

    Method and class documentation for ``ansys.geometry.core``: how to call a method,
    what its parameters and return value are, which import line to use, and code
    examples from the official examples and user guide. Use this after
    ``suggest_api``, or directly with a known name, before writing code for
    ``run_python_code``. The bundled documentation is extracted from the
    ``ansys-geometry-core`` source and is authoritative: use the signature and import
    lines as given, without checking them with ``dir()``, ``help()``, or ``inspect``.
    No running session is required.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    identifier : str
        An ``id`` from a ``suggest_api`` hit, such as
        ``"ansys.geometry.core.designer.component.Component.extrude_sketch"``. A
        shorter form is also resolved: ``"Component.extrude_sketch"``, a class name
        such as ``"Body"``, or a member name such as ``"extrude_sketch"``. An
        unknown or ambiguous identifier returns ``found: false`` with
        ``candidates`` to try instead.
    include_members : bool, default: False
        For a class, list every member as a signature line with a one-line
        summary. The default lists member names only.
    include_body : bool, default: False
        For a class, also return the full stored class body.

    Returns
    -------
    str
        JSON object. ``found`` is ``false`` when the identifier is absent or
        ambiguous. A method, property, or enumeration value has ``signature`` and
        ``description`` (the docstring). An enumeration has ``body`` with its
        values. A class has ``parents`` and ``members``; inherited members are
        grouped under the parent class id. ``fragments`` are code samples that use
        the record, each with ``source`` (``"examples"`` or ``"doc_snippets"``) and
        ``text``. ``returned_by`` and ``accepted_by`` list up to 10 members that
        return or accept this type, with ``*_total`` when there are more.
        ``imports`` gives the import line for the record and for each type named.

    """
    logger.info(
        f"Getting API details for identifier={identifier!r} "
        f"(include_members={include_members}, include_body={include_body})"
    )
    try:
        connection = open_bundle()
    except (OSError, ValueError) as exc:
        return _bundle_error(exc)
    try:
        detail = _get_api_details(connection, identifier, section="body" if include_body else None)
    finally:
        connection.close()
    return _dumps(_compact_detail(detail, include_members))
