# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Retrieve a vcs-import branch from the internal publication server, and save
it as bzrworking in the working directory.

This module is the back-end for scripts/importd-get-target.py.
"""

__metaclass__ = type

__all__ = ['ImportdTargetGetter']


import os
import shutil

from bzrlib.errors import UpToDateFormat
from bzrlib.transport import get_transport
from bzrlib.upgrade import upgrade
from zope.component import getUtility

from canonical.codehosting.codeimport.worker import BazaarBranchStore
from canonical.launchpad.interfaces import IProductSeriesSet


class ImportdTargetGetter:
    """Retrieve a working copy of a published vcs import branch."""

    def __init__(self, log, workingdir, series_id, push_prefix):
        self.logger = log
        self.workingdir = workingdir
        self.series_id = series_id
        self.push_prefix = push_prefix
        self._store = BazaarBranchStore(get_transport(self.push_prefix))

    def get_target(self):
        branch = getUtility(IProductSeriesSet)[self.series_id].import_branch
        from_location = self._store._getMirrorURL(branch.id)
        self.upgrade_location(from_location)
        to_location = os.path.join(self.workingdir, 'bzrworking')
        if os.path.isdir(to_location):
            shutil.rmtree(to_location)
        self._store.pull(branch.id, to_location)

    def upgrade_location(self, location):
        """Upgrade the branch at this location to the current default format.

        Do nothing if the branch does not need upgrading.
        """
        try:
            upgrade(location)
        except UpToDateFormat:
            pass
