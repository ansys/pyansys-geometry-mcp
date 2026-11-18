.. _ref_heat_sink:

Create a basic heat sink
========================

This example shows a conversation with a Geometry-MCP assistant: prompt,
tool call with arguments, and result. It creates a rectangular heat sink
and a face named selection for a later thermal simulation.

Prerequisites and conventions
-----------------------------

Connect your MCP client to a Geometry-MCP server with a running Ansys
Geometry backend. Use a fresh session: creating a design changes the active
design. Python variables persist between calls to ``run_python``.

The calls below use server tool names; clients can display a server prefix.
``ctx`` is injected by MCP and is not a client argument. The Python-style
call in step 2 represents a tool invocation, not a local Python client script.

.. note::

   This is an illustrative transcript, not a captured backend run. Results
   describe the expected successful outcome. IDs and selection handles must
   come from your own tool responses. No thermal solution is computed here.

The base is centered on the XY plane and extends from Z = 0 to 5 mm.
Five fins run along Y and extend from Z = 5 to 25 mm.
The entire underside, at Z = 0, receives heat from a component beneath it.
It is a single face in this simple model; named selections can contain
multiple faces in more complex models.

1. Create the design
--------------------

**Prompt**

    Create a new design called BasicHeatSink. Make a 60 by 40 mm base,
    5 mm thick, with five evenly spaced fins. Each fin should be 2 mm
    thick, 40 mm long, and extend 20 mm from the top of the base. Make one solid body.

**Tool:** ``create_design``

**Arguments**

.. code-block:: json

    {"design_name": "BasicHeatSink"}

**Expected response**

.. code-block:: text

    Design 'BasicHeatSink' created successfully.

2. Build the base and fins
--------------------------

The same prompt continues with ``run_python`` because there is no
dedicated primitive-creation tool. All bare lengths below are in metres.
The fins overlap the base by 1 mm to make the union operation unambiguous;
their exposed height remains 20 mm.

**Tool call with arguments**

.. code-block:: python

    run_python(
        code="""
    from ansys.geometry.core.math import Plane, Point2D
    from ansys.geometry.core.sketch import Sketch

    base_sketch = Sketch()
    base_sketch.box(Point2D([0.0, 0.0]), width=0.060, height=0.040)
    heat_sink = design.extrude_sketch("HeatSink", base_sketch, distance=0.005)

    fins = []
    for index, x_position in enumerate([-0.024, -0.012, 0.0, 0.012, 0.024], start=1):
        fin_sketch = Sketch(Plane(origin=[0.0, 0.0, 0.004]))
        fin_sketch.box(Point2D([x_position, 0.0]), width=0.002, height=0.040)
        fin = design.extrude_sketch(f"Fin_{index}", fin_sketch, distance=0.021)
        fins.append(fin)

    heat_sink.unite(fins)
    print("Base and five fins constructed; boolean union call completed.")
    """,
        timeout=300,
        no_output_timeout=300,
    )

**Expected response** (successful execution envelope)

.. code-block:: json

    {
      "success": true,
      "stdout": "Base and five fins constructed; boolean union call completed.\n",
      "stderr": "",
      "error": null
    }

The printed message reports completion of the call, not an independent
check of the resulting topology. If execution fails, read ``error`` and
``stderr`` before continuing. Do not select faces until modeling is finished:
modeling operations can change face IDs.

3. Select the heat-input face
-----------------------------

**Prompt**

    Select only the underside of the base at Z = 0 mm for heat input.
    Exclude the vertical side faces and all fin faces.

**Tool:** ``create_selection_builder``

**Arguments**

.. code-block:: json

    {}

**Expected response:** an opaque selection handle. In subsequent calls,
replace ``<selection_handle>`` with this exact returned string.

**Tool:** ``select_entities``

**Arguments**

.. code-block:: json

    {
      "selection_handle": "<selection_handle>",
      "entity_type": "face",
      "criteria": "z_location",
      "min_value": -0.0000001,
      "max_value": 0.0000001,
      "range_type": "contain"
    }

**Expected result:** a list containing the underside face ID.
Do not continue with an empty list or a string error response.
An unexpected set of faces needs clarification before saving the selection.

The bounds are in metres: a 0.0001 mm tolerance on either side of Z = 0.
``contain`` requires the face's entire Z range to lie within this band.
The default ``intersect`` could also include vertical faces touching Z = 0.
This query is design-wide, which is appropriate for this fresh, single-body
example; an existing assembly would need additional scoping.

4. Create the named selection
-----------------------------

**Prompt**

    Save those selected faces as HeatInput for scoping a thermal load
    in a simulation.

**Tool:** ``create_named_selection``

**Arguments**

.. code-block:: json

    {
      "name": "HeatInput",
      "selection_handle": "<selection_handle>"
    }

**Expected result:** confirmation that the named selection ``HeatInput``
was created. Reusing the same builder saves the faces selected in step 3;
it does not create a new geometric query or rely on a guessed face ID.

This prepares geometry scoping only. In your thermal solver, assign a
material and apply the desired heat flow or heat flux to ``HeatInput``.
Convection, ambient temperature, meshing, and solving are separate steps.

5. Plot the heat sink (optional)
--------------------------------

**Prompt**

    Show a 3D plot of the heat sink.

**Tool:** ``visualize``

**Arguments**

.. code-block:: json

    {"save": false, "use_service_colors": false}

**Expected response**

.. code-block:: text

    3D scene window opened.

The plot should show a rectangular base with five parallel fins.
It does not highlight the named selection or display temperature contours.
Interactive rendering requires a display on the MCP server host.
To request an image instead, use ``{"save": true}``; the tool returns
the generated PNG path. Pass that path as ``image_path`` to
``read_image_in_base64`` if your client needs the image data to display it.