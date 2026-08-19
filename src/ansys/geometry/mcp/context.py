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

"""Context for PyAnsys Geometry MCP server."""

from dataclasses import dataclass, field
from typing import Any, Optional

from ansys.common.mcp import PyAnsysBaseAppContext
from ansys.geometry.core import Modeler
from ansys.geometry.core.selection_builder.selection_builder import SelectionBuilder


@dataclass
class PyAnsysGeometryContext(PyAnsysBaseAppContext):
    """Application context for PyAnsys Geometry MCP server.

    Attributes
    ----------
    product_instance : Optional[Any]
        The connected product instance.
    mode : Optional[str]
        Launch mode for the geometry service (e.g. ``"docker"``, ``"spaceclaim"``).
    transport_mode : Optional[str]
        Transport mode for the geometry service connection.
    host : str
        Host name or IP address of the geometry service.
    port : int
        Port number of the geometry service.
    connect_to_existing_service : bool
        When ``True``, connect to a running geometry service instead of
        launching a new one.
    selection_registry: Optional[dict[str, Any]]


    Examples
    --------
    >>> context = PyAnsysGeometryContext()
    >>> context.product_instance  # None until product_startup() runs

    """

    product_instance: Optional[Modeler] = None
    mode: Optional[str] = None
    transport_mode: Optional[str] = None
    host: str = "localhost"
    port: int = 50051
    connect_to_existing_service: bool = False
    selection_registry: dict[str, SelectionBuilder] = field(default_factory=dict)
