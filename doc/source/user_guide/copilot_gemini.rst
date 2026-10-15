Connect GitHub Copilot and Gemini
=================================

You can connect PyAnsys Geometry-MCP to GitHub Copilot, Gemini, or both. You must configure the server separately in each client.

Start the server
----------------

Each client uses this command to start its own MCP server:

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

Add this configuration to the ``.gemini/settings.json`` file:

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

After you connect the MCP server, ask the assistant to call one of its tools.

.. TODO: Add example prompts specific to your product tools. For example:
..
.. - "Run <tool_name> with parameter X."
.. - "Get the current state of the model."

Troubleshooting
---------------

The MCP server does not respond
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Confirm that you have met all product prerequisites, including license
  and service requirements.
- Confirm that you installed PyAnsys Geometry (``ansys-geometry-core``)
  in your virtual vironment.
- Confirm that the Python executable in your MCP configuration belongs to the
  correct virtual environment.

The tool returns a startup or connection error
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Review the server logs to confirm that the Ansys Geometry backend backend
  started successfully.
- Restart the MCP client session to relaunch the server.
