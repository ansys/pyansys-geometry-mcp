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

"""Identifier splitting and search-query preparation.

The SQLite ``unicode61`` tokenizer splits on dots and underscores, but not on case changes.
``DesignPoint`` would otherwise be one token, so a query for ``point`` would miss it.
"""

from __future__ import annotations

import re

__all__ = ["STOP_WORDS", "prepare_query", "query_tokens", "segment_identifier"]

# Words that match almost every record when a query is an OR of its tokens.
# ``ansys``, ``geometry``, and ``core`` are the package prefix on every API id.
STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "ansys",
        "are",
        "as",
        "at",
        "be",
        "been",
        "by",
        "core",
        "do",
        "does",
        "for",
        "from",
        "geometry",
        "how",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "what",
        "which",
        "with",
    }
)

# Dots and underscores are included so this split agrees with the tokenizer. The extra
# punctuation shows up in snippet association identifiers.
_SEPARATORS = re.compile(r"""[.\-_/\\~|,;:()\[\]{}<>"'`=*&!?+\u2018\u2019\u201c\u201d\s]+""")

# Split before a capital that starts a new word, and between a run of capitals and the
# capitalised word that follows it. The second case keeps acronyms whole: "UVParameter"
# yields "UV" and "Parameter" rather than one letter at a time.
_CASE_BOUNDARY = re.compile(
    r"""
    (?<=[a-z0-9])(?=[A-Z])
    | (?<=[A-Z])(?=[A-Z][a-z])
    | (?<=[a-zA-Z])(?=[0-9])
    """,
    re.VERBOSE,
)

_QUERY_TOKEN = re.compile(r"\S+")
_EDGE_PUNCTUATION = re.compile(r"^[^\w\"]+|[^\w\"]+$")


def segment_identifier(identifier: str) -> list[str]:
    """Split an identifier into searchable words.

    Parameters
    ----------
    identifier
        Dotted, underscored, or CamelCase name.

    Returns
    -------
    list of str
        Lowercase words in order of first appearance, without duplicates. Single-character
        parts are omitted.

    Examples
    --------
    >>> segment_identifier("DesignPoint")
    ['design', 'point']

    """
    parts: list[str] = []
    for chunk in _SEPARATORS.split(identifier):
        for word in _CASE_BOUNDARY.split(chunk):
            lowered = word.lower()
            if len(lowered) > 1 and lowered not in parts:
                parts.append(lowered)
    return parts


def query_tokens(text: str) -> list[str]:
    """Split a query into searchable words.

    Parameters
    ----------
    text
        Raw query text.

    Returns
    -------
    list of str
        Lowercase words from ``segment_identifier``, with stop words removed.
        Dotted and CamelCase names become their separate words. A CamelCase
        token is also kept whole, so a class name such as ``DesignPoint`` still
        matches. Single-character parts are omitted. Empty when every word is a
        stop word or the text is blank.

    """
    tokens: list[str] = []
    for match in _QUERY_TOKEN.finditer(text):
        word = _EDGE_PUNCTUATION.sub("", match.group())
        if not word:
            continue
        parts = segment_identifier(word)
        for token in parts:
            if token in STOP_WORDS or token in tokens:
                continue
            tokens.append(token)
        # A CamelCase token is also kept whole so it matches an indexed leaf name as written.
        # Dotted and underscored names are already split the way the tokenizer splits them.
        if len(parts) > 1 and _SEPARATORS.search(word) is None:
            whole = word.lower()
            if whole not in STOP_WORDS and whole not in tokens:
                tokens.append(whole)
    return tokens


def prepare_query(text: str) -> str:
    """Turn a query into an FTS5 ``OR`` expression.

    Parameters
    ----------
    text
        Raw query text.

    Returns
    -------
    str
        Quoted tokens joined with ``OR``, with stop words removed. Empty when every token
        is a stop word or the text is blank. A double quote inside a token is doubled so
        FTS5 reads it as part of the token. Each whitespace-separated word is split with
        ``segment_identifier`` first, so a dotted or CamelCase name matches its parts.

    """
    return " OR ".join(_quote(token) for token in query_tokens(text))


def _quote(token: str) -> str:
    """Return an FTS5 string literal for one token.

    Parameters
    ----------
    token
        One lowercase query token.

    Returns
    -------
    str
        The token wrapped in double quotes, with any inner quote doubled.

    """
    return '"' + token.replace('"', '""') + '"'
