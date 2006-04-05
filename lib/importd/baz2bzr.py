#!/usr/bin/env python
# Copyright 2006 Canonical Ltd.  All rights reserved.
# Author: David Allouche <david@allouche.net>

"""Script for Importd that converts baz branches to bzr and publishes them.

Usage: baz2bzr.py arch_version bzr_branch blacklist_file
"""

__metaclass__ = type

import sys

from bzrlib.bzrdir import BzrDir
from bzrlib.plugins.bzrtools import baz_import
from bzrlib.progress import DummyProgress
import pybaz

from zope.component import getUtility
from canonical.lp import initZopeless
from canonical.database.sqlbase import begin, rollback, commit
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.database import ProductSeries
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IBranchSet)


def stdout_printer(msg):
    print msg


def silent_printer(msg):
    pass


class BatchProgress(DummyProgress):
    """Progress-bar that gives simple line-by-line progress."""

    def update(self, msg, current=None, total=None):
        if current is None and total is None:
            print msg
        elif total is None:
            assert current is not None
            print '%d %s' % (current, msg)
        else:
            assert current is not None
            print '%d/%d %s' % (current, total, msg)


def make_progress_bar(quiet):
    if quiet:
        return DummyProgress()
    else:
        return BatchProgress()


def make_printer(quiet):
    if quiet:
        return silent_printer
    else:
        return stdout_printer


def parse_arguments(args):
    if args[0] == '-q':
        quiet = True
        del args[0]
    else:
        quiet = False
    series_id = args.pop(0)
    blacklist_path = args.pop(0)
    if args:
        push_prefix = args.pop(0)
    else:
        push_prefix = None
    assert not args, 'extraneous arguments: %r' % (args,)
    return quiet, series_id, blacklist_path, push_prefix


def main(args):
    quiet, series_id, blacklist_path, push_prefix = parse_arguments(args)
    to_location = 'bzrworking'
    begin()
    series = ProductSeries.get(series_id)
    from_branch = arch_from_series(series)
    rollback()

    if is_in_blacklist(from_branch, blacklist_path):
        print 'blacklisted:', from_branch
        print "Not exporting to bzr"
        return 0
    from_branch = pybaz.Version(from_branch)
    progress_bar = make_progress_bar(quiet)
    printer = make_printer(quiet)
    baz_import.import_version(
        to_location, from_branch, printer, 
        max_count=None, reuse_history_from=[],
        progress_bar=progress_bar)
    if push_prefix is None:
        return 0
    begin()
    branch = branch_from_series(series)
    commit()
    push_to = push_prefix + ('%08x' % branch.id)
    bzr_push(to_location, push_to, quiet)
    return 0

def bzr_push(from_location, to_location, quiet):
    # Duplicate code from bzrlib so we can use our custom ProgressBar.
    from bzrlib.transport import get_transport
    from bzrlib.branch import Branch
    from bzrlib.errors import NotBranchError

    br_from = Branch.open(from_location)
    
    try:
        br_to = Branch.open(to_location)
    except NotBranchError:
        # create a branch.
        transport = get_transport(to_location).clone('..')
        transport.mkdir(transport.relpath(to_location))
        # Do not create a working tree
        br_to = BzrDir.create_branch_and_repo(to_location)
    old_rh = br_to.revision_history()
    br_from.lock_read()
    try:
        stop_revision = br_from.last_revision()
        if stop_revision in br_to.revision_history():
            return
        pb = make_progress_bar(quiet)
        br_to.fetch(br_from, stop_revision, pb)
        pullable_revs = br_to.pullable_revisions(br_from, stop_revision)
        if len(pullable_revs) > 0:
            br_to.append_revision(*pullable_revs)
    finally:
        br_from.unlock()


def arch_from_series(series):
    if series.targetarcharchive is None:
        assert series.targetarchcategory is None
        assert series.targetarchbranch is None
        assert series.targetarchversion is None
        return 'unnamed@bazaar.ubuntu.com/series--%d' % series.id
    else:
        archive = pybaz.Archive(series.targetarcharchive)
        category = archive[series.targetarchcategory]
        branch = category[series.targetarchbranch]
        version = branch[series.targetarchversion]
        return version.fullname


def branch_from_series(series):
    if series.branch is None:
        series.branch = create_branch_for_series(series)
    return series.branch


def create_branch_for_series(series):
    name = series.name
    vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
    product = series.product
    branch = getUtility(IBranchSet).new(name, vcs_imports, product, url=None)
    return branch
        

def is_in_blacklist(from_branch, blacklist_path):
    blacklist = open(blacklist_path)
    return from_branch in parse_blacklist(blacklist)


def parse_blacklist(blacklist):
    for line in blacklist:
        line = line.strip()
        if line:
            yield line


def initialize_zopeless():
    initZopeless()
    execute_zcml_for_scripts()


if __name__ == '__main__':
    args = sys.argv[1:]
    initialize_zopeless()
    status = main(args)
    sys.exit(status)
