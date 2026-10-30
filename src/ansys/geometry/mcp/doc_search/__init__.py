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

"""Offline search over the bundled PyAnsys Geometry documentation database.

``query``, ``schema``, and ``terms`` are copied from the
``pygeometry-mcp-docs-bundler`` project, which also builds the database. Update
them by copying them again rather than editing them here.

The database ships gzip-compressed as :data:`COMPRESSED_BUNDLE_PATH`. The first
call to :func:`open_bundle` decompresses it into a per-user cache directory and
later calls reuse that copy. No geometry service and no network access are
required to query it.
"""

import gzip
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

from ansys.geometry.mcp.doc_search.query import get_api_details, suggest_api
from ansys.geometry.mcp.doc_search.schema import open_database

#: Location of the gzip-compressed documentation bundle shipped in the wheel.
COMPRESSED_BUNDLE_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "pygeometry-docs.sqlite.gz"
)

#: Environment variable overriding the directory used for the decompressed cache.
CACHE_DIR_ENV = "ANSYS_GEOMETRY_MCP_CACHE"

__all__ = [
    "CACHE_DIR_ENV",
    "COMPRESSED_BUNDLE_PATH",
    "cache_dir",
    "get_api_details",
    "open_bundle",
    "open_database",
    "suggest_api",
]


def cache_dir() -> Path:
    """Return the directory that holds the decompressed documentation bundle.

    Returns
    -------
    pathlib.Path
        The ``ANSYS_GEOMETRY_MCP_CACHE`` environment variable when set,
        otherwise a per-user cache location for the operating system.

    """
    override = os.environ.get(CACHE_DIR_ENV)
    if override:
        return Path(override)
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
    else:
        root = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
    return Path(root) / "ansys-geometry-mcp" / "doc_bundle"


def _cache_file() -> Path:
    """Return the path of the decompressed bundle for the shipped archive.

    The name embeds the archive size and modification time, so a different
    bundle never reuses an old cache file.

    Returns
    -------
    pathlib.Path
        Path to the decompressed SQLite file inside :func:`cache_dir`.

    """
    stat = COMPRESSED_BUNDLE_PATH.stat()
    key = f"{stat.st_size}-{int(stat.st_mtime)}"
    return cache_dir() / f"pygeometry-docs-{key}.sqlite"


def _ensure_bundle() -> Path:
    """Decompress the documentation bundle on first use and cache the result.

    The archive is decompressed into a temporary file in the cache directory and
    then moved into place, so concurrent callers never see a partial database.

    Returns
    -------
    pathlib.Path
        Path to the decompressed SQLite database.

    Raises
    ------
    FileNotFoundError
        The compressed bundle is not present next to the package.
    OSError
        The archive could not be read or the cache could not be written.

    """
    target = _cache_file()
    if target.is_file():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as destination:
            with gzip.open(COMPRESSED_BUNDLE_PATH, "rb") as source:
                shutil.copyfileobj(source, destination, length=1 << 20)
        Path(temporary).replace(target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return target


def open_bundle() -> sqlite3.Connection:
    """Open the documentation bundle shipped with the MCP server.

    Returns
    -------
    sqlite3.Connection
        Connection to the documentation database. Rows support access by
        column name. The caller must close it.

    Raises
    ------
    FileNotFoundError
        The compressed bundle is not present next to the package.
    OSError
        The archive could not be read or the cache could not be written.
    ValueError
        The bundle stores an unsupported schema version.

    """
    return open_database(_ensure_bundle(), create=False)
