.. _ref_implementing_custom_tools:

Implement a custom tool
=======================

Learn how to implement a custom tool for PyAnsys Geometry-MCP.

Tool overview
-------------

A tool is a function that performs a specific task using PyAnsys Geometry.
When you start the MCP server, MCP clients discover your tools and
can invoke them to perform tasks.

Your tools should:

- Accept structured input parameters.
- Perform operations.
- Return structured output.

Tool anatomy
------------

Use this structure to implement your tool:

.. code-block:: python

    @app.tool()
    def my_custom_tool(ctx: Context, param_1: str, param_2: int) -> str:
        """Perform a custom action on the design to learn how to implement a custom tool.

        Use this tool when asked to create a custom tool.

        Parameters
        ----------
        ctx : Context
            MCP request context (injected automatically).
        param_1 : str
            The first input parameter.
        param_2 : int
            The second input parameter.

        Returns
        -------
        str
            Result message indicating success or failure.
        """
        # Use the context to get the modeler instance
        app_context = get_geometry_ctx(ctx)

        try:
            # Access the live modeler instance through app_context.product_instance
            design = app_context.product_instance.create_design("TestDesignName")

            # Record the command in the history
            app_context.command_history.append(
                f'design=instance.create_design("TestDesignName")'
            )

            # Use the input parameters to perform an operation
            result = f"Received {param_1} and {param_2}"

            # Return the result or an error message
            return result
        except Exception as e:
            logger.error(f"my_custom_tool failed: {e}")
            return f"Error using my_custom_tool: {str(e)}"

Key components
~~~~~~~~~~~~~~

- Document what your tool does, when to use it, and its input and output parameters.
- Use the context object to access the MCP request context and modeler instance.
- Define the input parameters your tool needs.
- Handle errors gracefully and log useful details.
- Add commands to the command history.
- Return the result or an error message after your tool runs.
