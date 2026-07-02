===============
Getting Started
===============

Installation
============

.. code-block:: bash

    pip install litestar-autowire

Install optional integrations only when the app uses them:

.. code-block:: bash

    pip install "litestar-autowire[dishka]"
    pip install "litestar-autowire[queues]"

Domain Layout
=============

Autowire is for Litestar apps that group code by domain instead of by framework
layer:

.. code-block:: text

    my_app/
      domains/
        accounts/
          controllers.py
          events.py
          jobs.py
        billing/
          controllers.py

Each domain package owns its HTTP routes, event listeners, and background task
modules.

Wire Domains
============

.. code-block:: python

    # my_app/domains/accounts/controllers.py
    from litestar import Controller, get


    class AccountController(Controller):
        path = "/accounts"

        @get("/", sync_to_thread=False)
        def list_accounts(self) -> dict[str, str]:
            return {"status": "ok"}

Register the domain root once:

.. code-block:: python

    from litestar import Litestar
    from litestar_autowire import AutowireConfig, AutowirePlugin

    app = Litestar(
        plugins=[
            AutowirePlugin(
                AutowireConfig(domain_packages=["my_app.domains"]),
            )
        ],
    )

Autowire checks the configured domain package root and its direct child domain
packages for:

.. list-table::
    :header-rows: 1

    * - Component
      - Module names
    * - Controllers
      - ``controllers``, ``routes``, ``controller``, ``route``
    * - Event listeners
      - ``events``, ``listeners``
    * - Queue tasks
      - ``jobs``

Optional Integrations
=====================

Built-in integrations use string aliases:

.. code-block:: python

    AutowireConfig(
        domain_packages=["my_app.domains"],
        extensions=["dishka", "queues"],
    )

``dishka`` wraps discovered controllers in Dishka's Litestar router. Dishka is
not enabled merely because it is installed; configure Dishka separately with
``setup_dishka(...)``.

``queues`` imports task modules with ``litestar_queues.discover_tasks``.
Litestar Queues still owns queue configuration, execution, workers, schedules,
and task results.

Unknown string aliases raise ``ValueError``. Use a hook object for custom
behavior.

Custom Extensions
=================

Custom extension objects run after built-in discovery and can mutate Litestar's
``AppConfig``:

.. code-block:: python

    from litestar.config.app import AppConfig
    from litestar_autowire import AutowireConfig


    class InventoryExtension:
        name = "inventory"

        def on_autowire(self, app_config: AppConfig, config: AutowireConfig) -> AppConfig:
            app_config.state["autowire_domain_packages"] = config.domain_packages
            return app_config


    config = AutowireConfig(
        domain_packages=["my_app.domains"],
        extensions=[InventoryExtension()],
    )

Custom extension names cannot reuse built-in names such as ``dishka`` or
``queues``.

Discovery Logs
==============

With ``log_discovered=True``, Autowire logs a startup summary with controller,
domain, listener, and task counts. Debug logging includes the controller
inventory grouped by domain.
