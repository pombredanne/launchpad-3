#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# arch-tag: f33e66e2-1561-43fa-bb12-ee8c5248c801
"""Logging.

This module contains utility functions for creating trees of logging
instances for objects.
"""

__copyright__ = "Copyright © 2004 Canonical Software."
__author__    = "Scott James Remnant <scott@canonical.com>"


import logging


def get_logger(name, parent=None):
    """Create a logging instance underneath the given parent."""
    if parent is None or parent == parent.root:
        l = logging.getLogger(name)
    else:
        l = logging.getLogger("%s.%s" % (parent.name, name))

    return l
