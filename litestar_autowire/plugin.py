"""Litestar plugin for domain package-based component discovery."""

import importlib
import logging
from typing import TYPE_CHECKING, Any, cast

from litestar.plugins import InitPluginProtocol

from litestar_autowire.config import AutowireConfig
from litestar_autowire.discovery import discover_controllers, discover_listeners, discover_queue_tasks

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
        if not self.config.domain_packages:
            return self._run_custom_extensions(app_config)

        controller_count = 0
        controller_inventory: dict[str, list[str]] = {}
        listener_count = 0
        task_count = 0

        if self.config.discover_controllers:
            controllers = discover_controllers(self.config.domain_packages, self.config.controller_modules)
            controller_count = len(controllers)
            controller_inventory = self._controller_inventory_by_domain(controllers)
            self._register_controllers(app_config, controllers)

        if self.config.discover_listeners:
            listeners = discover_listeners(self.config.domain_packages, self.config.listener_modules)
            listener_count = len(listeners)
            app_config.listeners.extend(listeners)

        if self.config.extension_enabled("queues"):
            task_names = discover_queue_tasks(
                self.config.domain_packages,
                self.config.task_modules,
                force_reload=self.config.force_reload_tasks,
            )
            task_count = len(task_names)

        app_config = self._run_custom_extensions(app_config)

        if self.config.log_discovered:
            logger.info(
                "Autowire discovery complete: controllers=%d domains=%d listeners=%d tasks=%d",
                controller_count,
                len(controller_inventory),
                listener_count,
                task_count,
            )
            if controller_inventory:
                logger.debug("Autowire controller inventory by domain: %s", controller_inventory)
        return app_config

    def _register_controllers(self, app_config: "AppConfig", controllers: "list[type[Controller]]") -> None:
        if not controllers:
            logger.warning(
                "Autowire discovered no controllers in domain packages: %s",
                ", ".join(self.config.domain_packages),
            )
            return

        router_class = self._resolve_router_class()
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

    def _resolve_router_class(self) -> "type[Any] | None":
        if self.config.router_class is not None:
            return self.config.router_class
        if not self.config.extension_enabled("dishka"):
            return None
        try:
            litestar_integration = importlib.import_module("dishka.integrations.litestar")
        except ModuleNotFoundError as exc:
            if exc.name == "dishka":
                msg = "Dishka router support requires the optional 'litestar-autowire[dishka]' dependency."
                raise RuntimeError(msg) from exc
            raise
        return cast("type[Any]", litestar_integration.DishkaRouter)

    def _run_custom_extensions(self, app_config: "AppConfig") -> "AppConfig":
        for extension in self.config.custom_extensions:
            app_config = extension.on_autowire(app_config, self.config)
        return app_config

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
