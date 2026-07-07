"""Configuration objects for Litestar Autowire."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from litestar_autowire.integrations import AutowireIntegration, AutowireIntegrationsInput, normalize_integrations

SUPPORTED_INTEGRATIONS = frozenset({"dishka", "queues"})


@dataclass(frozen=True, slots=True, init=False)
class AutowireConfig:
    """Configure domain package-based Litestar component discovery.

    Attributes:
        domain_packages: Dotted domain package names to inspect. Each package
            and its direct child packages are checked for configured
            controller, listener, and task submodules.
        integrations: Optional built-in integration names or custom integration
            objects. Supported built-in values are ``"dishka"`` to wrap
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
        log_discovered: Emit startup logs summarizing discovered components.
    """

    domain_packages: tuple[str, ...] = ()
    integrations: tuple[AutowireIntegration, ...] = ()
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
        integrations: AutowireIntegrationsInput = (),
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
        extensions: Any | None = None,
    ) -> None:
        """Initialize and normalize discovery configuration."""
        if extensions is not None:
            msg = "AutowireConfig.extensions was renamed to integrations. Use integrations=[...]."
            raise TypeError(msg)

        object.__setattr__(self, "domain_packages", _as_tuple(domain_packages))
        object.__setattr__(self, "integrations", normalize_integrations(integrations))
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

    def integration_enabled(self, name: str) -> bool:
        """Return whether an integration with ``name`` is enabled."""
        return any(integration.name == name for integration in self.integrations)


def _as_tuple(value: Iterable[str] | str) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    return tuple(value)
