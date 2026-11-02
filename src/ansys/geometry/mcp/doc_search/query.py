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

"""Search the documentation database and return record details."""

from __future__ import annotations

from collections.abc import Collection
import json
import re
import sqlite3
from typing import NamedTuple

from ansys.geometry.mcp.doc_search.terms import prepare_query, query_tokens, segment_identifier

# Scales attachment BM25 into the same range as record BM25. The fixture tests
# require a direct name match to beat the best three fragments, while an
# attachment-only match still returns its owner.
_ATTACHMENT_FACTOR = 0.5
_TOP_ATTACHMENTS = 3
# Attachment-only hits use this order.
_ATTACHMENT_GROUP = {
    "doc_snippets": 0,
    "examples": 1,
}
# Enumeration values that match only in passing rank below classes and members.
_VALUE_FACTOR = 0.2
_KINDS = frozenset({"class", "enumeration", "property", "method", "value"})
_SECTIONS = frozenset({"body"})
_CANDIDATE_LIMIT = 8
_INHERITS_FROM = re.compile(
    r"^Inherits from\n(?P<bullets>(?:- [^\n]+\n?)*)",
    re.MULTILINE,
)
_CLASS_MEMBERS = """
SELECT id, kind, title, summary, body
FROM records
WHERE parent_id = ? AND kind IN ('property', 'method')
ORDER BY CASE kind WHEN 'property' THEN 0 WHEN 'method' THEN 1 ELSE 2 END, id
"""

# Records with these statuses stay in the index and rank lower.
_STATUS_MULTIPLIER = {
    "obsolete": 0.25,
    "deprecated": 0.5,
    "internal": 0.5,
}

# bm25() consumes one weight per column in table order, including unindexed
# columns. The weights are id 0, leaf name 10, title 3, summary 2, terms 2,
# signature 3, and description 1.
_RECORD_MATCH = """
SELECT records.id, records.kind, records.summary, records.status, records.parent_id,
       -bm25(records_fts, 0.0, 10.0, 3.0, 2.0, 2.0, 3.0, 1.0) AS score
FROM records_fts
JOIN records ON records.id = records_fts.id
WHERE records_fts MATCH ?
"""

_FIELD_MATCH = """
SELECT id FROM records_fts
WHERE records_fts MATCH ?
"""

# Record fields reported in ``matched_via``, strongest weight first.
_MATCH_FIELDS = (
    ("leaf_name", "leaf name"),
    ("title", "title"),
    ("signature", "signature"),
    ("summary", "summary"),
    ("terms", "terms"),
    ("description", "description"),
)

_ATTACHMENT_MATCH = """
SELECT records.id, records.kind, records.summary, records.status, records.parent_id,
       attachments_fts.source,
       (-bm25(attachments_fts)) * links.weight AS contribution
FROM attachments_fts
JOIN attachment_links AS links
  ON links.attachment_id = attachments_fts.attachment_id
JOIN records ON records.id = links.record_id
WHERE attachments_fts MATCH ?
  AND attachments_fts.source IN ('examples', 'doc_snippets')
ORDER BY contribution DESC, links.attachment_id
"""


class _Record(NamedTuple):
    """Kind, summary, status, and parent for one ranked record."""

    kind: str
    summary: str
    status: str
    parent_id: str | None


class _Contribution(NamedTuple):
    """One matching attachment and its weighted BM25 contribution."""

    source: str
    contribution: float


