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


def _bundle_error(exc: Exception) -> str:
    logger.error(f"Documentation bundle unavailable: {exc}")
    return json.dumps({"error": f"Documentation bundle is unavailable: {exc}"})


@app.tool()
def suggest_api(
    ctx: Context,
    words: list[str],
    limit: int = 10,
    kinds: list[str] | None = None,
    module: str | None = None,
) -> str:
    """Search the PyAnsys Geometry API reference, examples, and user guide for API identifiers.

    Use this to find which ``ansys.geometry.core`` classes, methods, properties, or
    enumerations perform a task before writing code for ``run_python_code``. It is a
    ranked keyword search, not a semantic search: a paraphrase matches only when its
    words appear in the documentation, so search again with other words when the
    results miss. No geometry service and no network access are required. Pass a
    returned ``id`` to ``get_api_details`` for signatures, members, and examples.

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
        Maximum number of hits to return.
    kinds : list[str], default: None
        Keep only hits of these kinds: ``"class"``, ``"enumeration"``,
        ``"property"``, ``"method"``, or ``"value"`` (an enumeration value).
        ``None`` keeps every kind.
    module : str, default: None
        Keep only records whose dotted id contains this module segment, such as
        ``"designer"``, ``"sketch"``, ``"math"``, or ``"tools"``. ``None`` keeps
        every module.

    Returns
    -------
    str
        JSON array of hits in rank order. Each hit has ``id``, ``kind``,
        ``summary``, and ``matched_via``. Properties, methods, and enumeration
        values also have ``signature`` and ``parent``. ``matched_via`` lists the
        record fields and attachment sources (``"doc_snippets"`` for the user
        guide, ``"examples"`` for example notebooks) that matched; the labels are
        not lookup keys.

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
            connection, " ".join(words), limit=limit, kinds=kinds or None, module=module
        )
    except ValueError as exc:
        return json.dumps({"error": str(exc), "valid_kinds": list(_DOC_KINDS)})
    finally:
        connection.close()
    return json.dumps(hits, indent=2, ensure_ascii=False)


@app.tool()
def get_api_details(ctx: Context, identifier: str, include_body: bool = False) -> str:
    """Get the documentation for one PyAnsys Geometry API identifier.

    Use this after ``suggest_api`` to read the exact signature, description,
    members, and usage examples of an ``ansys.geometry.core`` class, method,
    property, or enumeration before writing code for ``run_python_code``. No
    geometry service and no network access are required.

    Parameters
    ----------
    ctx : Context
        MCP request context (injected automatically).
    identifier : str
        An ``id`` from a ``suggest_api`` hit, such as
        ``"ansys.geometry.core.designer.component.Component.extrude_sketch"``. A
        shorter form is also resolved: ``"Component.extrude_sketch"``, or a leaf
        name such as ``"extrude_sketch"``. An unknown or ambiguous identifier
        returns ``found: false`` with ``candidates`` to try instead.
    include_body : bool, default: False
        For a class, also return the full stored class body. The default omits it
        to keep the response compact.

    Returns
    -------
    str
        JSON object. ``found`` is ``false`` when the identifier is absent or
        ambiguous. A method, property, or enumeration value has ``signature``,
        ``description``, and ``fragments``. A class has ``parents``, ``members``
        (including inherited members, each with ``inherited_from``), and
        ``fragments``. Every record has ``returned_by`` and ``accepted_by``: the
        members that return or accept this type. A fragment has ``source``
        (``"examples"`` or ``"doc_snippets"``) and ``text``, a code sample that
        uses the record.

    """
    logger.info(f"Getting API details for identifier={identifier!r} (include_body={include_body})")
    try:
        connection = open_bundle()
    except (OSError, ValueError) as exc:
        return _bundle_error(exc)
    try:
        detail = _get_api_details(connection, identifier, section="body" if include_body else None)
    finally:
        connection.close()
    return json.dumps(detail, indent=2, ensure_ascii=False)
