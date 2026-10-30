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

"""SQLite schema, transactions, and full-text indexes.

``open_database`` is the only way to open the documentation file. Creating a
missing file also creates its parent directories and writes ``schema_version``
into ``metadata``. Opening a file that already exists leaves its rows in place.

``metadata`` also holds one ingest fact per source, under the keys
``{source}.input_path``, ``{source}.ingest_time``, ``{source}.record_count``,
and ``{source}.link_count``. Sources are ``api_reference``, ``examples``, and
``doc_snippets``.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3

from ansys.geometry.mcp.doc_search.terms import segment_identifier

__all__ = [
    "SCHEMA_VERSION",
    "open_database",
    "rebuild_fts",
    "transaction",
]

# The MCP server compares this value before it reads a database.
SCHEMA_VERSION = 1

_SCHEMA_VERSION_KEY = "schema_version"
_PACKAGE_PREFIX = "ansys.geometry.core."

_MEMBER_KINDS = frozenset({"property", "method", "value"})

# Standalone FTS tables, refilled by ``rebuild_fts``. ``terms`` is computed
# here rather than stored on the row, so the indexed segments stay aligned
# with ``segment_identifier``.
_RECORDS_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5 (
    id UNINDEXED,
    leaf_name,
    title,
    summary,
    terms,
    signature,
    description,
    tokenize = 'porter unicode61'
)
"""

_ATTACHMENTS = """
CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL CHECK (source IN ('examples', 'doc_snippets')),
    batch TEXT NOT NULL,
    body TEXT NOT NULL
)
"""