def suggest_api(
    connection: sqlite3.Connection,
    query: str,
    *,
    limit: int = 10,
    kinds: Collection[str] | None = None,
    module: str | None = None,
) -> list[dict[str, object]]:
    """Rank API records for a query.

    The score is the record's BM25 times a status multiplier, plus a scaled
    sum of the best three matching attachment scores. Each attachment score is
    multiplied by its link weight. A record that matches its own text ranks
    ahead of one that matches only through an attachment. Attachment-only
    matches then follow documentation snippets, then examples. The text
    score breaks ties inside a source. A record that matches more than one of
    those sources uses the highest source. Obsolete, deprecated, and internal
    records are ranked lower. An attachment match returns the linked record,
    including when the record text does not contain the query. A query that
    is empty or only stop words returns no hits, unless that single token is
    an exact id, suffix, or leaf.

    A single-token identifier is resolved before full-text search. Exact ids,
    id suffixes, and leaf names are placed first, in that order.
    Enumeration values rank lower unless the query names the value or its
    enumeration. ``kinds`` and ``module`` apply before ``limit``.

    Parameters
    ----------
    connection
        Open documentation database.
    query
        Natural-language query, or one dotted or CamelCase name.
    limit
        Maximum number of hits to return.
    kinds
        Kinds to keep. ``None`` keeps every kind. Each value is ``class``,
        ``enumeration``, ``property``, ``method``, or ``value``.
    module
        When set, keep records whose id contains this dotted segment, such as
        ``designer``.

    Returns
    -------
    list of dict
        Hits in rank order. Each hit has ``id``, ``kind``, ``summary``, and
        ``matched_via``. A property, method, or enumeration value also has
        ``signature`` and ``parent``. ``matched_via`` lists the labels that
        matched the query. Record fields come first, strongest weight first:
        ``leaf name``, ``title``, ``signature``, ``summary``, ``terms``, and
        ``description``. Attachment sources follow, strongest contribution
        first, and each source appears once: ``examples`` or ``doc_snippets``.

    Raises
    ------
    ValueError
        ``kinds`` contains a name that is not a record kind.

    """
    selected = _validate_kinds(kinds)
    module_name = (module or "").strip().lower()
    if limit < 1:
        return []
    normalized = _normalize_identifier(query)
    identifier_ids = (
        _identifier_ids(connection, normalized) if _is_single_token(query) and normalized else []
    )
    expression = prepare_query(query)
    tokens = query_tokens(query)
    records: dict[str, _Record] = {}
    own_scores: dict[str, float] = {}
    contributions: dict[str, list[_Contribution]] = {}
    if expression:
        own_scores = _own_scores(connection, expression, records)
        contributions = _contributions(connection, expression, records)
    _remember(connection, [item for item in identifier_ids if item not in records], records)
    ranked = _rank(records, own_scores, contributions, tokens, selected, module_name)
    chosen = _choose(identifier_ids, ranked, records, selected, module_name, limit)
    fields = _matched_fields(connection, expression, [item[0] for item in chosen])
    member_ids = [
        record_id for record_id, record, _matched in chosen if record.kind in _MEMBER_KINDS
    ]
    signatures = _signatures(connection, member_ids)
    return [
        _hit(record_id, record, fields.get(record_id, []), matched, signatures)
        for record_id, record, matched in chosen
    ]


# How much fragment text one detail response may include.
_FRAGMENT_LIMIT = 2000

_MEMBER_KINDS = frozenset({"property", "method", "value"})

_LOAD_RECORD = """
SELECT kind, source, summary, body, status
FROM records
WHERE id = ?
"""

_LOAD_CROSS_REFERENCES = """
SELECT returned_by, accepted_by
FROM api_cross_references
WHERE record_id = ?
"""

_MEMBER_FRAGMENTS = """
SELECT attachments.source, attachments.body, links.weight
FROM attachment_links AS links
JOIN attachments ON attachments.id = links.attachment_id
WHERE links.record_id = ?
  AND attachments.source IN ('examples', 'doc_snippets')
ORDER BY links.weight DESC, attachments.source, attachments.id
"""


class _TextItem(NamedTuple):
    """One fragment that may be cut to the character limit."""

    source: str
    text: str


def get_api_details(
    connection: sqlite3.Connection,
    record_id: str,
    *,
    section: str | None = None,
) -> dict[str, object]:
    """Return the documentation stored for one record.

    A member includes its signature and the linked example and documentation
    snippets, most specific first. A class or enumeration includes those
    snippets too. Fragment text stops at a fixed character limit. A class
    includes its own members and inherited members, and the parent ids.
    Every record includes ``returned_by`` and ``accepted_by`` lists.

    An unknown id is matched again after stripping a trailing dot or ``()``,
    then by case, suffix, or leaf name. One match returns that record under
    its canonical id. Several matches, or none, are a not-found result with
    ``candidates``.

    Parameters
    ----------
    connection
        Open documentation database.
    record_id
        API record id or leaf name.
    section
        ``body`` also returns the stored class body. ``None`` is the compact
        view.

    Returns
    -------
    dict
        Record detail. ``found`` is ``False`` when the id is absent or
        ambiguous. A not-found result has ``candidates``, each with ``id``,
        ``kind``, and ``summary``. A member has ``signature`` and
        ``fragments``. A class or enumeration has ``fragments``. A fragment
        has ``source`` and ``text``. A class has ``parents`` and ``members``.
        A member entry has ``id``, ``kind``, ``signature``, ``summary``, and
        ``inherited_from``. Every kind has structured type cross-references.

    Raises
    ------
    ValueError
        ``section`` is not ``body``.

    """
    _validate_section(section)
    row = connection.execute(_LOAD_RECORD, (record_id,)).fetchone()
    if row is None:
        resolved = _resolve_ids(connection, record_id)
        if len(resolved) != 1:
            return _not_found(connection, record_id, resolved)
        record_id = resolved[0]
        row = connection.execute(_LOAD_RECORD, (record_id,)).fetchone()
        if row is None:
            return _not_found(connection, record_id, [])
    kind = row["kind"]
    if kind == "class":
        detail = _class_details(connection, record_id, row, section)
    elif kind in _MEMBER_KINDS:
        detail = _member_details(connection, record_id, row)
    else:
        detail = {
            "found": True,
            "id": record_id,
            "kind": kind,
            "summary": row["summary"],
            "body": row["body"],
            "fragments": _linked_fragments(connection, record_id),
        }
    detail.update(_cross_references(connection, record_id))
    return detail


