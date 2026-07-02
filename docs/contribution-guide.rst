==================
Contribution Guide
==================

Development Setup
=================

.. code-block:: bash

    git clone https://github.com/cofin/litestar-autowire.git
    cd litestar-autowire
    uv sync --all-extras --dev

Useful Commands
===============

.. code-block:: bash

    make test
    make lint
    make docs
    make build

Contribution Notes
==================

- Keep public API changes covered by focused tests.
- Keep optional third-party integrations behind explicit configuration.
- Update README and docs when behavior changes.
- Run the narrow checks that cover the files you touched before opening a pull
  request.
