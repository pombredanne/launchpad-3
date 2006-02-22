#!/usr/bin/env python
# Copyright (c) 2005 Canonical Ltd.
# Author: David Allouche <david@allouche.net>

"""Script for Importd that converts baz branches to bzr and publish them.

Usage: baz2bzr.py arch_version bzr_branch blacklist_file
"""

import sys
import os

from bzrlib.plugins.bzrtools import baz_import
import pybaz


def printer(name):
    print name

def main(from_branch, to_location, blacklist_path):
    unused = blacklist_path
    to_location = os.path.realpath(str(to_location))
    from_branch = pybaz.Version(from_branch)
    baz_import.import_version(
        to_location, from_branch, printer, 
        max_count=None, reuse_history_from=[])


if __name__ == '__main__':
    status = main(*sys.argv[1:])
    sys.exit(status)
