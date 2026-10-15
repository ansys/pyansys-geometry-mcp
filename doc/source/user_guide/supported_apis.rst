Supported APIs
==============

Use this page to find the MCP tools registered in ``ansys.geometry.mcp.tools``.

.. TODO: Replace this section with your actual tool list.
   Use the format below for each tool.

Tools
-----

.. TODO: Document each tool using the signature format below.

``example_tool(param: str) -> str``
    Short description of what this tool does.

.. Add more tools following this pattern:
.. ``tool_name(param1: type, param2: type = default) -> return_type``
..     Description.

Usage patterns
--------------

.. TODO: Describe recommended sequences for calling your tools.

Startup behavior
^^^^^^^^^^^^^^^^

When you start PyAnsys Geometry-MCP, it launches the product backend. A
tool might report that the backend is still connecting. If it does, wait
briefly, then call the tool again.