def _cross_references(connection: sqlite3.Connection, record_id: str) -> dict[str, list[str]]:
    """Return structured type cross-references for one API record.

    Parameters
    ----------
    connection
        Open documentation database.
    record_id
        API record id.

    Returns
    -------
    dict
        The returned-by and accepted-by lists. Each list is empty when the
        database predates cross-reference ingest.

    """
    row = connection.execute(_LOAD_CROSS_REFERENCES, (record_id,)).fetchone()
    if row is None:
        return {"returned_by": [], "accepted_by": []}
    return {
        "returned_by": json.loads(row["returned_by"]),
        "accepted_by": json.loads(row["accepted_by"]),
    }


def _member_details(
    connection: sqlite3.Connection, record_id: str, row: sqlite3.Row
) -> dict[str, object]:
    """Return property, method, or enumeration-value details.

    Parameters
    ----------
    connection
        Open documentation database.
    record_id
        Member record id.
    row
        Record row. The first line of the body is the signature.

    Returns
    -------
    dict
        Member detail. Fragments are ordered from fewest owners to most.

    """
    signature, _separator, description = str(row["body"]).partition("\n")
    return {
        "found": True,
        "id": record_id,
        "kind": row["kind"],
        "summary": row["summary"],
        "signature": signature,
        "description": description.lstrip("\n"),
        "fragments": _linked_fragments(connection, record_id),
    }


def _linked_fragments(connection: sqlite3.Connection, record_id: str) -> list[dict[str, str]]:
    """Return the example and documentation snippets linked to one record.

    Parameters
    ----------
    connection
        Open documentation database.
    record_id
        API record id.

    Returns
    -------
    list of dict
        Snippets that fit the character limit, fewest owners first. Each
        snippet has ``source`` and ``text``.

    """
    fragments = [
        _TextItem(item["source"], item["body"])
        for item in connection.execute(_MEMBER_FRAGMENTS, (record_id,))
    ]
    return [{"source": item.source, "text": item.text} for item in _fit(fragments, _FRAGMENT_LIMIT)]


def _class_details(
    connection: sqlite3.Connection,
    record_id: str,
    row: sqlite3.Row,
    section: str | None,
) -> dict[str, object]:
    """Return class details, including members and parents.

    Parameters
    ----------
    connection
        Open documentation database.
    record_id
        Class record id.
    row
        Record row. The body holds inheritance and the stored member text.
    section
        ``body`` includes the stored body. ``None`` omits it.

    Returns
    -------
    dict
        Class detail, including ``parents``, ``members``, and ``fragments``.

    """
    stored = str(row["body"])
    detail: dict[str, object] = {
        "found": True,
        "id": record_id,
        "kind": "class",
        "summary": row["summary"],
        "parents": _parent_ids(stored),
        "members": _class_members(connection, record_id, stored),
        "fragments": _linked_fragments(connection, record_id),
    }
    if section == "body":
        detail["body"] = stored
    return detail


def _fit(items: list[_TextItem], limit: int) -> list[_TextItem]:
    """Keep text items until they reach ``limit`` characters.

    Parameters
    ----------
    items
        Candidates in the order they should be shown.
    limit
        Maximum number of characters of item text to keep.

    Returns
    -------
    list of _TextItem
        Items that fit. A later item that does not fit is omitted whole. The
        first item is shortened when it alone exceeds the limit.

    """
    kept: list[_TextItem] = []
    used = 0
    for item in items:
        remaining = limit - used
        if len(item.text) <= remaining:
            kept.append(item)
            used += len(item.text)
            continue
        if not kept and remaining > 0:
            kept.append(_TextItem(item.source, item.text[:remaining]))
        break
    return kept


def _own_scores(
    connection: sqlite3.Connection, expression: str, records: dict[str, _Record]
) -> dict[str, float]:
    """Return positive record BM25 scores and remember each matching record.

    Parameters
    ----------
    connection
        Open documentation database.
    expression
        FTS5 ``OR`` expression from ``prepare_query``.
    records
        Record details filled as matches are found.

    Returns
    -------
    dict
        Record id to a positive BM25 score. A non-positive score is omitted.

    """
    scores: dict[str, float] = {}
    for row in connection.execute(_RECORD_MATCH, (expression,)):
        record_id = row["id"]
        records.setdefault(record_id, _record(row))
        score = float(row["score"])
        if score > 0:
            scores[record_id] = score
    return scores


