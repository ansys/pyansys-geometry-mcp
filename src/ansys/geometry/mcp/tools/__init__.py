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
)
from ansys.geometry.mcp.tools.visualization_tools import (
    get_design_3d_scene,
    get_screenshot,
    read_image_in_base64,
)
