#!/usr/bin/env python
# Copyright (c) 2006 Canonical Ltd.
# Author: David Allouche <david@allouche.net>

"""Script for Importd that converts baz branches to bzr and publish them.

Usage: baz2bzr.py arch_version bzr_branch blacklist_file
"""

import sys
import os

from bzrlib.plugins.bzrtools import baz_import
from bzrlib.progress import DummyProgress
import pybaz

from canonical.lp import initZopeless
from canonical.database.sqlbase import begin, rollback
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.database import ProductSeries


def stdout_printer(msg):
    print msg

def silent_printer(msg):
    pass


class BatchProgress(DummyProgress):
    """Progress-bar that gives simple line-by-line progress."""

    def update(self, msg, current, total):
        print '%d/%d %s' % (current, total, msg)



def main(quiet, series_id, blacklist_path):
    to_location = 'bzrworking'
    begin()
    series = ProductSeries.get(series_id)
    from_branch = archFromSeries(series)
    rollback()

    if isInBlacklist(from_branch, blacklist_path):
        print 'blacklisted:', from_branch
        print "Not exporting to bzr"
        return 0
    from_branch = pybaz.Version(from_branch)
    if quiet:
        progress_bar = DummyProgress()
        printer = silent_printer
    else:
        progress_bar = BatchProgress()
        printer = stdout_printer
    baz_import.import_version(
        to_location, from_branch, printer, 
        max_count=None, reuse_history_from=[],
        progress_bar=progress_bar)
    return 0


def archFromSeries(series):
    archive = pybaz.Archive(series.targetarcharchive)
    category = archive[series.targetarchcategory]
    branch = category[series.targetarchbranch]
    version = branch[series.targetarchversion]
    return version.fullname


def isInBlacklist(from_branch, blacklist_path):
    blacklist = open(blacklist_path)
    return from_branch in parseBlacklist(blacklist)


def parseBlacklist(blacklist):
    for line in blacklist:
        line = line.strip()
        if line:
            yield line


def initialize_zopeless():
    initZopeless()
    execute_zcml_for_scripts()


if __name__ == '__main__':
    args = sys.argv[1:]
    if args[0] == '-q':
        quiet = True
        del args[0]
    else:
        quiet = False
    initialize_zopeless()
    status = main(quiet, *args)
    sys.exit(status)