def _contributions(
    connection: sqlite3.Connection, expression: str, records: dict[str, _Record]
) -> dict[str, list[_Contribution]]:
    """Group positive attachment contributions by the record they link to.

    Parameters
    ----------
    connection
        Open documentation database.
    expression
        FTS5 ``OR`` expression from ``prepare_query``.
    records
        Record details filled as matches are found. A link whose record was
        removed is ignored.

    Returns
    -------
    dict
        Record id to contributions ordered from strongest to weakest.

    """
    grouped: dict[str, list[_Contribution]] = {}
    for row in connection.execute(_ATTACHMENT_MATCH, (expression,)):
        contribution = float(row["contribution"])
        if contribution <= 0:
            continue
        record_id = row["id"]
        records.setdefault(record_id, _record(row))
        grouped.setdefault(record_id, []).append(_Contribution(row["source"], contribution))
    return grouped


def _record(row: sqlite3.Row) -> _Record:
    """Copy the ranking fields off a joined record row.

    Parameters
    ----------
    row
        Row from a record or attachment match query.

    Returns
    -------
    _Record
        Kind, summary, status, and parent id.

    """
    return _Record(row["kind"], row["summary"], row["status"], row["parent_id"])


def _matched_fields(
    connection: sqlite3.Connection, expression: str, record_ids: list[str]
) -> dict[str, list[str]]:
    """Return the indexed fields that match ``expression`` for each record.

    Parameters
    ----------
    connection
        Open documentation database.
    expression
        FTS5 ``OR`` expression from ``prepare_query``.
    record_ids
        Record ids whose match reasons are needed. The order of fields for
        each id follows ``_MATCH_FIELDS``.

    Returns
    -------
    dict
        Record id to field labels such as ``leaf name`` or ``title``.

    """
    found: dict[str, list[str]] = {record_id: [] for record_id in record_ids}
    if not record_ids:
        return found
    wanted = set(record_ids)
    for column, label in _MATCH_FIELDS:
        rows = connection.execute(_FIELD_MATCH, (f"{column} : ({expression})",))
        matched = {row["id"] for row in rows} & wanted
        for record_id in record_ids:
            if record_id in matched:
                found[record_id].append(label)
    return found


def _hit(
    record_id: str,
    record: _Record,
    fields: list[str],
    attachments: list[_Contribution],
    signatures: dict[str, str],
) -> dict[str, object]:
    """Build one public hit from a ranked record.

    Parameters
    ----------
    record_id
        API record id.
    record
        Kind and summary shown to the caller.
    fields
        Matching record fields, strongest first.
    attachments
        Matching attachments that contributed to the score, strongest first.
    signatures
        Member id to the first line of its body.

    Returns
    -------
    dict
        Hit with ``id``, ``kind``, ``summary``, and ``matched_via``.
        ``matched_via`` lists field labels, then each
        matching attachment source once. A member also has ``signature``
        and ``parent``.

    """
    reasons: list[str] = list(fields)
    seen: set[str] = set()
    for item in attachments:
        if item.source in seen:
            continue
        seen.add(item.source)
        reasons.append(item.source)
    hit: dict[str, object] = {
        "id": record_id,
        "kind": record.kind,
        "summary": record.summary,
        "matched_via": reasons,
    }
    if record.kind in _MEMBER_KINDS:
        hit["signature"] = signatures.get(record_id, "")
        hit["parent"] = record.parent_id
    return hit


def _validate_kinds(kinds: Collection[str] | None) -> frozenset[str] | None:
    """Return the kind allow-list, or ``None`` when every kind is allowed.

    Parameters
    ----------
    kinds
        Requested kinds. ``None`` allows every kind.

    Returns
    -------
    frozenset of str or None
        The requested kinds. ``None`` when ``kinds`` is ``None``.

    Raises
    ------
    ValueError
        A name is not a record kind.

    """
    if kinds is None:
        return None
    selected = frozenset(kinds)
    unknown = sorted(selected - _KINDS)
    if unknown:
        raise ValueError(f"unknown kind: {unknown[0]}")
    return selected


def _validate_section(section: str | None) -> None:
    """Reject a section name other than ``body``.

    Parameters
    ----------
    section
        Requested detail section. ``None`` is the compact view.

    Raises
    ------
    ValueError
        ``section`` is set and is not a known section.

    """
    if section is not None and section not in _SECTIONS:
        raise ValueError(f"unknown section: {section}")


