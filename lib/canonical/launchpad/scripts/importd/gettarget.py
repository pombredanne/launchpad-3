# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Retrieve a vcs-import branch from the internal publication server, and save
it as bzrworking in the working directory.

This module is the back-end for scripts/importd-get-target.py.
"""

__metaclass__ = type

__all__ = ['ImportdTargetGetter']


import os
import shutil

from bzrlib.bzrdir import BzrDir
from zope.component import getUtility

from canonical.launchpad.interfaces import IProductSeriesSet
from canonical.launchpad.scripts.importd.publish import mirror_url_from_series


class ImportdTargetGetter:
    """Retrieve a working copy of a published vcs import branch."""

    def __init__(self, log, workingdir, series_id, push_prefix):
        self.logger = log
        self.workingdir = workingdir
        self.series_id = series_id
        self.push_prefix = push_prefix

    def get_target(self):
        series = getUtility(IProductSeriesSet)[self.series_id]
        from_location = mirror_url_from_series(self.push_prefix, series)
        from_control = BzrDir.open(from_location)
        to_location = os.path.join(self.workingdir, 'bzrworking')
        if os.path.isdir(to_location):
            shutil.rmtree(to_location)
        from_control.sprout(to_location)
