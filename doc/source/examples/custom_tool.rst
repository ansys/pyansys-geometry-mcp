.. _ref_implementing_custom_tools:

Implementing Custom Tools
==============================

Learn how to implement a custom MCP tool for PyAnsys Geometry MCP.

Tool Overview
-------------

A tool is a function that performs a specific task using the PyAnsys Geometry library.
They are discovered by MCP clients when the MCP server is started, and can be invoked by the clients to perform their specific tasks.
Tools do the following:

- Take structured input parameters
- Perform some operations
- Return structured output results

Tool Anatomy
------------

Here is an example tool structure:

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
            # The app_context.product_instance holds the live modeler instance for the session
            design = app_context.product_instance.create_design("TestDesignName")

            # Perform transcript
            app_context.command_history.append(
                f'design=instance.create_design("TestDesignName")'
            )

            # Perform some operation(s) using the input parameters
            result = f"Received {param_1} and {param_2}"

            # Return a str containing the result or error message
            return result
        except Exception as e:
            logger.error(f"my_custom_tool failed: {e}")
            return f"Error using my_custom_tool: {str(e)}"

Key Components
~~~~~~~~~~~~~~

- Detailed documentation string describing what the tool does, when to use it, and the input/output parameters.
- Context object providing the MCP request context and access to the modeler instance.
- Input parameters defining the data required for the tool to perform its operation.
- Graceful handling of errors and useful logging.
- Addition of commands called to the command history.
- Return value containing the result or error message after the tool execution.