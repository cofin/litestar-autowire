"""Configuration objects for Litestar Autowire."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, TypeGuard, cast

from litestar_autowire.extensions import AutowireExtension

SUPPORTED_EXTENSIONS = frozenset({"dishka", "queues"})
AutowireExtensionInput = str | AutowireExtension
AutowireExtensionsInput = Iterable[AutowireExtensionInput] | AutowireExtensionInput


@dataclass(frozen=True, slots=True, init=False)
class AutowireConfig:
    """Configure domain package-based Litestar component discovery.

    Attributes:
        domain_packages: Dotted domain package names to inspect. Each package
            and its direct child packages are checked for configured
            controller, listener, and task submodules.
        extensions: Optional built-in integration names or custom extension
            hook objects. Supported built-in values are ``"dishka"`` to wrap
            discovered controllers in Dishka's Litestar router and ``"queues"``
            to import task modules with ``litestar_queues.discover_tasks``.
        discover_controllers: Register discovered ``Controller`` subclasses.
        discover_listeners: Register discovered Litestar event listeners.
        controller_modules: Submodule names that may contain controllers.
        listener_modules: Submodule names that may contain event listeners.
        task_modules: Subpackage names that may contain ``litestar_queues`` tasks.
        router_class: Optional router class used to wrap discovered controllers.
            Pass ``litestar.Router`` or a compatible router type.
        before_request: Optional hook attached to the wrapper router.
        after_response: Optional hook attached to the wrapper router.
        force_reload_tasks: Re-import task modules already loaded by
            ``litestar_queues``.
        log_discovered: Emit an info log summarizing discovered components.
    """

    domain_packages: tuple[str, ...] = ()
    extensions: tuple[AutowireExtensionInput, ...] = ()
    discover_controllers: bool = True
    discover_listeners: bool = True
    controller_modules: tuple[str, ...] = ("controllers", "routes", "controller", "route")
    listener_modules: tuple[str, ...] = ("events", "listeners")
    task_modules: tuple[str, ...] = ("jobs",)
    router_class: type[Any] | None = None
    before_request: Any | None = None
    after_response: Any | None = None
    force_reload_tasks: bool = False
    log_discovered: bool = True

    def __init__(
        self,
        *,
        domain_packages: Iterable[str] | str = (),
        extensions: AutowireExtensionsInput = (),
        discover_controllers: bool = True,
        discover_listeners: bool = True,
        controller_modules: Iterable[str] | str = ("controllers", "routes", "controller", "route"),
        listener_modules: Iterable[str] | str = ("events", "listeners"),
        task_modules: Iterable[str] | str = ("jobs",),
        router_class: type[Any] | None = None,
        before_request: Any | None = None,
        after_response: Any | None = None,
        force_reload_tasks: bool = False,
        log_discovered: bool = True,
    ) -> None:
        """Initialize and normalize discovery configuration."""
        normalized_extensions = _as_extension_tuple(extensions)
        _validate_extensions(normalized_extensions)

        object.__setattr__(self, "domain_packages", _as_tuple(domain_packages))
        object.__setattr__(self, "extensions", normalized_extensions)
        object.__setattr__(self, "discover_controllers", discover_controllers)
        object.__setattr__(self, "discover_listeners", discover_listeners)
        object.__setattr__(self, "controller_modules", _as_tuple(controller_modules))
        object.__setattr__(self, "listener_modules", _as_tuple(listener_modules))
        object.__setattr__(self, "task_modules", _as_tuple(task_modules))
        object.__setattr__(self, "router_class", router_class)
        object.__setattr__(self, "before_request", before_request)
        object.__setattr__(self, "after_response", after_response)
        object.__setattr__(self, "force_reload_tasks", force_reload_tasks)
        object.__setattr__(self, "log_discovered", log_discovered)

    def extension_enabled(self, name: str) -> bool:
        """Return whether a built-in optional integration is enabled."""
        return name in self.extension_names

    @property
    def extension_names(self) -> tuple[str, ...]:
        """Return enabled built-in extension names."""
        return tuple(extension for extension in self.extensions if isinstance(extension, str))

    @property
    def custom_extensions(self) -> tuple[AutowireExtension, ...]:
        """Return custom extension hook objects."""
        return tuple(extension for extension in self.extensions if not isinstance(extension, str))


def _as_tuple(value: Iterable[str] | str) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    return tuple(value)


def _as_extension_tuple(value: AutowireExtensionsInput) -> tuple[AutowireExtensionInput, ...]:
    if isinstance(value, str):
        return (value,)
    if _is_autowire_extension(value):
        return (value,)
    try:
        return tuple(cast("Iterable[AutowireExtensionInput]", value))
    except TypeError as exc:
        msg = "Autowire extensions must be strings, extension objects, or iterables of those values."
        raise TypeError(msg) from exc


def _validate_extensions(extensions: tuple[AutowireExtensionInput, ...]) -> None:
    unknown = sorted(
        extension for extension in extensions if isinstance(extension, str) and extension not in SUPPORTED_EXTENSIONS
    )
    if unknown:
        msg = f"Unsupported Autowire extension(s): {', '.join(unknown)}"
        raise ValueError(msg)

    for extension in extensions:
        if isinstance(extension, str):
            continue
        _validate_custom_extension(extension)


def _validate_custom_extension(extension: object) -> None:
    name = getattr(extension, "name", None)
    hook = getattr(extension, "on_autowire", None)
    if not isinstance(name, str) or not name or not callable(hook):
        msg = "Autowire extension objects must define a non-empty string 'name' and callable 'on_autowire'."
        raise TypeError(msg)
    if name in SUPPORTED_EXTENSIONS:
        msg = f"Custom Autowire extension name conflict with built-in extension: {name}"
        raise ValueError(msg)


def _is_autowire_extension(value: object) -> TypeGuard[AutowireExtension]:
    if isinstance(value, str):
        return False
    name = getattr(value, "name", None)
    hook = getattr(value, "on_autowire", None)
    return isinstance(name, str) and callable(hook)
