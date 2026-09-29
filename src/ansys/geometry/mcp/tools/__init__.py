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

"""General MCP tools package.

Importing this package registers every ``@app.tool()`` defined in its submodules.
"""

from ansys.geometry.mcp.misc.auxiliary import get_geometry_ctx
from ansys.geometry.mcp.tools.edit_tools import intersect_body, subtract_body, unite_body
from ansys.geometry.mcp.tools.modeling_tools import (
    add_component,
    create_box,
    extrude_sketch,
    move_body_to_component,
    revolve_sketch,
)
from ansys.geometry.mcp.tools.selection_tools import (
    create_named_selection,
    create_selection_builder,
    extend_selection,
    filter_entities,
    group_entities,
    list_entities,
    order_entities,
    select_entities,
)
from ansys.geometry.mcp.tools.session_tools import (
    create_design,
    export_design_to,
    get_command_history,
    get_design_info,
    get_product_status,
    get_transcript,
    import_geometry_file,
    run_python_code,
    run_script_file,
)
from ansys.geometry.mcp.tools.visualization_tools import (
    get_design_3d_scene,
    get_screenshot,
    read_image_in_base64,
)
