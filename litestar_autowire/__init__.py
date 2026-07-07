"""Automatic route, listener, and task discovery for Litestar applications."""

from litestar_autowire.__metadata__ import __project__, __version__
from litestar_autowire.config import AutowireConfig
from litestar_autowire.discovery import (
    clear_autowire_cache,
    discover_controllers,
    discover_feature_packages,
    discover_listeners,
    discover_queue_tasks,
    find_controllers_in_module,
    find_listeners_in_module,
)
from litestar_autowire.integrations import (
    AutowireContext,
    AutowireIntegration,
    AutowireLoader,
    DishkaIntegration,
    QueuesIntegration,
)
from litestar_autowire.plugin import AutowirePlugin

__all__ = (
    "AutowireConfig",
    "AutowireContext",
    "AutowireIntegration",
    "AutowireLoader",
    "AutowirePlugin",
    "DishkaIntegration",
    "QueuesIntegration",
    "__project__",
    "__version__",
    "clear_autowire_cache",
    "discover_controllers",
    "discover_feature_packages",
    "discover_listeners",
    "discover_queue_tasks",
    "find_controllers_in_module",
    "find_listeners_in_module",
)
