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
        integrations=["dishka", "queues"],
    )

``dishka`` wraps discovered controllers in Dishka's Litestar router. Dishka is
not enabled merely because it is installed; configure Dishka separately with
``setup_dishka(...)``.

``queues`` imports task modules with ``litestar_queues.discover_tasks``.
Litestar Queues still owns queue configuration, execution, workers, schedules,
and task results.

Unknown string aliases raise ``ValueError``.

Autowire Loader
===============

Use ``AutowireLoader`` when another registry needs each discovered domain module
loaded:

.. code-block:: python

    from litestar_autowire import AutowireConfig, AutowireLoader

    config = AutowireConfig(
        domain_packages=["my_app.domains"],
        integrations=[
            AutowireLoader(
                name="inventory_jobs",
                modules="jobs",
                loader="my_app.jobs:discover_jobs",
            )
        ],
    )

The loader receives existing module paths such as
``my_app.domains.accounts.jobs``. Use the ``pkg.module:func`` form to make the
module import and callable lookup explicit. If the loader returns an integer,
Autowire adds it to the startup task count.

Custom Integrations
===================

Custom integration objects run after built-in discovery and can mutate the
shared Autowire context:

.. code-block:: python

    from litestar_autowire import AutowireConfig, AutowireContext


    class InventoryIntegration:
        name = "inventory"

        def on_autowire(self, context: AutowireContext) -> None:
            context.app_config.state["autowire_domain_packages"] = context.config.domain_packages


    config = AutowireConfig(
        domain_packages=["my_app.domains"],
        integrations=[InventoryIntegration()],
    )

Custom integration names cannot reuse built-in names such as ``dishka`` or
``queues``.

Discovery Logs
==============

By default, Autowire defers discovery logs to the Litestar startup lifespan.
The summary includes controller, domain, listener, and task counts. Debug
logging includes the controller inventory grouped by domain. Set
``log_discovered=False`` to disable these logs.
