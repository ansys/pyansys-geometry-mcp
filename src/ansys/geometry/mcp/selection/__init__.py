# Copyright (C) 2026 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
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

"""MCP selection tools subpackage.

Provides an extensible, registry-based selection pipeline for building body,
face, and edge selections (with cross-type transitions) exposed as MCP tools
in :mod:`ansys.geometry.mcp.selection.tools`.

Adding a new entity type requires: create a new handler module implementing
``BaseSelectionHandler``, decorate it with ``@register_handler``, import it
here, and update the ``build_selection`` docstring in ``tools.py``. No changes
to the base infrastructure are needed.
"""

from ansys.geometry.mcp.selection._base import (
    HANDLER_REGISTRY,
    ActionSpec,
    BaseSelectionHandler,
    register_handler,
    transition,
)

# Importing these modules registers each handler into HANDLER_REGISTRY as a
# side effect of the `@register_handler` class decorator.
from ansys.geometry.mcp.selection._body import BodySelectionHandler
from ansys.geometry.mcp.selection._edge import EdgeSelectionHandler
from ansys.geometry.mcp.selection._face import FaceSelectionHandler

__all__ = [
    "ActionSpec",
    "BaseSelectionHandler",
    "BodySelectionHandler",
    "FaceSelectionHandler",
    "EdgeSelectionHandler",
    "HANDLER_REGISTRY",
    "register_handler",
    "transition",
]
