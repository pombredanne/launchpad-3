#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# arch-tag: 93e0818c-f857-4f4e-a093-4986e6164439
"""Debian packaging.

This package provides a reasonable subset of the functionality of
dpkg-dev without being written in Perl.
"""

__copyright__ = "Copyright © 2004 Canonical Software."
__author__    = "Scott James Remnant <scott@canonical.com>"


import controlfile
import source
import version
