#!/usr/bin/env python3
# type: ignore
# flake8: noqa

"""Sphinx documentation generation."""


import os
import sys
import typing

sys.path.insert(0, os.path.abspath(".."))

exec(open("../telegram_menu/_version.py").read())


# -- Project information -----------------------------------------------------

project = __title__
copyright = __copyright__
author = __author__

# The full version, including alpha/beta/rc tags
release = __version__

# overwrite TYPE_CHECKING to load static type hints
typing.TYPE_CHECKING = True

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinx.ext.viewcode",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