def _rank(
    records: dict[str, _Record],
    own_scores: dict[str, float],
    contributions: dict[str, list[_Contribution]],
    tokens: list[str],
    kinds: frozenset[str] | None,
    module_name: str,
) -> list[tuple[float, str, _Record, list[_Contribution]]]:
    """Score records that pass the kind and module filters.

    Parameters
    ----------
    records
        Record details for full-text and identifier matches.
    own_scores
        Record id to a positive BM25 score.
    contributions
        Record id to attachment contributions, strongest first.
    tokens
        Query words, used to decide whether an enumeration value keeps its score.
    kinds
        Kind allow-list. ``None`` allows every kind.
    module_name
        Lowercase module segment. Empty allows every record.

    Returns
    -------
    list of tuple
        Score, record id, record, and the best three attachments. Records that
        match their own text come first, in score order. Attachment-only
        matches follow, grouped as documentation snippets, then examples.
        A non-positive score is omitted.

    """
    own: list[tuple[float, str, _Record, list[_Contribution]]] = []
    grouped: list[tuple[int, float, str, _Record, list[_Contribution]]] = []
    for record_id, record in records.items():
        if not _passes(record_id, record, kinds, module_name):
            continue
        matched = contributions.get(record_id, [])
        best = matched[:_TOP_ATTACHMENTS]
        attachment_score = sum(item.contribution for item in best)
        own_score = own_scores.get(record_id, 0.0)
        multiplier = _STATUS_MULTIPLIER.get(record.status, 1.0)
        score = own_score * multiplier + _ATTACHMENT_FACTOR * attachment_score
        if record.kind == "value" and not _value_named(record_id, record, tokens):
            score *= _VALUE_FACTOR
        if score <= 0:
            continue
        item = (score, record_id, record, best)
        if own_score > 0:
            own.append(item)
            continue
        grouped.append((_attachment_group(matched), score, record_id, record, best))
    own.sort(key=lambda item: (-item[0], item[1]))
    grouped.sort(key=lambda item: (item[0], -item[1], item[2]))
    return own + [(item[1], item[2], item[3], item[4]) for item in grouped]


def _attachment_group(contributions: list[_Contribution]) -> int:
    """Return the highest documentation or example group that matched.

    Parameters
    ----------
    contributions
        Matching attachments for one record.

    Returns
    -------
    int
        ``0`` for a documentation snippet and ``1`` for an example. The lowest
        number is the highest group. An unknown source sorts last.

    """
    return min(
        (_ATTACHMENT_GROUP.get(item.source, len(_ATTACHMENT_GROUP)) for item in contributions),
        default=len(_ATTACHMENT_GROUP),
    )


def _choose(
    identifier_ids: list[str],
    ranked: list[tuple[float, str, _Record, list[_Contribution]]],
    records: dict[str, _Record],
    kinds: frozenset[str] | None,
    module_name: str,
    limit: int,
) -> list[tuple[str, _Record, list[_Contribution]]]:
    """Place identifier matches ahead of the remaining full-text hits.

    Parameters
    ----------
    identifier_ids
        Exact, suffix, and leaf matches, already in that order.
    ranked
        Full-text hits, highest score first.
    records
        Record details, including identifier matches that full-text missed.
    kinds
        Kind allow-list. ``None`` allows every kind.
    module_name
        Lowercase module segment. Empty allows every record.
    limit
        Maximum number of hits.

    Returns
    -------
    list of tuple
        Record id, record, and the attachments that contributed, identifier
        matches first.

    """
    by_id = {record_id: matched for _score, record_id, _record, matched in ranked}
    chosen: list[tuple[str, _Record, list[_Contribution]]] = []
    seen: set[str] = set()
    for record_id in identifier_ids:
        record = records.get(record_id)
        if record is None or record_id in seen:
            continue
        if not _passes(record_id, record, kinds, module_name):
            continue
        chosen.append((record_id, record, by_id.get(record_id, [])))
        seen.add(record_id)
        if len(chosen) >= limit:
            return chosen
    for _score, record_id, record, matched in ranked:
        if record_id in seen:
            continue
        chosen.append((record_id, record, matched))
        seen.add(record_id)
        if len(chosen) >= limit:
            break
    return chosen


def _execute_in(
    connection: sqlite3.Connection, statement: str, values: Collection[str]
) -> list[sqlite3.Row]:
    """Execute an ``IN`` query with one bound parameter per value.

    Parameters
    ----------
    connection
        Open documentation database.
    statement
        SQL containing the text ``{placeholders}``. That text is replaced with
        one ``?`` per value. The values themselves are bound parameters, not
        interpolated into the statement.
    values
        Bound values for the ``IN`` list. Must be non-empty.

    Returns
    -------
    list of sqlite3.Row
        Rows the statement returns.

    """
    markers = ", ".join("?" * len(values))
    query = statement.replace("{placeholders}", markers)
    return list(connection.execute(query, tuple(values)))


