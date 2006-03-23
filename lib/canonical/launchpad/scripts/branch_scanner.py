#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.
# Author: Gustavo Niemeyer <gustavo@niemeyer.net>
#         David Allouche <david@allouche.net>

"""Internal helpers for cronscripts/branches-scanner.py"""

__metaclass__ = type

__all__ = ['BranchScanner']


from bzrlib.errors import NotBranchError, ConnectionError

from zope.component import getUtility

from canonical.launchpad.interfaces import IBranchSet
from importd.bzrsync import BzrSync


class BranchScanner:
    """Runner for BzrSync.

    Implement the application logic of cronscripts/branch-scanner.py.
    """

    def __init__(self, ztm, log, config):
        self.ztm = ztm
        self.log = log
        self.config = config

    def scanAllBranches(self):
        """Run Bzrsync on all branches, and intercept most exceptions."""
        self.log.debug('Starting branches update')
        for branch in getUtility(IBranchSet):
            try:
                self.scanOneBranch(branch)
            except (KeyboardInterrupt, SystemExit):
                # If either was raised, something really wants us to finish.
                # Any other Exception is an error condition and must not
                # terminate the script.
                raise
            except:
                # Yes, bare except. Bugs or error conditions when scanning any
                # given branch must not prevent scanning the other branches.
                self.logScanFailure(branch)
                self.log.exception('Unhandled exception')
        self.log.debug('Finished branches update')


    def scanOneBranch(self, branch):
        """Run BzrSync on a single branch and handle expected exceptions."""
        try:
            bzrsync = BzrSync(
                self.ztm, branch.id, self.branchWarehouseUrl(branch), self.log)
        except NotBranchError:
            # The branch is not present in the Warehouse
            self.logScanFailure(branch, "Branch not found")
            return
        try:
            bzrsync.syncHistory()
        except ConnectionError:
            # A network glitch occured. Yes, that does happen.
            self.log.shortException("Transient network failure")
            self.logScanFailure(branch)

    def logScanFailure(self, branch, message="Failed to scan"):
        """Log diagnostic for branches that could not be scanned."""
        self.log.warning("%s: %s\n    branch.url = %r",
                         message, self.branchWarehouseUrl(branch), branch.url)

    def branchWarehouseUrl(self, branch):
        """Return the id-based URL of a branch in the Warehouse."""
        return "%s%08x" % (self.config.root_url, branch.id)
