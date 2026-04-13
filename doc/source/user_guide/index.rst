.. _ref_user_guide:


User guide
==========

The PyAnsys Geometry MCP user guide explains:

- What this MCP server does and what it needs to run.
- Which APIs (MCP tools) are currently supported.
- How to connect the server to both GitHub Copilot and Gemini.

What this server provides
--------------------------

PyAnsys Geometry MCP exposes workflows from
``ansys-geometry-core`` through MCP tools.
When connected to an MCP-capable assistant, you can ask the AI to perform
tasks using the registered tools.

Runtime requirements
--------------------

- Python 3.10 or newer.
- A working installation of ``ansys-geometry-core``.

.. TODO: Add product-specific runtime requirements (e.g., Docker, license
   server, etc.) here.

Guide contents
--------------

.. toctree::
    :maxdepth: 2

    supported_apis
    copilot_gemini