def _remember(
    connection: sqlite3.Connection, record_ids: list[str], records: dict[str, _Record]
) -> None:
    """Load ranking fields for identifier matches the full-text query missed.

    Parameters
    ----------
    connection
        Open documentation database.
    record_ids
        Record ids that are not yet in ``records``.
    records
        Record details filled for each id that exists.

    """
    if not record_ids:
        return
    for row in _execute_in(
        connection,
        """
        SELECT id, kind, summary, status, parent_id
        FROM records
        WHERE id IN ({placeholders})
        """,
        record_ids,
    ):
        records.setdefault(row["id"], _record(row))


def _signatures(connection: sqlite3.Connection, record_ids: list[str]) -> dict[str, str]:
    """Return the signature line for each member.

    Parameters
    ----------
    connection
        Open documentation database.
    record_ids
        Property, method, and enumeration-value ids.

    Returns
    -------
    dict
        Record id to the first line of its body.

    """
    if not record_ids:
        return {}
    return {
        row["id"]: str(row["body"]).partition("\n")[0].strip()
        for row in _execute_in(
            connection,
            "SELECT id, body FROM records WHERE id IN ({placeholders})",
            record_ids,
        )
    }


def _passes(
    record_id: str, record: _Record, kinds: frozenset[str] | None, module_name: str
) -> bool:
    """Return whether one record satisfies the kind and module filters.

    Parameters
    ----------
    record_id
        API record id.
    record
        Ranking fields. ``kind`` is compared with ``kinds``.
    kinds
        Kind allow-list. ``None`` allows every kind.
    module_name
        Lowercase module segment. Empty allows every record.

    Returns
    -------
    bool
        ``True`` when the record may be returned.

    """
    if kinds is not None and record.kind not in kinds:
        return False
    if module_name and module_name not in record_id.lower().split("."):
        return False
    return True


def _value_named(record_id: str, record: _Record, tokens: list[str]) -> bool:
    """Return whether a query names this enumeration value or its enumeration.

    Parameters
    ----------
    record_id
        Enumeration-value id.
    record
        Ranking fields. ``parent_id`` is the enumeration.
    tokens
        Query words.

    Returns
    -------
    bool
        ``True`` when the value's leaf, or its enumeration's leaf, is the query
        or one query word. ``False`` when ``tokens`` is empty.

    """
    if not tokens:
        return False
    if _segments_match(_leaf_of(record_id), tokens):
        return True
    parent_id = record.parent_id
    return parent_id is not None and _segments_match(_leaf_of(parent_id), tokens)


def _segments_match(leaf: str, tokens: list[str]) -> bool:
    """Return whether ``leaf`` is the whole query or one of its words.

    Parameters
    ----------
    leaf
        Unqualified record name.
    tokens
        Query words.

    Returns
    -------
    bool
        ``True`` when the leaf's segments equal ``tokens``, or the leaf is a
        single segment that appears in ``tokens``.

    """
    words = segment_identifier(leaf)
    if not words:
        return False
    if words == tokens:
        return True
    return len(words) == 1 and words[0] in tokens


def _leaf_of(record_id: str) -> str:
    """Return the unqualified name of a record id.

    Parameters
    ----------
    record_id
        API record id.

    Returns
    -------
    str
        The last dotted component.

    """
    return record_id.rsplit(".", 1)[-1]


def _is_single_token(text: str) -> bool:
    """Return whether ``text`` is one identifier rather than a phrase.

    Parameters
    ----------
    text
        Raw query or record id.

    Returns
    -------
    bool
        ``True`` when stripping whitespace leaves a single token.

    """
    stripped = text.strip()
    return bool(stripped) and len(stripped.split()) == 1


def _normalize_identifier(text: str) -> str:
    """Strip whitespace, a trailing dot, and a trailing call suffix.

    Parameters
    ----------
    text
        Raw query or record id.

    Returns
    -------
    str
        The identifier with trailing ``.`` and ``()`` removed. Interior dots
        stay, so a member id keeps its parent.

    """
    normalized = text.strip()
    while normalized:
        if normalized.endswith("()"):
            normalized = normalized[:-2].rstrip()
            continue
        if normalized.endswith("."):
            normalized = normalized[:-1].rstrip()
            continue
        break
    return normalized


