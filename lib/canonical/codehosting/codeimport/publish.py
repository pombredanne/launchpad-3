# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Publish a vcs import branch from the importd slave.

This module is the back-end for scripts/importd-publish.py.
"""

__metaclass__ = type

__all__ = ['ImportdPublisher']


import os

from zope.component import getUtility

from bzrlib.transport import get_transport
from bzrlib.workingtree import WorkingTree

from canonical.codehosting.codeimport.worker import BazaarBranchStore
from canonical.database.sqlbase import begin, commit
from canonical.launchpad.interfaces import (
    BranchType, ILaunchpadCelebrities, IBranchSet, IProductSeriesSet)


class ImportdPublisher:
    """Publish a vcs import branch."""

    def __init__(self, log, workingdir, series_id, push_prefix):
        self.logger = log
        self.workingdir = workingdir
        self.series_id = series_id
        self.push_prefix = push_prefix
        self._store = BazaarBranchStore(get_transport(self.push_prefix))

    def publish(self):
        begin()
        series = getUtility(IProductSeriesSet)[self.series_id]
        ensure_series_branch(series)
        branch = series.import_branch
        commit()
        local = os.path.join(self.workingdir, 'bzrworking')
        self._store.push(branch.id, WorkingTree.open(local))


def ensure_series_branch(series):
    """Ensure a ProductSeries has as associated vcs-imports branch.

    :param series: ProductSeries database object specifying a VCS import.
    """
    if series.import_branch is None:
        series.import_branch = create_branch_for_series(series)


def create_branch_for_series(series):
    """Create the Branch registration for the VCS import.

    :param series: ProductSeries database object specifying a VCS import.
    :return: Branch database object used to publish that VCS import.
    """
    name = series.name
    vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
    product = series.product
    branch = getUtility(IBranchSet).new(
        BranchType.IMPORTED, name, vcs_imports, vcs_imports, product,
        url=None)
    return branch
