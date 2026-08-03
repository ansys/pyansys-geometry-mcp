# Copyright (C) 2026 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Base infrastructure for the MCP selection pipeline.

Defines the registry-based dispatch mechanism used by ``build_selection``:
each entity-type handler (body, face, edge) declares an ``ACTIONS`` table
mapping a public action name to the underlying ``*Selection`` method to call,
plus any enum parameters that need string resolution. This avoids a giant
if/elif dispatch chain in the MCP tool layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ansys.geometry.core.connection.client import GrpcClient
    from ansys.geometry.core.designer.design import Design


@dataclass(frozen=True)
class ActionSpec:
    """Maps a public selection-pipeline action name to a concrete method call.

    Attributes
    ----------
    method : str
        Name of the method to call on the current ``*Selection`` object.
    enums : dict[str, Callable]
        Maps parameter names to resolver functions that convert a caller-supplied
        string into the enum value expected by ``method``. Parameters not listed
        here are passed through unchanged.

    """

    method: str
    enums: dict[str, Callable[[Any], Any]] = field(default_factory=dict)


class BaseSelectionHandler(ABC):
    """Base class for entity-type-specific selection handlers.

    Subclasses declare:

    - ``ENTITY_TYPE`` — the entity type name (``"body"``, ``"face"``, ``"edge"``).
    - ``ACTIONS`` — a registry of action name -> :class:`ActionSpec`.
    - ``CHILD_TYPES`` — entity types this handler can transition its selection into.

    and implement the abstract methods below to build/serialize selections of
    their entity type.
    """

    ENTITY_TYPE: str
    ACTIONS: dict[str, ActionSpec] = {}
    CHILD_TYPES: tuple[str, ...] = ()

    @classmethod
    def apply_step(cls, selection: Any, step: dict) -> Any:
        """Apply a single pipeline step to a selection, returning a new selection.

        Parameters
        ----------
        selection : Any
            Current typed selection (for example a ``BodySelection``).
        step : dict
            Step dict of the form ``{"action": <name>, **params}``.

        Returns
        -------
        Any
            The new selection returned by the resolved action method.

        Raises
        ------
        ValueError
            If ``step["action"]`` is not a registered action for this handler.

        """
        action = step.get("action")
        spec = cls.ACTIONS.get(action)
        if spec is None:
            valid = ", ".join(sorted(cls.ACTIONS))
            raise ValueError(
                f"Unknown action '{action}' for entity type '{cls.ENTITY_TYPE}'. "
                f"Valid actions: {valid}"
            )

        kwargs = {}
        for key, value in step.items():
            if key == "action":
                continue
            resolver = spec.enums.get(key)
            kwargs[key] = resolver(value) if resolver else value

        method = getattr(selection, spec.method)
        return method(**kwargs)

    @classmethod
    @abstractmethod
    def build_initial(cls, design: "Design", grpc_client: "GrpcClient") -> Any:
        """Create an empty typed selection of this handler's entity type."""

    @classmethod
    @abstractmethod
    def build_from_ids(cls, design: "Design", grpc_client: "GrpcClient", ids: list[str]) -> Any:
        """Reconstruct a typed selection from a list of entity IDs."""

    @classmethod
    @abstractmethod
    def build_from_items(cls, design: "Design", grpc_client: "GrpcClient", items: list) -> Any:
        """Build a typed selection directly from domain objects (used for transitions)."""

    @classmethod
    @abstractmethod
    def serialize(cls, selection: Any) -> list[dict]:
        """Convert selection items into JSON-serializable summaries."""

    @classmethod
    def get_child_entities(cls, selection: Any, target_type: str) -> list:
        """Extract child entities of ``target_type`` from a selection (for transitions).

        Overridden by handlers that support downward transitions (body -> face,
        body -> edge, face -> edge). The default raises, since not every entity
        type has child entities to transition into (for example, edge is a leaf).
        """
        raise NotImplementedError(
            f"Entity type '{cls.ENTITY_TYPE}' does not support transitioning to '{target_type}'."
        )


#: Registry of entity type name -> handler class, populated via ``register_handler``
#: as a side effect of importing ``selection/__init__.py``.
HANDLER_REGISTRY: dict[str, type[BaseSelectionHandler]] = {}


def register_handler(handler_cls: type[BaseSelectionHandler]) -> type[BaseSelectionHandler]:
    """Class decorator that registers a handler under its ``ENTITY_TYPE``."""
    HANDLER_REGISTRY[handler_cls.ENTITY_TYPE] = handler_cls
    return handler_cls


def transition(
    design: "Design",
    grpc_client: "GrpcClient",
    from_type: str,
    selection: Any,
    to_type: str,
) -> Any:
    """Transition a selection of one entity type into a selection of a child entity type.

    Only downward transitions are supported: body -> face, body -> edge, and
    face -> edge. There is no way back up (edge -> face, face -> body).

    Parameters
    ----------
    design : Design
        Active design (used to construct the new typed selection).
    grpc_client : GrpcClient
        gRPC client (used to construct the new typed selection).
    from_type : str
        Entity type of ``selection``.
    selection : Any
        Current typed selection to transition from.
    to_type : str
        Entity type to transition into.

    Returns
    -------
    Any
        A new typed selection of ``to_type``, built from the child entities of
        ``selection``'s items.

    """
    from_handler = HANDLER_REGISTRY.get(from_type)
    if from_handler is None:
        raise ValueError(f"Unknown source entity type '{from_type}'.")
    to_handler = HANDLER_REGISTRY.get(to_type)
    if to_handler is None:
        raise ValueError(f"Unknown target entity type '{to_type}'.")
    if to_type not in from_handler.CHILD_TYPES:
        raise ValueError(
            f"Cannot transition from '{from_type}' to '{to_type}'. Supported downward "
            f"transitions from '{from_type}': {', '.join(from_handler.CHILD_TYPES) or 'none'}."
        )

    child_items = from_handler.get_child_entities(selection, to_type)
    return to_handler.build_from_items(design, grpc_client, child_items)
