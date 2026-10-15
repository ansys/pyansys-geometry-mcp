.. _ref_user_guide:


User guide
==========

This section explains:

- What PyAnsys Geometry-MCP does and lists its run-time requirements.
- Which APIs (MCP tools) are currently supported.
- How to connect the server to both GitHub Copilot and Gemini.

What PyAnsys Geometry-MCP does
------------------------------

PyAnsys Geometry-MCP exposes workflows from `PyAnsys Geometry <https://github.com/ansys/pyansys-geometry>`_ (``ansys-geometry-core``) through MCP tools.
When connected to an MCP-capable assistant, you can ask the AI to perform
tasks using these tools.

Runtime requirements
--------------------

- Python 3.10 or later
- A working installation of `PyAnsys Geometry <https://github.com/ansys/pyansys-geometry>`_.

.. TODO: Add product-specific runtime requirements (such as Docker and license
   server) here.

.. toctree::
   :hidden:
    :maxdepth: 2

    supported_apis
    copilot_gemini