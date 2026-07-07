"""Tests for the public Autowire plugin contract."""

import importlib
import logging
import sys
from pathlib import Path
from textwrap import dedent
from types import ModuleType
from typing import Any, cast

import pytest
from litestar import Litestar, Router, get
from litestar.logging.config import LoggingConfig
from litestar.testing import TestClient

from litestar_autowire import (
    AutowireConfig,
    AutowireContext,
    AutowireIntegration,
    AutowireLoader,
    AutowirePlugin,
    clear_autowire_cache,
)
from litestar_autowire.discovery import discover_controllers, discover_listeners


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content), encoding="utf-8")


def _create_package(tmp_path: Path, monkeypatch: Any) -> None:
    for module_name in list(sys.modules):
        if module_name == "example_app" or module_name.startswith("example_app."):
            del sys.modules[module_name]
    _write(tmp_path / "example_app" / "__init__.py")
    _write(tmp_path / "example_app" / "features" / "__init__.py")
    _write(tmp_path / "example_app" / "features" / "accounts" / "__init__.py")
    monkeypatch.syspath_prepend(str(tmp_path))


def test_autowire_plugin_registers_discovered_controllers(tmp_path: Path, monkeypatch: Any) -> None:
    _create_package(tmp_path, monkeypatch)
    _write(
        tmp_path / "example_app" / "features" / "accounts" / "controllers.py",
        """
        from litestar import Controller, get

        class AccountController(Controller):
            path = "/accounts"

            @get("/", sync_to_thread=False)
            def list_accounts(self) -> dict[str, str]:
                return {"status": "ok"}
        """,
    )

    clear_autowire_cache()
    app = Litestar(
        plugins=[AutowirePlugin(AutowireConfig(domain_packages=("example_app.features",)))],
    )

    with TestClient(app=app) as client:
        response = client.get("/accounts/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_autowire_plugin_registers_controllers_from_namespace_domain_packages(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    for module_name in list(sys.modules):
        if module_name == "namespace_app" or module_name.startswith("namespace_app."):
            del sys.modules[module_name]
    monkeypatch.syspath_prepend(str(tmp_path))
    _write(
        tmp_path / "namespace_app" / "features" / "accounts" / "controllers.py",
        """
        from litestar import Controller, get

        class NamespaceAccountController(Controller):
            path = "/namespace-accounts"

            @get("/", sync_to_thread=False)
            def list_accounts(self) -> dict[str, str]:
                return {"namespace": "ok"}
        """,
    )

    clear_autowire_cache()
    app = Litestar(
        plugins=[AutowirePlugin(AutowireConfig(domain_packages=("namespace_app.features",)))],
    )

    with TestClient(app=app) as client:
        response = client.get("/namespace-accounts/")

    assert response.status_code == 200
    assert response.json() == {"namespace": "ok"}


def test_discovery_reraises_missing_dependency_from_configured_package(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    for module_name in list(sys.modules):
        if module_name == "broken_app" or module_name.startswith("broken_app."):
            del sys.modules[module_name]
    monkeypatch.syspath_prepend(str(tmp_path))
    _write(tmp_path / "broken_app" / "__init__.py")
    _write(tmp_path / "broken_app" / "features" / "__init__.py", "import missing_autowire_dependency")

    clear_autowire_cache()
    with pytest.raises(ModuleNotFoundError) as exc_info:
        discover_controllers(("broken_app.features",))

    assert exc_info.value.name == "missing_autowire_dependency"


def test_missing_configured_package_is_ignored() -> None:
    clear_autowire_cache()

    assert discover_controllers(("missing_autowire_app.features",)) == []


def test_feature_package_and_listener_miss_discovery_is_cached(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    _create_package(tmp_path, monkeypatch)
    _write(
        tmp_path / "example_app" / "features" / "accounts" / "controllers.py",
        """
        from litestar import Controller

        class AccountController(Controller):
            path = "/accounts"
        """,
    )
    original_import_module = importlib.import_module
    import_counts: dict[str, int] = {}

    def import_module(name: str, package: str | None = None) -> ModuleType:
        import_counts[name] = import_counts.get(name, 0) + 1
        return original_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", import_module)

    clear_autowire_cache()
    discover_controllers(("example_app.features",))
    assert discover_listeners(("example_app.features",)) == []
    assert discover_listeners(("example_app.features",)) == []

    assert import_counts["example_app.features"] == 1
    assert import_counts["example_app.features.accounts.events"] == 1
    assert import_counts["example_app.features.accounts.listeners"] == 1


def test_autowire_plugin_can_wrap_discovered_controllers_in_router(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    _create_package(tmp_path, monkeypatch)
    _write(
        tmp_path / "example_app" / "features" / "accounts" / "routes.py",
        """
        from litestar import Controller, get

        class AccountRoutes(Controller):
            path = "/accounts"

            @get("/detail", sync_to_thread=False)
            def detail(self) -> dict[str, str]:
                return {"wrapped": "yes"}
        """,
    )

    clear_autowire_cache()
    app = Litestar(
        plugins=[
            AutowirePlugin(
                AutowireConfig(
                    domain_packages=("example_app.features",),
                    router_class=Router,
                ),
            )
        ],
    )

    with TestClient(app=app) as client:
        response = client.get("/accounts/detail")

    assert response.status_code == 200
    assert response.json() == {"wrapped": "yes"}


def test_autowire_plugin_can_enable_dishka_router_integration(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    _create_package(tmp_path, monkeypatch)
    _write(
        tmp_path / "example_app" / "features" / "accounts" / "controllers.py",
        """
        from litestar import Controller, get

        class AccountController(Controller):
            path = "/accounts"

            @get("/", sync_to_thread=False)
            def list_accounts(self) -> dict[str, str]:
                return {"extension": "dishka"}
        """,
    )
    fake_dishka = ModuleType("dishka")
    fake_integrations = ModuleType("dishka.integrations")
    fake_litestar = ModuleType("dishka.integrations.litestar")
    fake_litestar.DishkaRouter = Router  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "dishka", fake_dishka)
    monkeypatch.setitem(sys.modules, "dishka.integrations", fake_integrations)
    monkeypatch.setitem(sys.modules, "dishka.integrations.litestar", fake_litestar)

    clear_autowire_cache()
    app = Litestar(
        plugins=[
            AutowirePlugin(
                AutowireConfig(
                    domain_packages=["example_app.features"],
                    integrations=["dishka"],
                ),
            )
        ],
    )

    with TestClient(app=app) as client:
        response = client.get("/accounts/")

    assert response.status_code == 200
    assert response.json() == {"extension": "dishka"}


def test_autowire_config_normalizes_and_validates_integrations() -> None:
    config = AutowireConfig(integrations="dishka")

    assert tuple(integration.name for integration in config.integrations) == ("dishka",)
    assert config.integration_enabled("dishka")
    with pytest.raises(ValueError, match="Unsupported Autowire integration"):
        AutowireConfig(integrations=["not-installed-by-default"])


def test_autowire_config_accepts_custom_integration_objects() -> None:
    class CustomIntegration:
        name = "custom"

        def on_autowire(self, context: AutowireContext) -> None:
            assert isinstance(context.config, AutowireConfig)

    integration: AutowireIntegration = CustomIntegration()
    config = AutowireConfig(integrations=[integration])

    assert config.integrations == (integration,)
    assert config.integration_enabled("custom")


def test_autowire_config_rejects_invalid_custom_integration_objects() -> None:
    with pytest.raises(TypeError, match="Autowire integration objects"):
        AutowireConfig(integrations=cast("Any", [object()]))


def test_autowire_config_rejects_custom_integration_builtin_name_collisions() -> None:
    class QueuesExtension:
        name = "queues"

        def on_autowire(self, context: AutowireContext) -> None:
            assert isinstance(context.config, AutowireConfig)

    with pytest.raises(ValueError, match="conflict with built-in integration"):
        AutowireConfig(integrations=[QueuesExtension()])


def test_autowire_plugin_runs_custom_integrations(tmp_path: Path, monkeypatch: Any) -> None:
    _create_package(tmp_path, monkeypatch)

    class CustomRouteIntegration:
        name = "custom-route"

        def on_autowire(self, context: AutowireContext) -> None:
            @get("/custom-extension", sync_to_thread=False)
            def custom_extension() -> dict[str, str]:
                return {"integration": self.name, "domain_packages": ",".join(context.config.domain_packages)}

            context.app_config.route_handlers.append(custom_extension)

    clear_autowire_cache()
    app = Litestar(
        plugins=[
            AutowirePlugin(
                AutowireConfig(
                    domain_packages=["example_app.features"],
                    discover_controllers=False,
                    discover_listeners=False,
                    integrations=[CustomRouteIntegration()],
                ),
            )
        ],
    )

    with TestClient(app=app) as client:
        response = client.get("/custom-extension")

    assert response.status_code == 200
    assert response.json() == {"integration": "custom-route", "domain_packages": "example_app.features"}


def test_autowire_loader_calls_callable_for_existing_feature_modules(tmp_path: Path, monkeypatch: Any) -> None:
    _create_package(tmp_path, monkeypatch)
    _write(tmp_path / "example_app" / "features" / "accounts" / "jobs.py")
    calls: list[str] = []

    def load_jobs(module_path: str) -> None:
        calls.append(module_path)

    clear_autowire_cache()
    Litestar(
        plugins=[
            AutowirePlugin(
                AutowireConfig(
                    domain_packages=["example_app.features"],
                    discover_controllers=False,
                    discover_listeners=False,
                    integrations=[
                        AutowireLoader(
                            name="dma_jobs",
                            modules="jobs",
                            loader=load_jobs,
                        )
                    ],
                ),
            )
        ],
    )

    assert calls == ["example_app.features.accounts.jobs"]


def test_autowire_loader_resolves_dotted_loader_strings(tmp_path: Path, monkeypatch: Any) -> None:
    _create_package(tmp_path, monkeypatch)
    _write(tmp_path / "example_app" / "features" / "accounts" / "jobs.py")
    _write(
        tmp_path / "example_loader.py",
        """
        CALLED = []

        def load_jobs(module_path: str) -> None:
            CALLED.append(module_path)
        """,
    )

    clear_autowire_cache()
    Litestar(
        plugins=[
            AutowirePlugin(
                AutowireConfig(
                    domain_packages=["example_app.features"],
                    discover_controllers=False,
                    discover_listeners=False,
                    integrations=[
                        AutowireLoader(
                            name="dma_jobs",
                            modules="jobs",
                            loader="example_loader:load_jobs",
                        )
                    ],
                ),
            )
        ],
    )

    loader_module = importlib.import_module("example_loader")
    assert loader_module.CALLED == ["example_app.features.accounts.jobs"]


def test_autowire_loader_reraises_missing_dependency_from_existing_module(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    _create_package(tmp_path, monkeypatch)
    _write(
        tmp_path / "example_app" / "features" / "accounts" / "jobs.py",
        """
        import missing_autowire_job_dependency
        """,
    )
    calls: list[str] = []

    def load_jobs(module_path: str) -> None:
        calls.append(module_path)

    clear_autowire_cache()
    with pytest.raises(ModuleNotFoundError) as exc_info:
        Litestar(
            plugins=[
                AutowirePlugin(
                    AutowireConfig(
                        domain_packages=["example_app.features"],
                        discover_controllers=False,
                        discover_listeners=False,
                        integrations=[
                            AutowireLoader(
                                name="dma_jobs",
                                modules="jobs",
                                loader=load_jobs,
                            )
                        ],
                    ),
                )
            ],
        )

    assert exc_info.value.name == "missing_autowire_job_dependency"
    assert calls == []


def test_autowire_plugin_logs_loaded_domains(
    tmp_path: Path,
    monkeypatch: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _create_package(tmp_path, monkeypatch)
    _write(tmp_path / "example_app" / "features" / "billing" / "__init__.py")
    _write(
        tmp_path / "example_app" / "features" / "accounts" / "controllers.py",
        """
        from litestar import Controller

        class AccountController(Controller):
            path = "/accounts"
        """,
    )
    _write(
        tmp_path / "example_app" / "features" / "billing" / "routes.py",
        """
        from litestar import Controller

        class BillingController(Controller):
            path = "/billing"
        """,
    )

    clear_autowire_cache()
    with caplog.at_level(logging.DEBUG, logger="litestar_autowire.plugin"):
        app = Litestar(
            logging_config=LoggingConfig(configure_root_logger=False),
            plugins=[
                AutowirePlugin(
                    AutowireConfig(
                        domain_packages=("example_app.features",),
                        discover_listeners=False,
                    )
                )
            ],
        )
        assert not any(record.message.startswith("Autowire discovery complete") for record in caplog.records)

        startup_hook = cast("Any", app.on_startup[-1])
        startup_hook()

    discovery_summary = next(
        record for record in caplog.records if record.message.startswith("Autowire discovery complete")
    )
    inventory = next(record for record in caplog.records if record.message.startswith("Autowire controller inventory"))

    assert discovery_summary.message == "Autowire discovery complete: controllers=2 domains=2 listeners=0 tasks=0"
    assert inventory.args == {"accounts": ["AccountController"], "billing": ["BillingController"]}


def test_autowire_plugin_logs_loader_task_count_on_startup(
    tmp_path: Path,
    monkeypatch: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _create_package(tmp_path, monkeypatch)
    _write(tmp_path / "example_app" / "features" / "accounts" / "jobs.py")

    def load_jobs(module_path: str) -> int:
        assert module_path == "example_app.features.accounts.jobs"
        return 3

    clear_autowire_cache()
    with caplog.at_level(logging.INFO, logger="litestar_autowire.plugin"):
        app = Litestar(
            logging_config=LoggingConfig(configure_root_logger=False),
            plugins=[
                AutowirePlugin(
                    AutowireConfig(
                        domain_packages=("example_app.features",),
                        discover_controllers=False,
                        discover_listeners=False,
                        integrations=[AutowireLoader(name="example_jobs", modules="jobs", loader=load_jobs)],
                    ),
                )
            ],
        )
        assert not any(record.message.startswith("Autowire discovery complete") for record in caplog.records)

        startup_hook = cast("Any", app.on_startup[-1])
        startup_hook()

    discovery_summary = next(
        record for record in caplog.records if record.message.startswith("Autowire discovery complete")
    )
    assert discovery_summary.message == "Autowire discovery complete: controllers=0 domains=0 listeners=0 tasks=3"


def test_autowire_plugin_registers_discovered_listeners(tmp_path: Path, monkeypatch: Any) -> None:
    _create_package(tmp_path, monkeypatch)
    _write(
        tmp_path / "example_app" / "features" / "accounts" / "events.py",
        """
        from litestar.events import listener

        @listener("account.created")
        async def account_created(data: object) -> None:
            return None
        """,
    )

    clear_autowire_cache()
    app = Litestar(
        plugins=[
            AutowirePlugin(
                AutowireConfig(
                    domain_packages=("example_app.features",),
                    discover_controllers=False,
                    discover_listeners=True,
                )
            )
        ],
    )

    assert len(app.event_emitter.listeners["account.created"]) == 1


def test_autowire_plugin_can_discover_litestar_queue_tasks(tmp_path: Path, monkeypatch: Any) -> None:
    _create_package(tmp_path, monkeypatch)
    calls: list[tuple[str, str, bool]] = []
    fake_litestar_queues = ModuleType("litestar_queues")

    def discover_tasks(package: str, subpackage: str = "jobs", *, force_reload: bool = False) -> tuple[str, ...]:
        calls.append((package, subpackage, force_reload))
        return ("accounts.send_email",)

    fake_litestar_queues.discover_tasks = discover_tasks  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "litestar_queues", fake_litestar_queues)

    Litestar(
        plugins=[
            AutowirePlugin(
                AutowireConfig(
                    domain_packages=("example_app.features",),
                    discover_controllers=False,
                    discover_listeners=False,
                    integrations=["queues"],
                )
            )
        ],
    )

    assert calls == [("example_app.features", "jobs", False)]