def _identifier_ids(connection: sqlite3.Connection, normalized: str) -> list[str]:
    """Return exact, suffix, and leaf matches for one identifier.

    Parameters
    ----------
    connection
        Open documentation database.
    normalized
        Identifier with trailing dots and ``()`` already removed.

    Returns
    -------
    list of str
        Record ids. Exact ids come first, then ids that end with the
        identifier, then leaf and snake_case names. Duplicates are omitted.

    """
    ordered: list[str] = []
    seen: set[str] = set()
    for finder in (_exact_ids, _suffix_ids, _leaf_ids):
        for record_id in finder(connection, normalized):
            if record_id in seen:
                continue
            seen.add(record_id)
            ordered.append(record_id)
    return ordered


def _exact_ids(connection: sqlite3.Connection, normalized: str) -> list[str]:
    """Return records whose id equals ``normalized``, ignoring case.

    Parameters
    ----------
    connection
        Open documentation database.
    normalized
        Identifier to compare with ``records.id``.

    Returns
    -------
    list of str
        Matching record ids in alphabetical order.

    """
    return [
        row["id"]
        for row in connection.execute(
            "SELECT id FROM records WHERE id = ? COLLATE NOCASE ORDER BY id",
            (normalized,),
        )
    ]


def _suffix_ids(connection: sqlite3.Connection, normalized: str) -> list[str]:
    """Return records whose id ends with ``.`` plus ``normalized``.

    Parameters
    ----------
    connection
        Open documentation database.
    normalized
        Identifier suffix. Underscores are matched literally.

    Returns
    -------
    list of str
        Matching record ids in alphabetical order.

    """
    pattern = _like_pattern("%.", normalized)
    return [
        row["id"]
        for row in connection.execute(
            """
            SELECT id FROM records
            WHERE lower(id) LIKE ? ESCAPE '\\'
            ORDER BY id
            """,
            (pattern,),
        )
    ]


def _leaf_ids(connection: sqlite3.Connection, normalized: str) -> list[str]:
    """Return records named like the leaf or the snake_case form.

    Parameters
    ----------
    connection
        Open documentation database.
    normalized
        Identifier. Its last dotted piece and its snake_case form are both
        compared with titles and leaf names.

    Returns
    -------
    list of str
        Matching record ids. Names are tried in leaf, full snake_case, then
        leaf snake_case order.

    """
    names: list[str] = []
    leaf = normalized.rsplit(".", 1)[-1]
    for name in (leaf, _snake(normalized), _snake(leaf)):
        lowered = name.lower()
        if lowered and lowered not in names:
            names.append(lowered)
    found: list[str] = []
    seen: set[str] = set()
    for name in names:
        rows = connection.execute(
            """
            SELECT id FROM records
            WHERE lower(title) = ?
               OR lower(id) = ?
               OR lower(id) LIKE ? ESCAPE '\\'
            ORDER BY id
            """,
            (name, name, _like_pattern("%.", name)),
        )
        for row in rows:
            if row["id"] not in seen:
                seen.add(row["id"])
                found.append(row["id"])
    return found


def _like_pattern(prefix: str, text: str) -> str:
    """Return a LIKE pattern that treats ``%`` and ``_`` in ``text`` as literal.

    Parameters
    ----------
    prefix
        Text placed before the escaped identifier, such as ``%.``.
    text
        Identifier fragment. It is lowercased.

    Returns
    -------
    str
        A pattern for a ``LIKE`` comparison that uses backslash as the escape character.

    """
    escaped = text.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return prefix + escaped


def _snake(identifier: str) -> str:
    """Return the snake_case form of an identifier.

    Parameters
    ----------
    identifier
        Dotted or CamelCase name.

    Returns
    -------
    str
        Segments from ``segment_identifier`` joined with underscores.

    """
    return "_".join(segment_identifier(identifier))


def _resolve_ids(connection: sqlite3.Connection, record_id: str) -> list[str]:
    """Return record ids that a missing details id might have meant.

    Parameters
    ----------
    connection
        Open documentation database.
    record_id
        Id that was not stored exactly.

    Returns
    -------
    list of str
        Matches from the most specific identifier rule that finds any: exact
        id, then id suffix, then leaf name. When that rule finds several and
        exactly one is a class or enumeration whose name is written exactly as
        given, only that one is returned, so ``Body`` means the class rather
        than every ``body`` property. Empty for a phrase.

    """
    normalized = _normalize_identifier(record_id)
    if not normalized or not _is_single_token(normalized):
        return []
    for finder in (_exact_ids, _suffix_ids, _leaf_ids):
        found = finder(connection, normalized)
        if len(found) > 1:
            types = _exact_type_ids(connection, normalized, found)
            if len(types) == 1:
                return types
        if found:
            return found
    return []


