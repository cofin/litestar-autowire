=========
Changelog
=========

0.2.0
=====

- Renames ``AutowireConfig.extensions`` to ``integrations`` and replaces
  ``AutowireExtension`` with ``AutowireIntegration``.
- Adds ``AutowireContext`` and runs built-in and custom integrations through the
  same discovery pipeline.
- Adds ``AutowireLoader`` for loading per-domain modules with a callable or
  ``"pkg.module:func"`` string.
- Converts Dishka and Litestar Queues support into first-party integration
  objects behind the ``"dishka"`` and ``"queues"`` aliases.
- Exposes ``discover_feature_packages()`` for users that need the same package
  traversal semantics as Autowire.

0.1.0
=====

- Initial Litestar Autowire release with ``AutowirePlugin`` and
  ``AutowireConfig`` for wiring domain packages into a Litestar app.
- Discovers controllers, event listeners, and optional Litestar Queues task
  modules from configured domain package roots and direct child domain packages.
- Supports built-in Dishka and Litestar Queues integrations, custom extension
  hook objects, and domain-aware discovery logs.
