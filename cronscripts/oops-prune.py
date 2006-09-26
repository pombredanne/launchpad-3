#!/usr/bin/env python
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Cronscript to prune old and unreferenced OOPS reports from the archive."""

__metaclass__ = type

import _pythonpath
import sys

from canonical.launchpad.scripts.oops import referenced_oops
from canonical.lp import initZopeless, AUTOCOMMIT_ISOLATION

def main():
    ztm = initZopeless(isolation=AUTOCOMMIT_ISOLATION)
    referenced_oops_codes = referenced_oops()
    for code in referenced_oops_codes:
        print code


if __name__ == '__main__':
    sys.exit(main())
