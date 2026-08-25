"""Configuration file for the Sphinx documentation builder."""

from datetime import datetime
import os

from ansys_sphinx_theme import (
    ansys_favicon,
    ansys_logo_white,
    ansys_logo_white_cropped,
    get_version_match,
    watermark,
)

from ansys.geometry.mcp import __version__

# Project information
project = "pyansys-geometry-mcp"
copyright = f"(c) {datetime.now().year} ANSYS, Inc. All rights reserved"
author = "ANSYS, Inc."
release = version = __version__
cname = os.getenv("DOCUMENTATION_CNAME", default="pyansys-geometry-mcp.docs.pyansys.com")
switcher_version = get_version_match(__version__)

html_theme = "ansys_sphinx_theme"
html_short_title = html_title = "PyAnsys Geometry MCP"
html_baseurl = f"https://{cname}/version/stable"

html_context = {
    "github_user": "ansys",
    "github_repo": "pyansys-geometry-mcp",
    "github_version": "main",
    "doc_path": "doc/source",
}
html_theme_options = {
    "logo": "pyansys",
    "switcher": {
        "json_url": f"https://{cname}/versions.json",
        "version_match": switcher_version,
    },
    "check_switcher": False,
    "github_url": "https://github.com/ansys/pyansys-geometry-mcp",
    "show_prev_next": False,
    "show_breadcrumbs": True,
    "collapse_navigation": True,
    "use_edit_page_button": True,
    "additional_breadcrumbs": [
        ("PyAnsys", "https://docs.pyansys.com/"),
    ],
    "icon_links": [
        {
            "name": "Support",
            "url": "https://github.com/ansys/pyansys-geometry-mcp/discussions",
            "icon": "fa fa-comment fa-fw",
        },
        {
            "name": "Download documentation in PDF",
            "url": f"https://{cname}/version/{switcher_version}/_static/assets/download/pyansys-geometry-mcp.pdf",  # noqa: E501
            "icon": "fa fa-file-pdf fa-fw",
        },
    ],
    "static_search": {
        "threshold": 0.5,
        "minMatchCharLength": 2,
        "ignoreLocation": True,
    },
}

linkcheck_ignore = [
    "https://github.com/ansys/pyansys-geometry-mcp/*",
]

if switcher_version != "dev":
    linkcheck_ignore.append(
        f"https://github.com/ansys/pyansys-geometry-mcp/releases/tag/v{__version__}"
    )

# Sphinx extensions
extensions = [
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_click",
    "sphinx_jinja",
]

# numpydoc configuration
numpydoc_show_class_members = False
numpydoc_xref_param_type = True

numpydoc_validate = True
numpydoc_validation_checks = {
    "GL06",  # Found unknown section
    "GL07",  # Sections are in the wrong order.
    "GL09",  # Deprecation warning should precede extended summary
    "GL10",  # reST directives {directives} must be followed by two colons
    "SS01",  # No summary found
    "SS02",  # Summary does not start with a capital letter
    "SS04",  # Summary contains heading whitespaces
    "RT02",  # The first line of the Returns section should contain only the type
}

html_favicon = ansys_favicon
templates_path = ["_templates"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

typehints_defaults = "comma"
latex_additional_files = [watermark, ansys_logo_white, ansys_logo_white_cropped]
suppress_warnings = ["ref.python"]

exclude_patterns = ["changelog/*.md"]
