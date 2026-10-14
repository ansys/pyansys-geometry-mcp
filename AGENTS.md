# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this project is

`pyansys-geometry-mcp` is a Model Context Protocol server that exposes
`ansys-geometry-core` to AI assistants. Tools are registered with `@app.tool()` and
talk to a running Ansys Geometry/Discovery backend over gRPC.

The server builds on `ansys-common-mcp`, which is a **separate package installed into
`.venv/Lib/site-packages/ansys/common/mcp/`**. It provides `PyAnsysBaseMCP`,
`PersistentPythonSession`, and the shared `execute_python_code` helper. Code there is
not part of this repository — do not edit it. If a defect is in that package, say so
and report it upstream rather than patching `site-packages` or working around it here.

## Environment and commands

Python >= 3.12. The repo venv lives at the root:

```powershell
.\.venv\Scripts\python.exe -m pytest              # run the test suite
.\.venv\Scripts\python.exe -m pytest -k <expr>    # run a subset
.\.venv\Scripts\python.exe -m pre_commit run --files <paths>
```

`pyproject.toml` sets `addopts` (including `--cov=ansys.geometry.mcp`) and
`asyncio_mode = "auto"`, so plain `async def test_*` needs no marker. Do not pass an
extra `--cov=` override on the command line.

## Layout

```
src/ansys/geometry/mcp/
  server.py     PyAnsysGeometryMCP  (startup/cleanup, product instance)
  context.py    PyAnsysGeometryContext dataclass (app state)
  tools/        one module per tool family; __init__.py imports them to register
  misc/         auxiliary/helper functions shared by tools
tests/
  integration/  mirrors the tool modules; needs a live geometry backend
  eval/         opt-in LLM tool-discoverability suite (requires Azure OpenAI)
```

## Which tools exist

**`list_tools()` is the only accepted source of truth for the tool set.** Do not
determine which tools exist by recalling a previous session.

Importing `ansys.geometry.mcp.tools` is what performs registration, so this doubles as
a check that a new tool was wired into `tools/__init__.py`. The app exposes
`list_tools()` (async).

This rule governs *discovery*. Reading a tool's source is still expected once
`list_tools()` has told you the tool exists and you need to change it.

## Conventions

- Ruff, line length 100, double quotes. Lint rules: `D` (pydocstyle, numpy
  convention), `I` (isort), `PTH`, `TD`.
- Every tool's docstring **is** its MCP description, so wording directly affects
  whether a model picks the tool. Treat docstring edits as behavioural changes.
- New tool functions must be imported in `tools/__init__.py` or they are never
  registered.
- `ansys-geometry-core` defaults to SI: a bare number is metres (m², m³ for areas
  and volumes), and angles passed as `Quantity` need an explicit unit. Users
  usually speak in millimetres, so convert at the boundary and state the unit in
  every numeric parameter's docstring.
- Keep the existing MIT license header at the top of source files.
- Do not manually create changelog files. These are automatically created on PRs.

## Testing

Most of `tests/integration/` requires a running geometry backend; without one, the
session-scoped fixtures fail during setup. That is an environment problem, not a code
regression — check whether a backend is running before investigating further. Tests
built on a plain `MagicMock()` context run without a backend.

## Working agreement

**Do not write repository memory.** Do not create files under `/memories/repo/` for
this project. This codebase changes faster than notes about it stay true, and stale
notes have caused real misdiagnoses. Durable facts belong in this file, in
docstrings, or in tests, where they are reviewed and updated alongside the code.

**Stop and ask instead of guessing.** When a tool reports success but returns no
usable result, or a command behaves inexplicably:

1. Form a specific hypothesis and run one test that distinguishes it from the
   alternatives.
2. If that does not resolve it, stop. Report what was observed, what was tried, and
   what is still unknown.

Do not poll a non-responding tool repeatedly, and do not reach for evidence you
cannot interpret (process CPU counters, memory usage, unrelated system state) to
justify continuing. Two failed attempts is the limit before raising the issue.

**Report tool defects as defects.** When a server tool misbehaves, prefer naming the
bug over building a workaround around it. A workaround that hides a silent failure is
worse than a stalled task.

**A geometry operation is not expected to succeed completely.** Partial success is a
normal outcome, not a defect. The modeling kernel legitimately declines work that
would invalidate adjacent topology, so a repair can leave problem areas behind, a
boolean can consume only some of its tools, a fillet can skip edges it cannot resolve,
and an import can drop entities it has no representation for. Counts returned by
`ansys-geometry-core` are generally per-call results, not totals for the design — the
`found`/`repaired` fields on repair tools are batch counts, not problem-area totals.
Do not treat a partial result as a failed operation or as an automatic reason to
repeat the same tool, escalate, or start diagnosing more broadly.

Treat each requested geometry task as one bounded attempt, not necessarily one tool
call. A short sequence of directly related tools is appropriate when needed to carry
out the requested operation or its natural follow-up. Keep the sequence within the
requested scope; do not rerun a step without a concrete reason, broaden the scope, or
keep trying alternate parameters solely because the kernel reports partial success.
Report each operation, its parameters and entities in scope, and the result returned.
Stop after the bounded sequence and let the user decide whether to continue. Go beyond
it only when the user asks or when a self-contradictory result needs clarification —
for example, a re-scan showing *more* problems than before, a body count that moves
the wrong way, or an error raised by the call itself.

**Do not measure the model unless asked.** The call's own report is the default
evidence for what happened; quote it and stop there. Independent before/after metrics
— edge, face, or problem-area counts — are a separate, billable piece of work. Take
them only when the user asks for a comparison, or when the call's report contradicts
itself.

When a measurement *is* warranted, take the cheapest one that answers the question:
scope it to the bodies the operation actually touched, and prefer `inspect_geometry`
over hand-written traversal. Never walk the whole design's topology through
`run_python_code` — iterating `body.edges` or `body.faces` across every body pulls
thousands of entities over gRPC one at a time and is far more expensive than the
repair it is checking. If only an expensive measurement would settle the question, say
so and let the user choose.

**Proceed with requested repairs without approval prompts.** Geometry repair operations
are understood to take time and mutate the active design in place. Do not ask the user
to approve requested repairs or confirm their runtime. Stay within the requested scope,
use specified thresholds or documented defaults, and ask only when a required parameter
or scope is genuinely ambiguous. Prefer the cheapest form of an operation (for example,
avoid `comprehensive_result=True`, which issues one backend round trip per problem area),
and state clearly what has already been applied if a sequence is interrupted.

**Clarify export format; default saves to `.dsco`.** When a user requests "export"
without specifying a format, including at the end of a longer prompt, ask which supported
format they want before exporting. Offer the supported choices: `fmd`, `step`, `iges`,
`scdocx`, `disco` (`.dsco`), `parasolid_text`, and `parasolid_bin`. Do not silently choose
an export format. When a user requests "save" without specifying a format, save as
`.dsco` by default using `file_format="disco"`; no format clarification is needed.
Honor an explicitly requested format for either operation.
For both save and export, check whether the destination file already exists before
writing. Never overwrite an existing file without the user's explicit permission.
If the file exists and overwrite permission has not been given, ask whether to overwrite
it or use a different filename or destination. If the tool chooses the filename, resolve
the actual output path and check it before invoking the operation.
