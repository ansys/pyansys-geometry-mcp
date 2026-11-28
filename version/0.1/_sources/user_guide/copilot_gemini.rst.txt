Connect GitHub Copilot and Gemini
=================================

You can connect PyAnsys Geometry-MCP to GitHub Copilot, Gemini, or both. You must configure the server separately in each client.

Start the server
----------------

Start the MCP server with this command:

.. code-block:: text

    python -m ansys.geometry.mcp

GitHub Copilot (Visual Studio Code)
-----------------------------------

Add this configuration to your workspace MCP configuration file (``.vscode/mcp.json``):

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

Use tools in chat
-----------------

After you connect to the MCP server, ask your assistant to call one of its tools.

Example prompts
---------------

Try prompts such as:

- "What bodies are in the active design?" to use ``list_entities``.
- "Inspect the active design for geometry issues." to use ``inspect_geometry``.
- "Create a named selection containing the bodies named Housing and Cover."
  to use ``create_named_selection``.
- "Create a 10 mm fillet on the edges of the Housing body." If no dedicated
  tool supports the requested operation, use ``run_python`` with the
  PyAnsys Geometry API.

Troubleshooting
---------------

The MCP server does not respond
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Confirm that you have met all product prerequisites, including license
  and service requirements.
- Confirm that you installed PyAnsys Geometry (``ansys-geometry-core``)
  in your virtual environment.
- Confirm that the Python executable in your MCP configuration belongs to the
  correct virtual environment.

The tool returns a startup or connection error
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Review the server logs to confirm that the Ansys Geometry backend
  started successfully.
- Restart the MCP client session to relaunch the server.
