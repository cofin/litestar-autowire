"""Package walkers used by :class:`litestar_autowire.AutowirePlugin`."""

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from types import ModuleType
from typing import Any

from litestar import Controller
from litestar.events import EventListener

logger = logging.getLogger(__name__)

_controller_cache: dict[tuple[tuple[str, ...], tuple[str, ...]], list[type[Controller]]] = {}
_listener_cache: dict[tuple[tuple[str, ...], tuple[str, ...]], list[EventListener]] = {}
_feature_package_cache: dict[str, tuple[str, ...]] = {}
_module_import_cache: dict[str, ModuleType | None] = {}


def clear_autowire_cache() -> None:
    """Clear cached discovery results."""
    _controller_cache.clear()
    _listener_cache.clear()
    _feature_package_cache.clear()
    _module_import_cache.clear()


def find_controllers_in_module(module: ModuleType) -> list[type[Controller]]:
    """Return controller classes defined directly in ``module``.

    Imported controller classes are ignored so shared base classes and re-exported
    controllers do not get registered twice.
    """
    controllers: list[type[Controller]] = []
    module_name = module.__name__
    for name, value in inspect.getmembers(module, inspect.isclass):
        if value is Controller:
            continue
        if name.startswith("_"):
            continue
        if getattr(value, "__module__", None) != module_name:
            continue
        if issubclass(value, Controller):
            controllers.append(value)
    return controllers


def find_listeners_in_module(module: ModuleType) -> list[EventListener]:
    """Return Litestar event listeners defined in ``module``."""
    return [value for _, value in inspect.getmembers(module) if isinstance(value, EventListener)]


def discover_controllers(
    packages: tuple[str, ...] | list[str],
    module_names: tuple[str, ...] | list[str] = ("controllers", "routes", "controller", "route"),
) -> list[type[Controller]]:
    """Discover ``Controller`` subclasses under package feature folders."""
    package_tuple = tuple(packages)
    module_tuple = tuple(module_names)
    cache_key = (package_tuple, module_tuple)
    cached = _controller_cache.get(cache_key)
    if cached is not None:
        return list(cached)

    discovered: list[type[Controller]] = []
    for feature_package in discover_feature_packages(package_tuple):
        for module_name in module_tuple:
            module_path = f"{feature_package}.{module_name}"
            discovered.extend(_discover_controllers_in_module_path(module_path))

    result = _dedupe(discovered)
    _controller_cache[cache_key] = result
    return list(result)


def discover_listeners(
    packages: tuple[str, ...] | list[str],
    module_names: tuple[str, ...] | list[str] = ("events", "listeners"),
) -> list[EventListener]:
    """Discover Litestar event listeners under package feature folders."""
    package_tuple = tuple(packages)
    module_tuple = tuple(module_names)
    cache_key = (package_tuple, module_tuple)
    cached = _listener_cache.get(cache_key)
    if cached is not None:
        return list(cached)

    discovered: list[EventListener] = []
    for feature_package in discover_feature_packages(package_tuple):
        for module_name in module_tuple:
            module_path = f"{feature_package}.{module_name}"
            discovered.extend(_discover_listeners_in_module_path(module_path))
    result = _dedupe(discovered)
    _listener_cache[cache_key] = result
    return list(result)


def discover_queue_tasks(
    packages: tuple[str, ...] | list[str],
    module_names: tuple[str, ...] | list[str] = ("jobs",),
    *,
    force_reload: bool = False,
) -> tuple[str, ...]:
    """Import ``litestar_queues`` task modules below the configured packages.

    Returns:
        A sorted tuple of registered task names reported by ``litestar_queues``.

    Raises:
        RuntimeError: If task discovery is enabled without installing
            ``litestar-autowire[queues]`` or a compatible ``litestar_queues``.
    """
    try:
        queues = importlib.import_module("litestar_queues")
    except ModuleNotFoundError as exc:
        if exc.name == "litestar_queues":
            msg = "Task discovery requires the optional 'litestar-autowire[queues]' dependency."
            raise RuntimeError(msg) from exc
        raise

    discover_tasks = getattr(queues, "discover_tasks", None)
    if discover_tasks is None:
        msg = "The installed 'litestar_queues' package does not expose discover_tasks()."
        raise RuntimeError(msg)

    task_names: set[str] = set()
    for package_name in packages:
        for module_name in module_names:
            discovered = discover_tasks(package_name, subpackage=module_name, force_reload=force_reload)
            task_names.update(discovered)
    return tuple(sorted(task_names))


