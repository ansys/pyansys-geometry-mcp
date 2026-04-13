Using with Copilot and Gemini
=============================

This guide shows how to connect the PyAnsys Geometry MCP server to both
GitHub Copilot and Gemini clients.

Start command
-------------

Both clients launch the same MCP server command:

.. code-block:: text

    python -m ansys.geometry.mcp

GitHub Copilot (VS Code)
------------------------

Add this configuration to your workspace MCP file (``.vscode/mcp.json``):

.. code-block:: json

    {
      "servers": {
        "pyansys-geometry-mcp": {
          "type": "stdio",
          "command": "<path-to-your-venv-python>",
          "args": ["-m", "ansys.geometry.mcp"]
        }
      },
      "inputs": []
    }

Gemini
------

Add this configuration to ``.gemini/settings.json``:

.. code-block:: json

    {
      "mcpServers": {
        "pyansys-geometry-mcp": {
          "command": "<path-to-your-venv-python>",
          "args": ["-m", "ansys.geometry.mcp"],
          "trust": true
        }
      }
    }

How to use from chat
---------------------

After the MCP server is connected, ask the assistant to call tools.

.. TODO: Add example prompts specific to your product tools. For example:
..
.. - "Run <tool_name> with parameter X."
.. - "Get the current state of the model."

Troubleshooting
---------------

Server does not respond
^^^^^^^^^^^^^^^^^^^^^^^

- Confirm all product prerequisites are met (licenses, services, etc.).
- Confirm ``ansys-geometry-core`` is installed in the selected environment.
- Confirm the Python path in your MCP configuration points to the correct virtual environment.

Tool returns a startup/connection error
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Check that the product backend launched successfully by reviewing server logs.
- Restart the MCP client session so the server relaunches.
