Currently supported APIs
========================

This page lists the MCP tools currently registered by the server in
``ansys.geometry.mcp.tools``.

.. TODO: Replace this section with your actual tool list.
   Use the format below for each tool.

Tool list
---------

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

When the MCP server starts, it launches the product backend. During
this startup phase, tools may return a message indicating the product
is still connecting. If this happens, retry the tool call after a short
wait.
