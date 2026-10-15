PyAnsys Geometry-MCP
====================
|pyansys| |python| |pypi| |Apache| |GH-CI| |pre-commit|

.. |pyansys| image:: https://img.shields.io/badge/Py-Ansys-ffc107.svg?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAABDklEQVQ4jWNgoDfg5mD8vE7q/3bpVyskbW0sMRUwofHD7Dh5OBkZGBgW7/3W2tZpa2tLQEOyOzeEsfumlK2tbVpaGj4N6jIs1lpsDAwMJ278sveMY2BgCA0NFRISwqkhyQ1q/Nyd3zg4OBgYGNjZ2ePi4rB5loGBhZnhxTLJ/9ulv26Q4uVk1NXV/f///////69du4Zdg78lx//t0v+3S88rFISInD59GqIH2esIJ8G9O2/XVwhjzpw5EAam1xkkBJn/bJX+v1365hxxuCAfH9+3b9/+////48cPuNehNsS7cDEzMTAwMMzb+Q2u4dOnT2vWrMHu9ZtzxP9vl/69RVpCkBlZ3N7enoDXBwEAAA+YYitOilMVAAAAAElFTkSuQmCC
   :target: https://docs.pyansys.com/
   :alt: PyAnsys

.. |python| image:: https://img.shields.io/pypi/pyversions/ansys-geometry-mcp?logo=pypi
   :target: https://pypi.org/project/ansys-geometry-mcp/
   :alt: Python

.. |pypi| image:: https://img.shields.io/pypi/v/ansys-geometry-mcp.svg?logo=python&logoColor=white
   :target: https://pypi.org/project/ansys-geometry-mcp
   :alt: PyPI

.. |Apache| image:: https://img.shields.io/badge/License-Apache%202.0-blue.svg
   :target: https://opensource.org/licenses/Apache-2.0
   :alt: Apache

.. |GH-CI| image:: https://github.com/ansys/pyansys-geometry-mcp/actions/workflows/cicd.yml/badge.svg
   :target: https://github.com/ansys/pyansys-geometry-mcp/actions/workflows/cicd.yml
   :alt: GH-CI

.. |pre-commit| image:: https://results.pre-commit.ci/badge/github/ansys/pyansys-geometry-mcp/main.svg
   :target: https://results.pre-commit.ci/latest/github/ansys/pyansys-geometry-mcp/main
   :alt: pre-commit.ci status

Overview
--------

Use this Python package to make PyAnsys Geometry-MCP tools available to AI
clients through the Model Context Protocol (MCP).

**Warning: arbitrary code execution**

The ``run_python_code`` and ``run_script_file`` tools execute arbitrary code with
the permissions of the account running the server. Connect the server only to AI
clients and content sources you trust. For details, see the `SECURITY.md
<https://github.com/ansys/pyansys-geometry-mcp/blob/main/SECURITY.md>`_ file.


Documentation and support
-------------------------

See the latest stable release documentation in the
`PyAnsys Geometry-MCP documentation <https://geometry-mcp.docs.pyansys.com/version/stable/index.html>`_.

Browse these sections:

- `Getting started <https://geometry-mcp.docs.pyansys.com/version/stable/getting_started/index.html>`_: Install the
  package in user mode.
- `User guide <https://geometry-mcp.docs.pyansys.com/version/stable/user_guide/index.html>`_: Learn key concepts for
  using the tools in your workflows.
- `API reference <https://geometry-mcp.docs.pyansys.com/version/stable/api/index.html>`_: Explore the Python API.
- `Examples <https://geometry-mcp.docs.pyansys.com/version/stable/examples.html>`_: See example workflows.
- `Contribute <https://geometry-mcp.docs.pyansys.com/version/stable/contributing.html>`_: Learn how to contribute to
  the codebase or documentation.

Use the version selector in the upper-right corner of the documentation page
to switch from viewing the documentation for the latest stable release to viewing
the documentation for the development version or previously released versions.

Report bugs or request features on the project's GitHub `Issues
<https://github.com/ansys/pyansys-geometry-mcp/issues>`_ page. For questions,
ideas, or community feedback, use GitHub `Discussions
<https://github.com/ansys/pyansys-geometry-mcp/discussions>`_ or the Ansys
Developer portal's `Discussions <https://discuss.ansys.com/>`_ page.

For general questions about the PyAnsys ecosystem, email
`pyansys.core@ansys.com <pyansys.core@ansys.com>`_. For questions about
PyAnsys Geometry-MCP, use one of the discussion pages above.

License
-------

The project uses the
`Apache License 2.0 <https://github.com/ansys/pyansys-geometry-mcp/blob/main/LICENSE>`_.

PyAnsys Geometry-MCP makes no commercial claims about Ansys.
