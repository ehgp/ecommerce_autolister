"""Configuration file for the Sphinx documentation builder."""
# # This file only contains a selection of the most common options.
# For a full # list see the documentation: # https://www.sphinx-doc.org/en/master/usage/configuration.html
# # -- Path setup -------------------------------------------------------------- #
# If extensions (or modules to document with autodoc) are in another directory, # add these directories
# to sys.path here. If the directory is relative to the # documentation root, use os.path.abspath
# to make it absolute, like shown here.
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.abspath("../.."))
# # -- Project information -----------------------------------------------------
project = "eCommerce Autolister"
author = "ehgp"
copyright = "%s ehgp. All rights reserved." % (dt.date.today().year)
# The full version, including alpha/beta/rc tags
release = "0.1.0"
# -- General configuration ---------------------------------------------------
# Add any Sphinx extension module names here, as strings.
# They can be # extensions coming with Sphinx (named 'sphinx.ext.*') or your custom # ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.coverage",
    "recommonmark",
]
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_param = False
napoleon_use_ivar = True
html_show_sourcelink = False
# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]
# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []
# The master toctree document.
master_doc = "index"
# -- Options for HTML output -------------------------------------------------
# The theme to use for HTML and HTML Help pages. See the documentation for # a list of builtin themes.
html_theme = "sphinx_rtd_theme"
# HTML Theme Options
html_theme_options = {
    "display_version": True,
    "collapse_navigation": False,
    # "logo_only": True,
}
# Image for the top of the sidebar & favicon
# html_logo = "_static/logo.jpg"
# html_favicon = "_static/logo.jpg"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