_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS records (
        id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        source TEXT NOT NULL CHECK (source IN ('api_reference')),
        parent_id TEXT,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        body TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT ''
            CHECK (status IN ('', 'obsolete', 'deprecated', 'internal'))
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS records_by_source ON records (source)
    """,
    """
    CREATE INDEX IF NOT EXISTS records_by_parent ON records (parent_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS api_cross_references (
        record_id TEXT PRIMARY KEY,
        returned_by TEXT NOT NULL,
        accepted_by TEXT NOT NULL,
        FOREIGN KEY (record_id) REFERENCES records (id) ON DELETE CASCADE
    )
    """,
    _ATTACHMENTS,
    """
    CREATE INDEX IF NOT EXISTS attachments_by_batch ON attachments (source, batch)
    """,
    """
    CREATE TABLE IF NOT EXISTS attachment_links (
        attachment_id INTEGER NOT NULL,
        record_id TEXT NOT NULL,
        weight REAL NOT NULL,
        PRIMARY KEY (attachment_id, record_id),
        FOREIGN KEY (attachment_id) REFERENCES attachments (id) ON DELETE CASCADE
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS attachment_links_by_record ON attachment_links (record_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    _RECORDS_FTS,
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS attachments_fts USING fts5 (
        attachment_id UNINDEXED,
        source UNINDEXED,
        body,
        terms,
        tokenize = 'porter unicode61'
    )
    """,
)


def open_database(path: Path, *, create: bool) -> sqlite3.Connection:
    """Open the documentation database.

    Parameters
    ----------
    path
        Path to the SQLite file.
    create
        When ``True``, create the file and any missing parent directories, then
        initialize the schema. When ``False``, a missing file is an error and
        nothing is created. An existing file is opened without removing its rows.

    Returns
    -------
    sqlite3.Connection
        Connection to the documentation database. The connection is in autocommit
        mode; ``transaction`` is what groups an ingest into one commit. Rows
        support access by column name.

    Raises
    ------
    FileNotFoundError
        ``create`` is ``False`` and ``path`` is not an existing file.
    ValueError
        The file stores a schema version other than the current one.

    """
    path = Path(path)
    if not path.is_file():
        if not create:
            raise FileNotFoundError(f"database file does not exist: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)

    # Autocommit so ``transaction`` can own BEGIN/COMMIT. The default isolation
    # level would open a transaction on the first write and make that BEGIN fail.
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        _ensure_schema(connection)
    except Exception:
        connection.close()
        raise
    return connection


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run one ingest so a failure leaves the previous content in place.

    Parameters
    ----------
    connection
        Open documentation database.

    Yields
    ------
    sqlite3.Connection
        The same connection, inside a transaction that commits on success and
        rolls back when the body raises.

    """
    connection.execute("BEGIN")
    try:
        yield connection
    except BaseException:
        connection.rollback()
        raise
    else:
        connection.commit()


def rebuild_fts(connection: sqlite3.Connection) -> None:
    """Rebuild both full-text indexes from the current tables.

    The record index stores the leaf name, title, summary, identifier segments,
    signature, and description. An Examples section stays in the description.
    The attachment index stores the attachment text and its identifier
    segments. Both use the ``porter unicode61`` tokenizer, so a
    stemmed query matches the original word. Segments from
    ``segment_identifier`` are what make a CamelCase name match its separate
    words.

    Parameters
    ----------
    connection
        Open documentation database. Writes join a transaction already started
        by ``transaction``.

    """
    records = connection.execute("SELECT id, kind, title, summary, body FROM records").fetchall()
    connection.execute("DELETE FROM records_fts")
    connection.executemany(
        """
        INSERT INTO records_fts (
            id, leaf_name, title, summary, terms, signature, description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [_record_index_row(row) for row in records],
    )

    attachments = connection.execute("SELECT id, source, body FROM attachments").fetchall()
    connection.execute("DELETE FROM attachments_fts")
    connection.executemany(
        """
        INSERT INTO attachments_fts (attachment_id, source, body, terms)
        VALUES (?, ?, ?, ?)
        """,
        [(row["id"], row["source"], row["body"], _terms(row["body"])) for row in attachments],
    )


def _ensure_schema(connection: sqlite3.Connection) -> None:
    """Create any missing tables and store the schema version.

    Parameters
    ----------
    connection
        Open documentation database.

    Raises
    ------
    ValueError
        The file already stores a schema version other than the current one.

    """
    current = _stored_schema_version(connection)
    if current is not None and current != str(SCHEMA_VERSION):
        raise ValueError(
            f"database schema version {current} is not supported; create a new database"
        )
    for statement in _STATEMENTS:
        connection.execute(statement)
    _store_schema_version(connection)


def _stored_schema_version(connection: sqlite3.Connection) -> str | None:
    """Return the stored schema version, or ``None`` when the file has none.

    Parameters
    ----------
    connection
        Open documentation database. A file that has no ``metadata`` table is
        a new database and returns ``None`` without creating that table.

    """
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'metadata'"
    ).fetchone()
    if exists is None:
        return None
    row = connection.execute(
        "SELECT value FROM metadata WHERE key = ?",
        (_SCHEMA_VERSION_KEY,),
    ).fetchone()
    if row is None:
        return None
    return row["value"]


def _store_schema_version(connection: sqlite3.Connection) -> None:
    """Write the current schema version when it is missing.

    Parameters
    ----------
    connection
        Open documentation database. A database that already stores the
        current version is left unchanged, so opening it does not write.

    """
    current = connection.execute(
        "SELECT value FROM metadata WHERE key = ?",
        (_SCHEMA_VERSION_KEY,),
    ).fetchone()
    if current is not None:
        return
    connection.execute(
        """
        INSERT INTO metadata (key, value)
        VALUES (?, ?)
        """,
        (_SCHEMA_VERSION_KEY, str(SCHEMA_VERSION)),
    )


def _indexed_body(kind: str, body: str) -> tuple[str, str]:
    """Split a stored body into its signature and description.

    Parameters
    ----------
    kind
        Record kind. Properties, methods, and enumeration values take their
        signature from the first line. Classes and enumerations have no
        signature line.
    body
        Stored body. An Examples section stays in the description.

    Returns
    -------
    tuple of (str, str)
        Signature and description.

    """
    text = body.replace("\r\n", "\n")
    if kind in _MEMBER_KINDS:
        signature, _separator, description = text.partition("\n")
        return signature.strip(), description.strip()
    return "", text.strip()


def _without_package_prefix(text: str) -> str:
    """Remove a leading ``ansys.geometry.core.`` prefix from an identifier.

    Parameters
    ----------
    text
        Record id or title. A class title is the dotted name, so it can carry
        the same prefix as the id.

    Returns
    -------
    str
        ``text`` without that prefix. Other text is returned unchanged. The
        stored id and title columns are not modified.

    """
    if text.startswith(_PACKAGE_PREFIX):
        return text[len(_PACKAGE_PREFIX) :]
    return text


def _leaf_name(record_id: str) -> str:
    """Return the short name indexed at the highest weight.

    Parameters
    ----------
    record_id
        API record id.

    Returns
    -------
    str
        The last dotted component. A class leaf is the class name, and a
        member leaf is the member name, so a query for the class does not give
        every member the same name weight.

    """
    return record_id.rsplit(".", 1)[-1]


def _terms(*texts: str) -> str:
    """Join identifier segments from ``texts`` in order of first appearance.

    Parameters
    ----------
    *texts
        Identifier-bearing fields. Empty strings contribute nothing.

    Returns
    -------
    str
        Space-separated lowercase segments, without duplicates.

    """
    parts: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for part in segment_identifier(text):
            if part not in seen:
                seen.add(part)
                parts.append(part)
    return " ".join(parts)


def _record_index_row(row: sqlite3.Row) -> tuple[str, str, str, str, str, str, str]:
    """Return one record-index row.

    Parameters
    ----------
    row
        Record row with ``id``, ``kind``, ``title``, ``summary``, and ``body``.

    Returns
    -------
    tuple
        Values for one ``records_fts`` insert.

    """
    signature, description = _indexed_body(row["kind"], row["body"])
    return (
        row["id"],
        _leaf_name(row["id"]),
        row["title"],
        row["summary"],
        _terms(_without_package_prefix(row["id"]), _without_package_prefix(row["title"])),
        signature,
        description,
    )
