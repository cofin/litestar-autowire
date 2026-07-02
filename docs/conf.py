"""Sphinx configuration for Litestar Autowire."""

import sys
from pathlib import Path
from typing import Any

from litestar_autowire.__metadata__ import __version__

current_path = Path(__file__).parent.parent.resolve()
sys.path.append(str(current_path))

project = "Litestar Autowire"
copyright = "2026, Litestar Organization"  # noqa: A001
author = "Litestar Developers"
release = __version__
version = __version__

autowire_light_style = "tools.sphinx_ext.pygments_styles.LitestarAutowireLightStyle"
autowire_dark_style = "tools.sphinx_ext.pygments_styles.LitestarAutowireDarkStyle"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.githubpages",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "litestar": ("https://docs.litestar.dev/latest/", None),
}

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
    "special-members": "__init__",
}
autodoc_member_order = "bysource"
autosectionlabel_prefix_document = True
napoleon_google_docstring = True
nitpicky = False
smartquotes = False
suppress_warnings = ["app.add_node", "ref.python", "autodoc", "duplicate"]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "shibuya"
html_static_path = ["_static"]
html_js_files = ["versioning.js"]
html_css_files = ["custom.css", "style.css"]
html_title = "Litestar Autowire"
html_short_title = "Autowire"
html_favicon = "_static/favicon.svg"
html_show_sourcelink = True
html_context = {
    "source_type": "github",
    "source_user": "cofin",
    "source_repo": "litestar-autowire",
    "current_version": "latest",
    "version": release,
}
html_sidebars = {"**": []}
pygments_style = autowire_light_style
pygments_dark_style = autowire_dark_style

try:
    from shibuya._pygments import ShibuyaPygmentsBridge
except ModuleNotFoundError:
    pass
else:
    # Match the sibling docs setups: point Shibuya's dark bridge at our style
    # directly instead of relying on plugin-style scanning of the top-level
    # ``tools`` package.
    ShibuyaPygmentsBridge.dark_style_name = autowire_dark_style

__all__ = ("setup",)


html_theme_options: "dict[str, Any]" = {
    "github_url": "https://github.com/cofin/litestar-autowire",
    "discord_url": "https://discord.gg/litestar",
    "discussion_url": "https://github.com/cofin/litestar-autowire/discussions",
    "navigation_with_keys": True,
    "globaltoc_expand_depth": 0,
    "accent_color": "amber",
    "light_logo": "_static/logo-icon.svg",
    "dark_logo": "_static/logo-icon.svg",
    "nav_links": [
        {
            "title": "Docs",
            "children": [
                {
                    "title": "Get Started",
                    "url": "getting-started",
                    "summary": "Install the plugin and autowire your first feature package.",
                },
                {
                    "title": "Changelog",
                    "url": "changelog",
                    "summary": "See what changed in each release.",
                },
            ],
        },
        {
            "title": "Developers",
            "children": [
                {
                    "title": "GitHub",
                    "url": "https://github.com/cofin/litestar-autowire",
                    "summary": "Browse the source repository and issue tracker.",
                },
                {
                    "title": "Contributing",
                    "url": "contribution-guide",
                    "summary": "Set up the repo and follow project conventions.",
                },
            ],
        },
        {
            "title": "Help",
            "children": [
                {
                    "title": "Discord",
                    "url": "https://discord.gg/litestar",
                    "summary": "Ask questions in the Litestar community.",
                },
                {
                    "title": "GitHub Discussions",
                    "url": "https://github.com/cofin/litestar-autowire/discussions",
                    "summary": "Discuss usage, design, and support topics on GitHub.",
                },
            ],
        },
    ],
}


def setup(app: Any) -> "dict[str, bool]":
    app.setup_extension("shibuya")
    return {"parallel_read_safe": True, "parallel_write_safe": True}
