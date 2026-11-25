.. _ref_release_notes:

Release notes
#############

This document contains the release notes for the PyAnsys Geometry MCP project.

.. vale off

.. towncrier release notes start

`0.1.0 <https://github.com/ansys/pyansys-geometry-mcp/releases/tag/v0.1.0>`_ - November 24, 2026
================================================================================================

.. tab-set::


  .. tab-item:: Added

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Add tools for creating named selections
          - `#29 <https://github.com/ansys/pyansys-geometry-mcp/pull/29>`_

        * - Support linux
          - `#43 <https://github.com/ansys/pyansys-geometry-mcp/pull/43>`_

        * - Tech_review
          - `#52 <https://github.com/ansys/pyansys-geometry-mcp/pull/52>`_

        * - Add repair tools
          - `#75 <https://github.com/ansys/pyansys-geometry-mcp/pull/75>`_

        * - Enhance repair tools + docstrings
          - `#103 <https://github.com/ansys/pyansys-geometry-mcp/pull/103>`_

        * - Add log options
          - `#105 <https://github.com/ansys/pyansys-geometry-mcp/pull/105>`_

        * - Add logo removal functionality to repair tools
          - `#128 <https://github.com/ansys/pyansys-geometry-mcp/pull/128>`_

        * - Use body ids in tool calls
          - `#129 <https://github.com/ansys/pyansys-geometry-mcp/pull/129>`_

        * - Support range types for location selection
          - `#140 <https://github.com/ansys/pyansys-geometry-mcp/pull/140>`_

        * - Added support to filter / select by body id on selection_tools
          - `#158 <https://github.com/ansys/pyansys-geometry-mcp/pull/158>`_

        * - Improve design info and refresh run_python_code
          - `#168 <https://github.com/ansys/pyansys-geometry-mcp/pull/168>`_

        * - Run script string
          - `#184 <https://github.com/ansys/pyansys-geometry-mcp/pull/184>`_


  .. tab-item:: Fixed

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Run_python_code in same session
          - `#54 <https://github.com/ansys/pyansys-geometry-mcp/pull/54>`_

        * - Improve run_python_code timeout
          - `#72 <https://github.com/ansys/pyansys-geometry-mcp/pull/72>`_

        * - \`\`pyansys-common-mcp\`\` version
          - `#87 <https://github.com/ansys/pyansys-geometry-mcp/pull/87>`_

        * - Use items property on selection builder entity types
          - `#93 <https://github.com/ansys/pyansys-geometry-mcp/pull/93>`_

        * - Question and default save export
          - `#95 <https://github.com/ansys/pyansys-geometry-mcp/pull/95>`_

        * - Selection max only range
          - `#138 <https://github.com/ansys/pyansys-geometry-mcp/pull/138>`_

        * - Improve docstrings to avoid unsupported arguments
          - `#142 <https://github.com/ansys/pyansys-geometry-mcp/pull/142>`_

        * - Require explicit types when saving mixed selections
          - `#143 <https://github.com/ansys/pyansys-geometry-mcp/pull/143>`_

        * - Filtering by name and matching criteria case insensitive
          - `#157 <https://github.com/ansys/pyansys-geometry-mcp/pull/157>`_

        * - Change file format from disco to dsco
          - `#166 <https://github.com/ansys/pyansys-geometry-mcp/pull/166>`_

        * - Final changes
          - `#191 <https://github.com/ansys/pyansys-geometry-mcp/pull/191>`_


  .. tab-item:: Documentation

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Overall review for public release
          - `#112 <https://github.com/ansys/pyansys-geometry-mcp/pull/112>`_

        * - Improve getting started doc
          - `#147 <https://github.com/ansys/pyansys-geometry-mcp/pull/147>`_


  .. tab-item:: Dependencies

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Bump pypdf from 6.16.1 to 6.16.2
          - `#27 <https://github.com/ansys/pyansys-geometry-mcp/pull/27>`_

        * - Bump ansys-sphinx-theme from 1.10.0 to 1.11.0 in the docs-deps group
          - `#40 <https://github.com/ansys/pyansys-geometry-mcp/pull/40>`_

        * - Bump ansys-common-mcp from 0.3.3 to 0.3.4
          - `#47 <https://github.com/ansys/pyansys-geometry-mcp/pull/47>`_

        * - Bump pypdf from 6.16.2 to 6.17.0
          - `#56 <https://github.com/ansys/pyansys-geometry-mcp/pull/56>`_

        * - Bump openai from 3.6.0 to 3.8.0
          - `#57 <https://github.com/ansys/pyansys-geometry-mcp/pull/57>`_

        * - Bump pypdf from 6.17.0 to 6.18.0
          - `#58 <https://github.com/ansys/pyansys-geometry-mcp/pull/58>`_

        * - Bump pypdf from 6.18.0 to 6.18.1
          - `#62 <https://github.com/ansys/pyansys-geometry-mcp/pull/62>`_

        * - Bump openai from 3.8.0 to 3.14.0
          - `#68 <https://github.com/ansys/pyansys-geometry-mcp/pull/68>`_

        * - Bump pypdf from 6.18.1 to 6.19.0
          - `#71 <https://github.com/ansys/pyansys-geometry-mcp/pull/71>`_

        * - Bump notebook from 7.6.2 to 7.6.3 in the docs-deps group
          - `#73 <https://github.com/ansys/pyansys-geometry-mcp/pull/73>`_

        * - Bump openai from 3.14.0 to 3.15.0
          - `#74 <https://github.com/ansys/pyansys-geometry-mcp/pull/74>`_

        * - Bump openai from 3.15.0 to 3.17.0
          - `#78 <https://github.com/ansys/pyansys-geometry-mcp/pull/78>`_

        * - Bump openai from 3.17.0 to 3.19.0
          - `#80 <https://github.com/ansys/pyansys-geometry-mcp/pull/80>`_

        * - Bump pytest-mock from 3.15.1 to 3.16.0
          - `#86 <https://github.com/ansys/pyansys-geometry-mcp/pull/86>`_

        * - Bump openai from 3.17.0 to 3.20.0
          - `#88 <https://github.com/ansys/pyansys-geometry-mcp/pull/88>`_

        * - Bump openai from 3.20.0 to 3.22.1
          - `#91 <https://github.com/ansys/pyansys-geometry-mcp/pull/91>`_

        * - Bump jupytext from 1.19.5 to 1.19.6 in the docs-deps group
          - `#94 <https://github.com/ansys/pyansys-geometry-mcp/pull/94>`_

        * - Bump quarto-cli from 1.10.18 to 1.10.19
          - `#97 <https://github.com/ansys/pyansys-geometry-mcp/pull/97>`_

        * - Bump openai from 3.22.1 to 3.23.0
          - `#98 <https://github.com/ansys/pyansys-geometry-mcp/pull/98>`_

        * - Bump openai from 3.23.0 to 3.24.0
          - `#101 <https://github.com/ansys/pyansys-geometry-mcp/pull/101>`_

        * - Bump black from 26.5.1 to 26.10.0
          - `#102 <https://github.com/ansys/pyansys-geometry-mcp/pull/102>`_

        * - Bump black from 26.10.0 to 26.10.1
          - `#106 <https://github.com/ansys/pyansys-geometry-mcp/pull/106>`_

        * - Bump nbconvert from 7.17.1 to 7.17.2 in the docs-deps group across 1 directory
          - `#110 <https://github.com/ansys/pyansys-geometry-mcp/pull/110>`_

        * - Bump openai from 3.24.0 to 3.26.1
          - `#111 <https://github.com/ansys/pyansys-geometry-mcp/pull/111>`_

        * - Bump ansys-geometry-core from 0.18.1 to 0.18.2
          - `#114 <https://github.com/ansys/pyansys-geometry-mcp/pull/114>`_

        * - Bump pypdf from 6.19.0 to 6.20.0
          - `#115 <https://github.com/ansys/pyansys-geometry-mcp/pull/115>`_

        * - Bump pypdf from 6.20.0 to 6.20.1
          - `#118 <https://github.com/ansys/pyansys-geometry-mcp/pull/118>`_

        * - Bump openai from 3.26.1 to 3.29.0
          - `#119 <https://github.com/ansys/pyansys-geometry-mcp/pull/119>`_

        * - Bump pre-commit from 4.6.2 to 4.7.0
          - `#121 <https://github.com/ansys/pyansys-geometry-mcp/pull/121>`_

        * - Bump pytest-mock from 3.16.0 to 3.16.1
          - `#122 <https://github.com/ansys/pyansys-geometry-mcp/pull/122>`_

        * - Bump openai from 3.29.0 to 3.31.0
          - `#123 <https://github.com/ansys/pyansys-geometry-mcp/pull/123>`_

        * - Bump sphinx from 9.1.0 to 9.1.1 in the docs-deps group
          - `#125 <https://github.com/ansys/pyansys-geometry-mcp/pull/125>`_

        * - Bump pypdf from 6.20.1 to 6.21.0
          - `#126 <https://github.com/ansys/pyansys-geometry-mcp/pull/126>`_

        * - Bump pypdf from 6.21.0 to 6.21.2
          - `#130 <https://github.com/ansys/pyansys-geometry-mcp/pull/130>`_

        * - Bump pytest-mock from 3.16.1 to 3.17.0
          - `#131 <https://github.com/ansys/pyansys-geometry-mcp/pull/131>`_

        * - Bump openai from 3.31.0 to 3.35.1
          - `#132 <https://github.com/ansys/pyansys-geometry-mcp/pull/132>`_

        * - Bump openai from 3.35.1 to 3.36.1
          - `#144 <https://github.com/ansys/pyansys-geometry-mcp/pull/144>`_

        * - Bump pytest-asyncio from 1.4.0 to 1.4.1
          - `#145 <https://github.com/ansys/pyansys-geometry-mcp/pull/145>`_

        * - Bump pypdf from 6.21.2 to 6.21.3
          - `#150 <https://github.com/ansys/pyansys-geometry-mcp/pull/150>`_

        * - Bump openai from 3.36.1 to 3.37.0
          - `#151 <https://github.com/ansys/pyansys-geometry-mcp/pull/151>`_

        * - Bump the docs-deps group across 1 directory with 2 updates
          - `#154 <https://github.com/ansys/pyansys-geometry-mcp/pull/154>`_

        * - Bump quarto-cli from 1.10.19 to 1.10.20
          - `#155 <https://github.com/ansys/pyansys-geometry-mcp/pull/155>`_

        * - Bump pypdf from 6.21.3 to 6.21.4
          - `#156 <https://github.com/ansys/pyansys-geometry-mcp/pull/156>`_

        * - Bump openai from 3.37.0 to 3.39.0
          - `#159 <https://github.com/ansys/pyansys-geometry-mcp/pull/159>`_

        * - Bump pytest from 9.1.1 to 9.2.0
          - `#162 <https://github.com/ansys/pyansys-geometry-mcp/pull/162>`_

        * - Bump openai from 3.39.0 to 3.41.0
          - `#167 <https://github.com/ansys/pyansys-geometry-mcp/pull/167>`_

        * - Bump ansys-geometry-core from 0.18.2 to 0.18.4
          - `#170 <https://github.com/ansys/pyansys-geometry-mcp/pull/170>`_, `#172 <https://github.com/ansys/pyansys-geometry-mcp/pull/172>`_

        * - Bump openai from 3.41.0 to 3.42.1
          - `#171 <https://github.com/ansys/pyansys-geometry-mcp/pull/171>`_

        * - Bump pytest-asyncio from 1.4.1 to 1.4.1.post1
          - `#173 <https://github.com/ansys/pyansys-geometry-mcp/pull/173>`_

        * - Bump quarto-cli from 1.10.20 to 1.11.9
          - `#174 <https://github.com/ansys/pyansys-geometry-mcp/pull/174>`_

        * - Bump notebook from 7.6.4 to 7.6.5 in the docs-deps group
          - `#175 <https://github.com/ansys/pyansys-geometry-mcp/pull/175>`_

        * - Bump openai from 3.42.1 to 3.46.0
          - `#178 <https://github.com/ansys/pyansys-geometry-mcp/pull/178>`_

        * - Bump openai from 3.46.0 to 3.49.0 in the python-deps group
          - `#183 <https://github.com/ansys/pyansys-geometry-mcp/pull/183>`_

        * - Bump the python-deps group with 2 updates
          - `#186 <https://github.com/ansys/pyansys-geometry-mcp/pull/186>`_

        * - Bump the python-deps group across 1 directory with 2 updates
          - `#189 <https://github.com/ansys/pyansys-geometry-mcp/pull/189>`_

        * - Bump openai from 3.51.0 to 3.52.0 in the python-deps group
          - `#190 <https://github.com/ansys/pyansys-geometry-mcp/pull/190>`_


  .. tab-item:: Maintenance

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Add doc build jobs
          - `#20 <https://github.com/ansys/pyansys-geometry-mcp/pull/20>`_

        * - Bump the pre-commit-hooks group with 5 updates
          - `#21 <https://github.com/ansys/pyansys-geometry-mcp/pull/21>`_

        * - Bump the actions group with 5 updates
          - `#22 <https://github.com/ansys/pyansys-geometry-mcp/pull/22>`_

        * - Add required files
          - `#24 <https://github.com/ansys/pyansys-geometry-mcp/pull/24>`_, `#26 <https://github.com/ansys/pyansys-geometry-mcp/pull/26>`_

        * - Ci/cd reliability and doc fixes
          - `#25 <https://github.com/ansys/pyansys-geometry-mcp/pull/25>`_

        * - Bump https://github.com/astral-sh/ruff-pre-commit from v0.16.3 to 0.16.4 in the pre-commit-hooks group
          - `#30 <https://github.com/ansys/pyansys-geometry-mcp/pull/30>`_

        * - Bump the actions group across 1 directory with 12 updates
          - `#31 <https://github.com/ansys/pyansys-geometry-mcp/pull/31>`_

        * - Reorganize tools
          - `#36 <https://github.com/ansys/pyansys-geometry-mcp/pull/36>`_

        * - Bump https://github.com/tox-dev/pyproject-fmt from v2.28.0 to 2.28.1 in the pre-commit-hooks group
          - `#37 <https://github.com/ansys/pyansys-geometry-mcp/pull/37>`_

        * - Bump the actions group with 12 updates
          - `#38 <https://github.com/ansys/pyansys-geometry-mcp/pull/38>`_, `#42 <https://github.com/ansys/pyansys-geometry-mcp/pull/42>`_, `#49 <https://github.com/ansys/pyansys-geometry-mcp/pull/49>`_

        * - Refactor and test selection tools
          - `#39 <https://github.com/ansys/pyansys-geometry-mcp/pull/39>`_

        * - Bump https://github.com/astral-sh/ruff-pre-commit from v0.16.4 to 0.16.5 in the pre-commit-hooks group
          - `#44 <https://github.com/ansys/pyansys-geometry-mcp/pull/44>`_

        * - Bump https://github.com/tox-dev/pyproject-fmt from v2.28.1 to 2.29.0 in the pre-commit-hooks group
          - `#46 <https://github.com/ansys/pyansys-geometry-mcp/pull/46>`_

        * - Bump https://github.com/tox-dev/pyproject-fmt from v2.29.0 to 2.29.2 in the pre-commit-hooks group
          - `#48 <https://github.com/ansys/pyansys-geometry-mcp/pull/48>`_

        * - Bump https://github.com/tox-dev/pyproject-fmt from v2.29.2 to 2.29.3 in the pre-commit-hooks group
          - `#50 <https://github.com/ansys/pyansys-geometry-mcp/pull/50>`_

        * - Bump https://github.com/astral-sh/ruff-pre-commit from v0.16.5 to 0.16.6 in the pre-commit-hooks group
          - `#55 <https://github.com/ansys/pyansys-geometry-mcp/pull/55>`_

        * - Bump pyvista/setup-headless-display-action from 5.0.0 to 5.1.0 in the actions group
          - `#61 <https://github.com/ansys/pyansys-geometry-mcp/pull/61>`_

        * - Bump astral-sh/setup-uv from 10.0.1 to 10.1.0 in the actions group
          - `#63 <https://github.com/ansys/pyansys-geometry-mcp/pull/63>`_

        * - Bump codecov/codecov-action from 7.0.0 to 7.1.0 in the actions group
          - `#67 <https://github.com/ansys/pyansys-geometry-mcp/pull/67>`_

        * - Bump codecov/codecov-action from 7.1.0 to 7.1.1 in the actions group
          - `#70 <https://github.com/ansys/pyansys-geometry-mcp/pull/70>`_

        * - Bump astral-sh/setup-uv from 10.1.0 to 10.2.0 in the actions group
          - `#76 <https://github.com/ansys/pyansys-geometry-mcp/pull/76>`_

        * - Bump the pre-commit-hooks group across 1 directory with 3 updates
          - `#79 <https://github.com/ansys/pyansys-geometry-mcp/pull/79>`_

        * - Bump https://github.com/python-jsonschema/check-jsonschema from 0.38.1 to 0.38.2 in the pre-commit-hooks group
          - `#82 <https://github.com/ansys/pyansys-geometry-mcp/pull/82>`_

        * - Bump https://github.com/astral-sh/ruff-pre-commit from v0.16.8 to 0.16.9 in the pre-commit-hooks group
          - `#84 <https://github.com/ansys/pyansys-geometry-mcp/pull/84>`_

        * - Tool reorganization
          - `#90 <https://github.com/ansys/pyansys-geometry-mcp/pull/90>`_

        * - Bump https://github.com/astral-sh/ruff-pre-commit from v0.16.9 to 0.16.10 in the pre-commit-hooks group
          - `#96 <https://github.com/ansys/pyansys-geometry-mcp/pull/96>`_

        * - Bump the pre-commit-hooks group with 2 updates
          - `#100 <https://github.com/ansys/pyansys-geometry-mcp/pull/100>`_

        * - Add teams notification for LLM eval action
          - `#104 <https://github.com/ansys/pyansys-geometry-mcp/pull/104>`_

        * - Bump actions/upload-artifact from 7.0.1 to 7.0.2 in the actions group
          - `#108 <https://github.com/ansys/pyansys-geometry-mcp/pull/108>`_

        * - Combine screenshot and 3d scene plot tools
          - `#109 <https://github.com/ansys/pyansys-geometry-mcp/pull/109>`_

        * - Bump astral-sh/setup-uv from 10.2.0 to 10.3.0 in the actions group
          - `#116 <https://github.com/ansys/pyansys-geometry-mcp/pull/116>`_

        * - Bump the pre-commit-hooks group with 3 updates
          - `#117 <https://github.com/ansys/pyansys-geometry-mcp/pull/117>`_

        * - Bump https://github.com/astral-sh/ruff-pre-commit from v0.17.0 to 0.17.1 in the pre-commit-hooks group
          - `#124 <https://github.com/ansys/pyansys-geometry-mcp/pull/124>`_

        * - Bump the actions group across 1 directory with 15 updates
          - `#127 <https://github.com/ansys/pyansys-geometry-mcp/pull/127>`_, `#185 <https://github.com/ansys/pyansys-geometry-mcp/pull/185>`_

        * - Bump pypa/gh-action-pypi-publish from 1.14.2 to 1.14.3 in the actions group
          - `#139 <https://github.com/ansys/pyansys-geometry-mcp/pull/139>`_

        * - Bump the actions group with 16 updates
          - `#141 <https://github.com/ansys/pyansys-geometry-mcp/pull/141>`_

        * - Bump the actions group with 2 updates
          - `#146 <https://github.com/ansys/pyansys-geometry-mcp/pull/146>`_

        * - Bump the actions group across 1 directory with 2 updates
          - `#153 <https://github.com/ansys/pyansys-geometry-mcp/pull/153>`_

        * - Bump the pre-commit-hooks group across 1 directory with 2 updates
          - `#160 <https://github.com/ansys/pyansys-geometry-mcp/pull/160>`_, `#179 <https://github.com/ansys/pyansys-geometry-mcp/pull/179>`_

        * - Bump the actions group across 1 directory with 17 updates
          - `#164 <https://github.com/ansys/pyansys-geometry-mcp/pull/164>`_

        * - Bump skitionek/notify-microsoft-teams from 1.3.5 to 1.3.6 in the actions group
          - `#177 <https://github.com/ansys/pyansys-geometry-mcp/pull/177>`_

        * - Bump docker/login-action from 4.7.0 to 4.8.0 in the actions group across 1 directory
          - `#180 <https://github.com/ansys/pyansys-geometry-mcp/pull/180>`_

        * - Bump https://github.com/astral-sh/ruff-pre-commit from v0.17.3 to 0.17.4 in the pre-commit-hooks group
          - `#182 <https://github.com/ansys/pyansys-geometry-mcp/pull/182>`_

        * - Rename tools for consistency
          - `#187 <https://github.com/ansys/pyansys-geometry-mcp/pull/187>`_

        * - Bump https://github.com/astral-sh/ruff-pre-commit from v0.17.4 to 0.17.5 in the pre-commit-hooks group
          - `#188 <https://github.com/ansys/pyansys-geometry-mcp/pull/188>`_

        * - Add smoke tests
          - `#194 <https://github.com/ansys/pyansys-geometry-mcp/pull/194>`_


  .. tab-item:: Test

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Improve tool coverage
          - `#23 <https://github.com/ansys/pyansys-geometry-mcp/pull/23>`_

        * - Tool discoverability test harness
          - `#45 <https://github.com/ansys/pyansys-geometry-mcp/pull/45>`_

        * - Add integration testing
          - `#53 <https://github.com/ansys/pyansys-geometry-mcp/pull/53>`_


.. vale on
