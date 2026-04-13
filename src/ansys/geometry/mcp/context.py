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

"""Context for PyAnsys Geometry MCP server."""

from dataclasses import dataclass
from typing import Any, Optional

from ansys.common.mcp import PyAnsysBaseAppContext


@dataclass
class PyAnsysGeometryContext(PyAnsysBaseAppContext):
    """Application context for PyAnsys Geometry MCP server.

    Attributes
    ----------
    product_instance : Optional[Any]
        The connected product instance.

    Notes
    -----
    Add any additional product-specific attributes here.
    For example, if your product exposes a model or session object,
    add it as a field with a default value of ``None``.

    Examples
    --------
    >>> context = PyAnsysGeometryContext()
    >>> context.product_instance  # None until product_startup() runs
    """

    product_instance: Optional[Any] = None

    # TODO: Add more product-specific fields as needed.
    # Example:
    # model: Optional[Any] = None
    # session: Optional[Any] = None
