"""Automatic route, listener, and task discovery for Litestar applications."""

from litestar_autowire.__metadata__ import __project__, __version__
from litestar_autowire.config import AutowireConfig
from litestar_autowire.discovery import (
    clear_autowire_cache,
    discover_controllers,
    discover_listeners,
    discover_queue_tasks,
    find_controllers_in_module,
    find_listeners_in_module,
)
from litestar_autowire.extensions import AutowireExtension
from litestar_autowire.plugin import AutowirePlugin

__all__ = (
    "AutowireConfig",
    "AutowireExtension",
    "AutowirePlugin",
    "__project__",
    "__version__",
    "clear_autowire_cache",
    "discover_controllers",
    "discover_listeners",
    "discover_queue_tasks",
    "find_controllers_in_module",
    "find_listeners_in_module",
)
