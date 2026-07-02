"""Shared pytest configuration."""

from pathlib import Path

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Apply the unit marker to tests under ``tests/unit``."""
    for item in items:
        if "unit" in Path(item.path).parts:
            item.add_marker(pytest.mark.unit)
