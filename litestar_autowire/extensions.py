"""Extension protocols for Litestar Autowire."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from litestar.config.app import AppConfig

    from litestar_autowire.config import AutowireConfig


class AutowireExtension(Protocol):
    """Hook object for extending Autowire's discovery lifecycle.

    Custom extensions are passed to ``AutowireConfig.extensions``. They run
    after built-in discovery and can mutate the Litestar ``AppConfig``.
    """

    name: str

    def on_autowire(self, app_config: "AppConfig", config: "AutowireConfig") -> "AppConfig":
        """Apply extension behavior and return the updated app config."""
        ...
