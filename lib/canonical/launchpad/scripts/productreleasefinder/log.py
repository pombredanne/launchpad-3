# -*- coding: utf-8 -*-
"""Logging.

This module contains a utility function for creating trees of logging
instances for objects.
"""

__copyright__ = "Copyright © 2004 Canonical Ltd."
__author__    = "Scott James Remnant <scott@canonical.com>"


import logging


def get_logger(name, parent=None):
    """Create a logging instance underneath the given parent."""
    if parent is None or parent == parent.root:
        l = logging.getLogger(name)
    else:
        l = logging.getLogger("%s.%s" % (parent.name, name))

    return l
