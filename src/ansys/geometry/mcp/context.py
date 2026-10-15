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

"""Context for PyAnsys Geometry-MCP server."""

from dataclasses import dataclass, field
from typing import Optional

from ansys.common.mcp import PyAnsysBaseAppContext
from ansys.geometry.core import Modeler
from ansys.geometry.core.selection_builder.selection_builder import SelectionBuilder


@dataclass
class PyAnsysGeometryContext(PyAnsysBaseAppContext):
    """App context for PyAnsys Geometry-MCP server.

    Attributes
    ----------
    product_instance : [Any], default: None
        Connected product instance.
    mode : default: str, default: None
        Launch mode for the geometry service (such as ``"docker"`` or ``"spaceclaim"``).
    transport_mode : str, default: None
        Transport mode for the geometry service connection.
    proto_version : str, default: ``"v1"``
        Geometry service protocol version for an existing service connection.
    geometry_host : str, default: ``"localhost"``
        Host name or IP address of the geometry service.
    geometry_port : int
        Port number of the geometry service.
    uds_dir : str, default: None
        Directory for the Unix domain socket.
    uds_id : str, default: None
        Optional identifier for the Unix domain socket filename.
    connect_to_existing_service : bool, default: False
        Whether to connect to a running geometry service. When ``False``, a new geometry service is launched.
    log_level : str, default: ``"INFO"``
        Logging level for the MCP server.
    log_file : str, default: None
        Optional path to a file that receives server logs.
    selection_registry : dict[str, SelectionBuilder], default: None
        Registry mapping selection IDs to their corresponding selection builders. If no registry is provided, an empty dictionary is used.

    Examples
    --------
    >>> context = PyAnsysGeometryContext()
    >>> context.product_instance  # None until product_startup() runs

    """

    product_instance: Optional[Modeler] = None
    mode: Optional[str] = None
    transport_mode: Optional[str] = None
    proto_version: str = "v1"
    geometry_host: str = "localhost"
    geometry_port: int = 50051
    uds_dir: Optional[str] = None
    uds_id: Optional[str] = None
    connect_to_existing_service: bool = False
    selection_registry: dict[str, SelectionBuilder] = field(default_factory=dict)
    log_level: str = "INFO"
    log_file: Optional[str] = None
