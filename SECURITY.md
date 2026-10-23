# Security Policy

## Reporting a vulnerability

> [!CAUTION]
> Do not use GitHub issues to report any security vulnerabilities.

If you detect a vulnerability, contact the [PyAnsys Core team](mailto:pyansys-core@synopsys.com),
mentioning the repository and the details of your finding. The team will address it as soon as possible.

Provide the PyAnsys Core team with this information:

- Any specific configuration settings needed to reproduce the problem
- Step-by-step guidance to reproduce the problem
- The exact location of the problematic source code, including tag, branch, commit, or a direct URL
- The potential consequences of the vulnerability, along with a description of how an attacker could take advantage of the issue

<!-- Begin content specific to your library here. -->

## Trust model

PyAnsys Geometry-MCP exposes tools that run arbitrary Python code and script files on the
machine hosting the server:

- `run_python_code` executes any Python code it is given in a persistent session with full
  access to the process's privileges (filesystem, network, subprocesses, and so on).
- `run_script_file` executes an existing Discovery/SpaceClaim script file from disk on the
  geometry backend.

These tools give the connected AI client **full code execution as the host user running the
MCP server**. This is intentional: it is what lets the assistant perform geometry operations
that have no dedicated tool. It also means the server does not, and cannot, sandbox or
restrict what that code can do.

As a result:

- Only connect this server to AI clients you trust, and only in sessions where you trust the
  content the assistant is exposed to (files, scripts, web pages, and so on). A prompt
  injection in untrusted content could induce the assistant to run malicious code through
  `run_python_code` or point `run_script_file` at a malicious script.
- Do not expose the server's HTTP/SSE transport to untrusted networks. Prefer the default
  `stdio` transport, and if you must use `--transport http`, bind to `127.0.0.1` (the
  default) and add your own network-level access control, since the server does not include
  built-in authentication.
- Treat the machine running the server as being within the same trust boundary as the AI
  client: anything the assistant can be led to run, the server will run.