def _exact_type_ids(connection: sqlite3.Connection, name: str, record_ids: list[str]) -> list[str]:
    """Return the classes and enumerations in ``record_ids`` whose id ends with ``name``.

    Parameters
    ----------
    connection
        Open documentation database.
    name
        Identifier compared with case, such as ``Body`` or ``designer.Body``.
    record_ids
        Candidate ids.

    Returns
    -------
    list of str
        Matching ids in the order given.

    """
    kinds = {
        row["id"]: row["kind"]
        for row in _execute_in(
            connection, "SELECT id, kind FROM records WHERE id IN ({placeholders})", record_ids
        )
    }
    return [
        record_id
        for record_id in record_ids
        if kinds.get(record_id) in {"class", "enumeration"}
        and (record_id == name or record_id.endswith(f".{name}"))
    ]


def _not_found(
    connection: sqlite3.Connection, record_id: str, record_ids: list[str]
) -> dict[str, object]:
    """Return a not-found result, with up to eight candidate records.

    Parameters
    ----------
    connection
        Open documentation database.
    record_id
        Id the caller passed.
    record_ids
        Candidate record ids, most specific first.

    Returns
    -------
    dict
        ``found`` is ``False``. ``candidates`` lists ``id``, ``kind``, and
        ``summary`` for the first candidates that still exist.

    """
    chosen = record_ids[:_CANDIDATE_LIMIT]
    candidates: list[dict[str, str]] = []
    if chosen:
        rows = {
            row["id"]: row
            for row in _execute_in(
                connection,
                "SELECT id, kind, summary FROM records WHERE id IN ({placeholders})",
                chosen,
            )
        }
        candidates = [
            {"id": item, "kind": rows[item]["kind"], "summary": rows[item]["summary"]}
            for item in chosen
            if item in rows
        ]
    return {"found": False, "id": record_id, "candidates": candidates}


def _parent_ids(body: str) -> list[str]:
    """Return the parent class ids listed in a class body.

    Parameters
    ----------
    body
        Stored class body. Parents are the bullets under ``Inherits from``.

    Returns
    -------
    list of str
        Parent ids in listed order, without duplicates.

    """
    match = _INHERITS_FROM.search(body)
    if match is None:
        return []
    parents: list[str] = []
    for line in match.group("bullets").splitlines():
        if not line.startswith("- "):
            continue
        name = line[2:].strip()
        if name and name not in parents:
            parents.append(name)
    return parents


def _class_members(
    connection: sqlite3.Connection, record_id: str, body: str
) -> list[dict[str, object]]:
    """Return own members, then inherited members that the class does not override.

    Parameters
    ----------
    connection
        Open documentation database.
    record_id
        Class record id.
    body
        Stored class body. ``Inherits from`` names the parents to walk.

    Returns
    -------
    list of dict
        Each entry has ``id``, ``kind``, ``signature``, ``summary``, and
        ``inherited_from``. Own members use ``None``. Inherited members name
        the parent class that defines them. A parent name the class already
        defines is skipped. Cycles in the parent list are ignored.

    """
    result: list[dict[str, object]] = []
    seen_titles: set[str] = set()
    for row in connection.execute(_CLASS_MEMBERS, (record_id,)):
        seen_titles.add(row["title"])
        result.append(_member_entry(row, None))
    queue = _parent_ids(body)
    visited = {record_id}
    while queue:
        parent_id = queue.pop(0)
        if parent_id in visited:
            continue
        visited.add(parent_id)
        for row in connection.execute(_CLASS_MEMBERS, (parent_id,)):
            if row["title"] in seen_titles:
                continue
            seen_titles.add(row["title"])
            result.append(_member_entry(row, parent_id))
        parent = connection.execute(_LOAD_RECORD, (parent_id,)).fetchone()
        if parent is None:
            continue
        for ancestor in _parent_ids(str(parent["body"])):
            if ancestor not in visited:
                queue.append(ancestor)
    return result


def _member_entry(row: sqlite3.Row, inherited_from: str | None) -> dict[str, object]:
    """Return one class-member line.

    Parameters
    ----------
    row
        Property or method row. The first line of the body is the signature.
    inherited_from
        Parent class id, or ``None`` when the member is defined on the class.

    Returns
    -------
    dict
        ``id``, ``kind``, ``signature``, a one-line ``summary``, and
        ``inherited_from``.

    """
    return {
        "id": row["id"],
        "kind": row["kind"],
        "signature": str(row["body"]).partition("\n")[0].strip(),
        "summary": _one_line(str(row["summary"])),
        "inherited_from": inherited_from,
    }


def _one_line(text: str) -> str:
    """Return the first line of ``text`` with its whitespace collapsed.

    Parameters
    ----------
    text
        Summary or other short field.

    Returns
    -------
    str
        The first line, or ``""`` when ``text`` is blank.

    """
    stripped = text.strip()
    if not stripped:
        return ""
    return " ".join(stripped.splitlines()[0].split())
