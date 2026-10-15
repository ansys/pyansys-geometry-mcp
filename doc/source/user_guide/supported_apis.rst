Supported APIs
==============

Use this page to browse the MCP tools registered in ``ansys.geometry.mcp.tools``.

.. TODO: Replace this section with your tool list.
    Use the following format for each tool.

Tools
-----

.. TODO: Document each tool with the following signature format.

``example_tool(param: str) -> str``
    Describe what this tool does.

.. Add more tools following this pattern:
.. ``tool_name(param1: type, param2: type = default) -> return_type``
..     Description.

Usage patterns
--------------

.. TODO: Describe recommended sequences for calling your tools.

Startup behavior
^^^^^^^^^^^^^^^^

When you start PyAnsys Geometry-MCP, it launches the product backend.
If a tool reports that the backend is still connecting, wait briefly, then
call the tool again.
