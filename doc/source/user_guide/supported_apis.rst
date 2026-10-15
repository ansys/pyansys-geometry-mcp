Supported APIs
==============

This page lists the MCP tools registered by PyAnsys Geometry-MCP.

Design and session
------------------

.. list-table::
   :header-rows: 1

   * - Tool
     - Description
   * - ``get_product_status``
     - Report whether the Geometry backend is connected.
   * - ``create_design``
     - Create a design with the specified name.
   * - ``get_design_info``
     - Report information about the active design.
   * - ``get_session_script``
     - Return the recorded session commands as a reusable PyAnsys Geometry script.
   * - ``run_python_code``
     - Run PyAnsys Geometry Python code in the persistent session for operations without a dedicated tool.
   * - ``run_script_file``
     - Run an existing Discovery or SpaceClaim scripting API file.
   * - ``file_io``
     - Import a geometry file or export the active design.

Selection and querying
----------------------

.. list-table::
   :header-rows: 1

   * - Tool
     - Description
   * - ``list_entities``
     - List bodies, components, faces, or edges in the active design.
   * - ``create_selection_builder``
     - Create an empty selection builder and return its handle.
   * - ``select_entities``
     - Find entities matching criteria and add them to a selection builder.
   * - ``filter_entities``
     - Narrow the entities already held by a selection builder.
   * - ``order_entities``
     - Order the selected entities by a numeric property.
   * - ``group_entities``
     - Group selected entities by a shared property.
   * - ``extend_selection``
     - Extend the current selection to related entities.
   * - ``create_named_selection``
     - Create a named selection from a selection builder or specified geometry entities.

Modeling and repair
-------------------

.. list-table::
   :header-rows: 1

   * - Tool
     - Description
   * - ``boolean_operation``
     - Subtract, unite, or intersect two bodies. The target body survives and the tool body is consumed.
   * - ``inspect_geometry``
     - Report geometry issues without modifying the design. By default, inspect all bodies.
   * - ``repair_geometry``
     - Repair a selected class of geometry problem.

Visualization
-------------

.. list-table::
   :header-rows: 1

   * - Tool
     - Description
   * - ``get_design_3d_scene``
     - Open a 3D scene window for the active design.
   * - ``get_screenshot``
     - Capture a screenshot of the active design's 3D scene.
   * - ``read_image_in_base64``
     - Read an image file and return its contents as base64-encoded data.

Recommended workflows
---------------------

Diagnosing and repairing geometry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``inspect_geometry`` when the problem is unknown. If you already know the
problem, call ``repair_geometry`` directly. Both tools can be scoped to named
bodies, a named selection, or a selection builder.

Selecting entities
^^^^^^^^^^^^^^^^^^^

Create a selection builder, add entities with ``select_entities``, and refine
the result with ``filter_entities``. Use ``order_entities`` or
``group_entities`` to organize results, and ``create_named_selection`` to save
a reusable selection.

Running other operations
^^^^^^^^^^^^^^^^^^^^^^^^

Use a dedicated MCP tool when one matches the requested operation. Otherwise,
use ``run_python_code`` for PyAnsys Geometry operations or ``run_script_file``
for an existing Discovery or SpaceClaim script.
