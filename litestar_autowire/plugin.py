"""Litestar plugin for domain package-based component discovery."""

import logging
from typing import TYPE_CHECKING, Any

from litestar.plugins import InitPluginProtocol

from litestar_autowire.config import AutowireConfig
from litestar_autowire.discovery import discover_controllers, discover_feature_packages, discover_listeners
from litestar_autowire.integrations import AutowireContext

if TYPE_CHECKING:
    from litestar import Controller
    from litestar.config.app import AppConfig

logger = logging.getLogger(__name__)


class AutowirePlugin(InitPluginProtocol):
    """Discover and register Litestar components from configured domain packages."""

    __slots__ = ("config",)

    def __init__(self, config: AutowireConfig | None = None) -> None:
        """Initialize the plugin.

        Args:
            config: Discovery configuration. The default config performs no
                discovery until domain packages are provided.
        """
        self.config = config or AutowireConfig()

    def on_app_init(self, app_config: "AppConfig") -> "AppConfig":
        """Discover configured components and add them to the app config."""
        controller_count = 0
        controller_inventory: dict[str, list[str]] = {}
        listener_count = 0
        feature_packages = discover_feature_packages(self.config.domain_packages) if self.config.domain_packages else ()

        controllers: list[type[Controller]] = []
        if self.config.domain_packages and self.config.discover_controllers:
            controllers = discover_controllers(self.config.domain_packages, self.config.controller_modules)
            controller_count = len(controllers)
            controller_inventory = self._controller_inventory_by_domain(controllers)

        listeners = []
        if self.config.domain_packages and self.config.discover_listeners:
            listeners = discover_listeners(self.config.domain_packages, self.config.listener_modules)
            listener_count = len(listeners)

        context = AutowireContext(
            app_config=app_config,
            config=self.config,
            feature_packages=feature_packages,
            controllers=controllers,
            listeners=listeners,
            router_class=self.config.router_class,
        )
        for integration in self.config.integrations:
            integration.on_autowire(context)

        if self.config.domain_packages and self.config.discover_controllers:
            self._register_controllers(context.app_config, context.controllers, context.router_class)
        if self.config.domain_packages and self.config.discover_listeners:
            context.app_config.listeners.extend(context.listeners)

        if self.config.log_discovered:
            self._defer_discovery_log(context, controller_count, controller_inventory, listener_count)
        return context.app_config

    def _defer_discovery_log(
        self,
        context: AutowireContext,
        controller_count: int,
        controller_inventory: dict[str, list[str]],
        listener_count: int,
    ) -> None:
        startup_hooks = list(context.app_config.on_startup or [])

        def log_autowire_discovery() -> None:
            self._log_discovery_summary(context, controller_count, controller_inventory, listener_count)

        startup_hooks.append(log_autowire_discovery)
        context.app_config.on_startup = startup_hooks

    def _log_discovery_summary(
        self,
        context: AutowireContext,
        controller_count: int,
        controller_inventory: dict[str, list[str]],
        listener_count: int,
    ) -> None:
        logger.info(
            "Autowire discovery complete: controllers=%d domains=%d listeners=%d tasks=%d",
            controller_count,
            len(controller_inventory),
            listener_count,
            context.task_count,
        )
        if controller_inventory:
            logger.debug("Autowire controller inventory by domain: %s", controller_inventory)

    def _register_controllers(
        self,
        app_config: "AppConfig",
        controllers: "list[type[Controller]]",
        router_class: "type[Any] | None",
    ) -> None:
        if not controllers:
            logger.warning(
                "Autowire discovered no controllers in domain packages: %s",
                ", ".join(self.config.domain_packages),
            )
            return

        if router_class is None:
            app_config.route_handlers.extend(controllers)
            return

        app_config.route_handlers.append(
            router_class(
                path="/",
                route_handlers=controllers,
                before_request=self.config.before_request,
                after_response=self.config.after_response,
            )
        )

    def _controller_inventory_by_domain(self, controllers: "list[type[Controller]]") -> dict[str, list[str]]:
        inventory: dict[str, list[str]] = {}
        for controller in controllers:
            module_name = getattr(controller, "__module__", "")
            domain = self._domain_name_for_module(module_name)
            inventory.setdefault(domain, []).append(controller.__name__)
        return {domain: sorted(names) for domain, names in sorted(inventory.items())}

    def _domain_name_for_module(self, module_name: str) -> str:
        for package_name in self.config.domain_packages:
            if module_name == package_name:
                return package_name.rsplit(".", maxsplit=1)[-1]

            prefix = f"{package_name}."
            if not module_name.startswith(prefix):
                continue

            remainder = module_name[len(prefix) :]
            first_part = remainder.split(".", maxsplit=1)[0]
            if first_part in self.config.controller_modules:
                return package_name.rsplit(".", maxsplit=1)[-1]
            return first_part
        return "unknown"
