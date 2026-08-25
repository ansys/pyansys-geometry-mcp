.. _ref_getting_started:

Getting started
===============

This section describes how to install PyAnsys Geometry MCP in user mode.
If you are interested in contributing to PyAnsys Geometry MCP, see
:ref:`contribute` for information on installing in developer mode.

Installation
------------

To use `pip <https://pypi.org/project/pip/>`_ to install PyAnsys Geometry MCP,
run this command:

.. code:: bash

    pip install pyansys-geometry-mcp

Alternatively, to install the latest version from this library's
`GitHub repository <https://github.com/ansys/pyansys-geometry-mcp/>`_,
run these commands:

.. code:: bash

    git clone https://github.com/ansys/pyansys-geometry-mcp
    cd pyansys-geometry-mcp
    pip install .

Client setup (Copilot and Gemini)
----------------------------------

After installing the package, configure your MCP client to launch the server
with:

.. code:: text

    python -m ansys.geometry.mcp

GitHub Copilot (VS Code)
^^^^^^^^^^^^^^^^^^^^^^^^^

1. Open or create ``.vscode/mcp.json`` in your workspace.
2. Add a server entry for ``pyansys-geometry-mcp``.
3. Point ``command`` to your Python executable and set ``args`` to
   ``["-m", "ansys.geometry.mcp"]``.

Example:

.. code-block:: json

    {
      "servers": {
        "pyansys-geometry-mcp": {
          "type": "stdio",
          "command": "<path-to-python>",
          "args": ["-m", "ansys.geometry.mcp"]
        }
      },
      "inputs": []
    }

Gemini
^^^^^^

1. Open or create ``.gemini/settings.json``.
2. Add an MCP server entry named ``pyansys-geometry-mcp``.
3. Use the same command and arguments as Copilot.

Example:

.. code-block:: json

    {
      "mcpServers": {
        "pyansys-geometry-mcp": {
          "command": "<path-to-python>",
          "args": ["-m", "ansys.geometry.mcp"],
          "trust": true
        }
      }
    }

Verification
^^^^^^^^^^^^

After configuration, start a chat in your client and ask it to call one of
the available tools. If the product backend is still starting, retry after
a few seconds.
