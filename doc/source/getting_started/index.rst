.. _ref_getting_started:

Getting started
===============

This section explains how to install PyAnsys Geometry-MCP in user mode.
If you are interested in contributing to PyAnsys Geometry-MCP, see
:ref:`contribute` for information on installing in developer mode.

Installation
------------

PyAnsys Geometry-MCP requires Python 3.12 or later. Install it into a
dedicated virtual environment so that its dependencies do not conflict with
other Python packages on your system.

To create and activate a virtual environment, run these commands:

.. tab-set::

    .. tab-item:: Windows

        .. code:: bash

            python -m venv .venv
            .venv\Scripts\activate

    .. tab-item:: Linux/macOS

        .. code:: bash

            python -m venv .venv
            source .venv/bin/activate

With the virtual environment activated, use `pip <https://pypi.org/project/pip/>`_
to install PyAnsys Geometry-MCP by running this command:

.. code:: bash

    pip install ansys-geometry-mcp

Alternatively, to install the current development version from this library's
`GitHub repository <https://github.com/ansys/pyansys-geometry-mcp/>`_,
run these commands:

.. code:: bash

    git clone https://github.com/ansys/pyansys-geometry-mcp
    cd pyansys-geometry-mcp
    pip install .

Client setup (Copilot and Gemini)
---------------------------------

PyAnsys Geometry-MCP supports two transports for communicating with your MCP
client:

- **stdio** (default): Your MCP client starts the server as a subprocess and
  communicates with it through standard input and output. This is the simplest
  option for local use.
- **HTTP**: You start the server yourself, and your MCP client connects to it
  through a URL.

Startup options
^^^^^^^^^^^^^^^

Both transports accept the same startup options, such as ``--mode`` to choose
the geometry backend or ``--log-level`` to control logging. To see all available
startup options and their defaults, run this command using the Python
interpreter where you installed the package:

.. code:: bash

    python -m ansys.geometry.mcp --help

Stdio transport
^^^^^^^^^^^^^^^

With the stdio transport, configure your MCP client to start the server
with this command:

.. code:: text

    python -m ansys.geometry.mcp

GitHub Copilot (Visual Studio Code) with stdio
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Open or create ``.vscode/mcp.json`` in your workspace. Alternatively, you
   can use a ``.mcp.json`` file at the root of your workspace.
2. Add a server entry for ``pyansys-geometry-mcp``.
3. Set ``type`` to ``"stdio"``.
4. Set ``command`` to the path to the Python interpreter where you installed
   the package. If you installed it in the virtual environment described in
   `Installation`_, this path looks like ``.venv\Scripts\python.exe`` on Windows
   or ``.venv/bin/python`` on Linux and macOS.
5. Set ``args`` to ``["-m", "ansys.geometry.mcp"]``. To customize startup,
   append more options to this list, such as ``"--mode", "discovery"``. For all
   available options, see `Startup options`_.

**Example:**

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

Gemini with stdio
~~~~~~~~~~~~~~~~~

1. Open or create ``.gemini/settings.json``.
2. Add an MCP server entry named ``pyansys-geometry-mcp``.
3. Set ``command`` and ``args`` as described for GitHub Copilot.

**Example:**

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

HTTP transport
^^^^^^^^^^^^^^

With the HTTP transport, you start the server yourself and then point your MCP
client at its URL.

Start the server
~~~~~~~~~~~~~~~~

Using the Python interpreter where you installed the package, run this command:

.. code:: bash

    python -m ansys.geometry.mcp --transport http

By default, the server listens on ``http://127.0.0.1:8080/mcp``. You can change
the address with these options:

- ``--http-host``: Host address to bind to. The default is ``127.0.0.1``.
- ``--http-port``: Port number. The default is ``8080``.
- ``--http-path``: URL path. The default is ``/mcp``.
- ``--cors-origins``: Comma-separated list of allowed CORS origins. The default
  is none.

You can combine these with any other startup options. For example:

.. code:: bash

    python -m ansys.geometry.mcp --transport http --http-port 9000 --mode discovery

Keep the terminal open while you use the server. To stop it, press
**Ctrl+C**.

.. warning::

   The HTTP server does not provide authentication. By default, it binds to
   ``127.0.0.1`` so that only your local machine can reach it. If you set
   ``--http-host`` to an address reachable from other machines, anyone who can
   reach that address can call the server's tools, including tools that run
   arbitrary Python code.

GitHub Copilot (Visual Studio Code) with HTTP
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Open or create ``.vscode/mcp.json`` in your workspace. Alternatively, you
   can use a ``.mcp.json`` file at the root of your workspace.
2. Add a server entry for ``pyansys-geometry-mcp``.
3. Set ``type`` to ``"http"``.
4. Set ``url`` to the address the server is listening on. If you changed
   ``--http-host``, ``--http-port``, or ``--http-path``, update the URL to match.

**Example:**

.. code-block:: json

    {
      "servers": {
        "pyansys-geometry-mcp": {
          "type": "http",
          "url": "http://127.0.0.1:8080/mcp"
        }
      },
      "inputs": []
    }

Gemini with HTTP
~~~~~~~~~~~~~~~~

1. Open or create ``.gemini/settings.json``.
2. Add an MCP server entry named ``pyansys-geometry-mcp``.
3. Set ``httpUrl`` to the address the server is listening on.

**Example:**

.. code-block:: json

    {
      "mcpServers": {
        "pyansys-geometry-mcp": {
          "httpUrl": "http://127.0.0.1:8080/mcp",
          "trust": true
        }
      }
    }

Verification
^^^^^^^^^^^^

After configuration, start a chat in your client and ask it to call one of
the available tools. If you use the HTTP transport, make sure the server is
running first. If the product backend is still starting, wait a few seconds
and then ask your client to call the tool again.

