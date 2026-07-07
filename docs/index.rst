.. title:: Litestar Autowire

.. meta::
   :description: Domain package discovery of Litestar controllers, event listeners, and queue task modules.
   :keywords: Litestar, plugin, autowire, domains, controllers, listeners, discovery

.. container:: title-with-logo

   .. raw:: html

      <h1 class="brand-text" aria-label="Litestar Autowire">Litestar Autowire</h1>

Litestar Autowire wires domain packages into a Litestar application. Put each
domain's controllers, listeners, and queue tasks beside the domain code, then
register the domain root once.

Use it to keep app setup small while each domain owns its Litestar surface.

.. toctree::
    :hidden:
    :caption: Documentation

    getting-started
    contribution-guide
    changelog

.. grid:: 1 1 2 2
    :padding: 0
    :gutter: 2

    .. grid-item-card:: Get Started
        :link: getting-started
        :link-type: doc

        Install the plugin and wire a ``domains/`` package into Litestar.

    .. grid-item-card:: Changelog
        :link: changelog
        :link-type: doc

        Review what changed in each release.

Quick Example
=============

.. code-block:: text

    my_app/
      domains/
        accounts/
          controllers.py
          events.py
          jobs.py

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

Discovery Rules
===============

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

Extensions
==========

Use string aliases for built-in integrations:

.. code-block:: python

    AutowireConfig(
        domain_packages=["my_app.domains"],
        integrations=["dishka", "queues"],
    )

Unknown strings fail fast. Custom behavior belongs in integration objects passed
to ``integrations``. Use ``AutowireLoader`` for registries that need to load
per-domain modules with a callable such as ``"my_app.jobs:discover_jobs"``.

API
===

.. autoclass:: litestar_autowire.AutowireConfig
    :members:

.. autoclass:: litestar_autowire.AutowireContext
    :members:

.. autoclass:: litestar_autowire.AutowireIntegration
    :members:

.. autoclass:: litestar_autowire.AutowireLoader
    :members:

.. autoclass:: litestar_autowire.AutowirePlugin
    :members:

.. autofunction:: litestar_autowire.discover_feature_packages

.. autofunction:: litestar_autowire.discover_controllers

.. autofunction:: litestar_autowire.discover_listeners

.. autofunction:: litestar_autowire.discover_queue_tasks
