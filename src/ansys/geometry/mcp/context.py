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

"""Context for PyAnsys Geometry MCP server."""

from dataclasses import dataclass, field
from typing import Optional

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
    proto_version : str
        Geometry service protocol version for an existing service connection.
    host : str
        Host name or IP address of the geometry service.
    port : int
        Port number of the geometry service.
    uds_dir : Optional[str]
        Directory for the Unix Domain Socket.
    uds_id : Optional[str]
        Optional identifier for the Unix Domain Socket filename.
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
    proto_version: str = "v1"
    host: str = "localhost"
    port: int = 50051
    uds_dir: Optional[str] = None
    uds_id: Optional[str] = None
    connect_to_existing_service: bool = False
    selection_registry: dict[str, SelectionBuilder] = field(default_factory=dict)
