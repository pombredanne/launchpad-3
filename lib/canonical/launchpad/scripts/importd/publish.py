# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Publish a vcs import branch from the importd slave.

This module is the back-end for script/importd-publish.py.
"""

__metaclass__ = type


import os

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.errors import NotBranchError
from bzrlib.transport import get_transport
from zope.component import getUtility

from canonical.database.sqlbase import begin, commit
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IBranchSet, IProductSeriesSet)
from canonical.launchpad.webapp.url import urlappend


class ImportdPublisher:
    """Publish a vcs improt branch."""

    def __init__(self, log, workingdir, series_id, push_prefix):
        self.logger = log
        self.workingdir = workingdir
        self.series_id = series_id
        self.push_prefix = push_prefix

    def publish(self):
        begin()
        series = getUtility(IProductSeriesSet)[self.series_id]
        branch = branch_from_series(series)
        commit()
        push_to = urlappend(self.push_prefix, '%08x' % branch.id)
        local = os.path.join(self.workingdir, 'bzrworking')
        bzr_push(local, push_to)


def branch_from_series(series):
    """Retrieve or create the Branch registration for the VCS import.

    :param series: ProductSeries database object specifying a VCS import.
    :return: Branch database object used to publish that VCS import.
    """
    if series.branch is None:
        series.branch = create_branch_for_series(series)
    return series.branch


def create_branch_for_series(series):
    """Create the Branch registration for the VCS import.

    :param series: ProductSeries database object specifying a VCS import.
    :return: Branch database object used to publish that VCS import.
    """
    name = series.name
    vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
    product = series.product
    branch = getUtility(IBranchSet).new(name, vcs_imports, product, url=None)
    return branch


def bzr_push(from_location, to_location):
    """Simple implementation of 'bzr push' that does not depend on the cwd."""
    branch_from = Branch.open(from_location)
    try:
        branch_to = Branch.open(to_location)
    except NotBranchError:
        # create a branch.
        transport = get_transport(to_location).clone('..')
        transport.mkdir(transport.relpath(to_location))
        # Do not create a working tree
        branch_to = BzrDir.create_branch_and_repo(to_location)
    branch_to.pull(branch_from)
