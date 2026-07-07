"""Integration objects for Litestar Autowire."""

import importlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, TypeAlias, TypeGuard, cast

from litestar_autowire.discovery import discover_queue_tasks, import_optional_module

if TYPE_CHECKING:
    from litestar import Controller
    from litestar.config.app import AppConfig
    from litestar.events import EventListener

    from litestar_autowire.config import AutowireConfig

AutowireLoaderCallable: TypeAlias = Callable[[str], object]


def _new_task_name_set() -> set[str]:
    return set()


@dataclass(slots=True)
class AutowireContext:
    """Shared state passed to Autowire integrations."""

    app_config: "AppConfig"
    config: "AutowireConfig"
    feature_packages: tuple[str, ...]
    controllers: list["type[Controller]"]
    listeners: list["EventListener"]
    router_class: type[Any] | None = None
    task_names: set[str] = field(default_factory=_new_task_name_set)


class AutowireIntegration(Protocol):
    """Protocol for extending Autowire's discovery lifecycle."""

    @property
    def name(self) -> str:
        """Integration name used for validation and diagnostics."""
        ...

    def on_autowire(self, context: AutowireContext) -> None:
        """Apply integration behavior to the shared Autowire context."""
        ...


AutowireIntegrationInput: TypeAlias = str | AutowireIntegration
AutowireIntegrationsInput: TypeAlias = Iterable[AutowireIntegrationInput] | AutowireIntegrationInput


@dataclass(frozen=True, slots=True, init=False)
class AutowireLoader:
    """Load discovered feature modules with a callable or dotted callable string."""

    name: str
    modules: tuple[str, ...]
    loader: AutowireLoaderCallable | str

    def __init__(
        self,
        *,
        name: str,
        modules: Iterable[str] | str,
        loader: AutowireLoaderCallable | str,
    ) -> None:
        """Initialize the loader integration.

        Args:
            name: Integration name used for validation and diagnostics.
            modules: Submodule names to load below each discovered feature package.
            loader: Callable or ``"pkg.module:func"`` string called with each
                existing module path.
        """
        if not name:
            msg = "AutowireLoader requires a non-empty name."
            raise ValueError(msg)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "modules", _as_tuple(modules))
        object.__setattr__(self, "loader", loader)

    def on_autowire(self, context: AutowireContext) -> None:
        """Load configured modules for every discovered feature package."""
        loader = resolve_dotted_callable(self.loader) if isinstance(self.loader, str) else self.loader
        for feature_package in context.feature_packages:
            for module_name in self.modules:
                module_path = f"{feature_package}.{module_name}"
                if import_optional_module(module_path) is None:
                    continue
                loader(module_path)


@dataclass(frozen=True, slots=True)
class DishkaIntegration:
    """Wrap discovered controllers with Dishka's Litestar router."""

    name: str = field(default="dishka", init=False)

    def on_autowire(self, context: AutowireContext) -> None:
        """Resolve and apply Dishka's router class."""
        if context.router_class is not None:
            return
        try:
            litestar_integration = importlib.import_module("dishka.integrations.litestar")
        except ModuleNotFoundError as exc:
            if exc.name == "dishka":
                msg = "Dishka router support requires the optional 'litestar-autowire[dishka]' dependency."
                raise RuntimeError(msg) from exc
            raise
        context.router_class = cast("type[Any]", litestar_integration.DishkaRouter)


@dataclass(frozen=True, slots=True)
class QueuesIntegration:
    """Discover Litestar Queues task modules."""

    name: str = field(default="queues", init=False)

    def on_autowire(self, context: AutowireContext) -> None:
        """Import task modules through ``litestar_queues.discover_tasks``."""
        task_names = discover_queue_tasks(
            context.config.domain_packages,
            context.config.task_modules,
            force_reload=context.config.force_reload_tasks,
        )
        context.task_names.update(task_names)


BUILTIN_INTEGRATIONS: dict[str, Callable[[], AutowireIntegration]] = {
    "dishka": DishkaIntegration,
    "queues": QueuesIntegration,
}
SUPPORTED_INTEGRATIONS = frozenset(BUILTIN_INTEGRATIONS)
BUILTIN_INTEGRATION_TYPES = (DishkaIntegration, QueuesIntegration)


def normalize_integrations(value: AutowireIntegrationsInput) -> tuple[AutowireIntegration, ...]:
    """Normalize integration aliases and objects into integration instances."""
    integrations = tuple(_normalize_integration(integration) for integration in _as_integration_tuple(value))
    _validate_integration_names(integrations)
    return integrations


def resolve_dotted_callable(value: str) -> AutowireLoaderCallable:
    """Resolve a ``pkg.module:func`` string to a callable."""
    module_name, separator, attribute_name = value.partition(":")
    if not separator:
        module_name, separator, attribute_name = value.rpartition(".")
    if not module_name or not attribute_name or not separator:
        msg = "Dotted callables must use 'pkg.module:func'."
        raise ValueError(msg)

    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name or module_name.startswith(f"{exc.name}."):
            msg = f"Could not import module for dotted callable: {module_name}"
            raise ValueError(msg) from exc
        raise

    try:
        value = getattr(module, attribute_name)
    except AttributeError as exc:
        msg = f"Dotted callable module {module_name!r} does not define {attribute_name!r}."
        raise ValueError(msg) from exc
    if not callable(value):
        msg = f"Dotted callable {module_name}:{attribute_name} is not callable."
        raise TypeError(msg)
    return cast("AutowireLoaderCallable", value)


def _normalize_integration(integration: AutowireIntegrationInput) -> AutowireIntegration:
    if isinstance(integration, str):
        integration_type = BUILTIN_INTEGRATIONS.get(integration)
        if integration_type is None:
            msg = f"Unsupported Autowire integration(s): {integration}"
            raise ValueError(msg)
        return integration_type()
    if not _is_autowire_integration(integration):
        msg = "Autowire integration objects must define a non-empty string 'name' and callable 'on_autowire'."
        raise TypeError(msg)
    return integration


def _as_integration_tuple(value: AutowireIntegrationsInput) -> tuple[AutowireIntegrationInput, ...]:
    if isinstance(value, str):
        return (value,)
    if _is_autowire_integration(value):
        return (value,)
    try:
        return tuple(cast("Iterable[AutowireIntegrationInput]", value))
    except TypeError as exc:
        msg = "Autowire integrations must be strings, integration objects, or iterables of those values."
        raise TypeError(msg) from exc


def _validate_integration_names(integrations: tuple[AutowireIntegration, ...]) -> None:
    seen: set[str] = set()
    for integration in integrations:
        if integration.name in seen:
            msg = f"Duplicate Autowire integration name: {integration.name}"
            raise ValueError(msg)
        seen.add(integration.name)
        if integration.name in SUPPORTED_INTEGRATIONS and not isinstance(integration, BUILTIN_INTEGRATION_TYPES):
            msg = f"Custom Autowire integration name conflict with built-in integration: {integration.name}"
            raise ValueError(msg)


def _is_autowire_integration(value: object) -> TypeGuard[AutowireIntegration]:
    if isinstance(value, str):
        return False
    name = getattr(value, "name", None)
    hook = getattr(value, "on_autowire", None)
    return isinstance(name, str) and bool(name) and callable(hook)


def _as_tuple(value: Iterable[str] | str) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    return tuple(value)