def discover_feature_packages(packages: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Discover configured package roots and their direct feature child packages."""
    discovered: list[str] = []
    seen: set[str] = set()
    for package_name in packages:
        for feature_package in _iter_feature_packages(package_name):
            if feature_package in seen:
                continue
            seen.add(feature_package)
            discovered.append(feature_package)
    return tuple(discovered)


def _iter_feature_packages(package_name: str) -> list[str]:
    cached = _feature_package_cache.get(package_name)
    if cached is not None:
        return list(cached)

    try:
        root = importlib.import_module(package_name)
    except ModuleNotFoundError as exc:
        if _is_requested_module_missing(package_name, exc):
            logger.warning("Autowire package not found: %s", package_name)
            _feature_package_cache[package_name] = ()
            return []
        raise

    root_paths = getattr(root, "__path__", None)
    if root_paths is None:
        logger.warning("Autowire package has no __path__: %s", package_name)
        _feature_package_cache[package_name] = ()
        return []

    feature_packages = _find_feature_packages(root.__name__, tuple(str(path) for path in root_paths))
    _feature_package_cache[package_name] = tuple(feature_packages)
    return list(feature_packages)


def _find_feature_packages(root_name: str, root_paths: tuple[str, ...]) -> list[str]:
    feature_packages = [root_name]
    seen = {root_name}

    def add_package(module_name: str) -> None:
        if module_name in seen:
            return
        seen.add(module_name)
        feature_packages.append(module_name)

    for _, module_name, is_package in pkgutil.iter_modules(root_paths, prefix=f"{root_name}."):
        if is_package:
            add_package(module_name)

    for root_path in root_paths:
        try:
            child_paths = sorted(Path(root_path).iterdir(), key=lambda path: path.name)
        except OSError:
            continue
        for child_path in child_paths:
            if not _is_feature_directory(child_path):
                continue
            add_package(f"{root_name}.{child_path.name}")

    return feature_packages


def _is_feature_directory(path: Path) -> bool:
    return path.is_dir() and not path.name.startswith(("_", "."))


def _discover_controllers_in_module_path(module_path: str) -> list[type[Controller]]:
    module = _import_optional_module(module_path)
    if module is None:
        return []

    controllers: list[type[Controller]] = []
    if hasattr(module, "__path__"):
        for _, child_name, is_package in pkgutil.walk_packages(module.__path__, prefix=f"{module.__name__}."):
            if is_package:
                continue
            child_module = _import_optional_module(child_name)
            if child_module is not None:
                controllers.extend(find_controllers_in_module(child_module))
    controllers.extend(find_controllers_in_module(module))
    return controllers


def _discover_listeners_in_module_path(module_path: str) -> list[EventListener]:
    module = _import_optional_module(module_path)
    if module is None:
        return []

    listeners: list[EventListener] = []
    if hasattr(module, "__path__"):
        for _, child_name, is_package in pkgutil.walk_packages(module.__path__, prefix=f"{module.__name__}."):
            if is_package:
                continue
            child_module = _import_optional_module(child_name)
            if child_module is not None:
                listeners.extend(find_listeners_in_module(child_module))
    listeners.extend(find_listeners_in_module(module))
    return listeners


def _import_optional_module(module_path: str) -> ModuleType | None:
    if module_path in _module_import_cache:
        return _module_import_cache[module_path]

    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        if _is_requested_module_missing(module_path, exc):
            _module_import_cache[module_path] = None
            return None
        raise
    _module_import_cache[module_path] = module
    return module


def import_optional_module(module_path: str) -> ModuleType | None:
    """Import an optional module without hiding dependency import failures."""
    return _import_optional_module(module_path)


def _is_requested_module_missing(module_path: str, exc: ModuleNotFoundError) -> bool:
    missing_name = exc.name or ""
    return module_path == missing_name or module_path.startswith(f"{missing_name}.")


def _dedupe(items: list[Any]) -> list[Any]:
    seen: set[int] = set()
    result: list[Any] = []
    for item in items:
        key = id(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
