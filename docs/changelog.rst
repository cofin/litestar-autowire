=========
Changelog
=========

0.1.0
=====

- Initial Litestar Autowire release with ``AutowirePlugin`` and
  ``AutowireConfig`` for wiring domain packages into a Litestar app.
- Discovers controllers, event listeners, and optional Litestar Queues task
  modules from configured domain package roots and direct child domain packages.
- Supports built-in Dishka and Litestar Queues integrations, custom
  ``AutowireExtension`` hook objects, and domain-aware discovery logs.
