#!/usr/bin/python2.4
# Copyright 2005-2008 Canonical Ltd.  All rights reserved.

"""Internal helpers for cronscripts/branches-scanner.py"""

__metaclass__ = type

__all__ = ['BranchScanner']


import sys

from bzrlib.errors import NotBranchError, ConnectionError
from zope.component import getUtility

from canonical.launchpad.interfaces.branchscanner import IBranchScanner
from canonical.codehosting.vfs import get_scanner_server
from canonical.codehosting.scanner.bzrsync import BzrSync
from canonical.launchpad.webapp import canonical_url, errorlog


class BranchScanner:
    """Scan bzr branches for meta data and insert them into content objects.

    This class is used by cronscripts/branch-scanner.py to perform its task.
    """

    def __init__(self, ztm, log):
        self.ztm = ztm
        self.log = log

    def scanAllBranches(self):
        """Run Bzrsync on all branches, and intercept most exceptions."""
        self.log.info('Starting branch scanning')
        server = get_scanner_server()
        server.setUp()
        try:
            for branch in getUtility(IBranchScanner).getBranchesToScan():
                try:
                    self.scanOneBranch(branch)
                except (KeyboardInterrupt, SystemExit):
                    # If either was raised, something really wants us to
                    # finish. Any other Exception is an error condition and
                    # must not terminate the script.
                    raise
                except Exception, e:
                    # Yes, bare except. Bugs or error conditions when scanning
                    # any given branch must not prevent scanning the other
                    # branches.
                    self.logScanFailure(branch, str(e))
        finally:
            server.tearDown()
        self.log.info('Finished branch scanning')

    def scanOneBranch(self, branch):
        """Run BzrSync on a single branch and handle expected exceptions."""
        try:
            bzrsync = BzrSync(self.ztm, branch, self.log)
        except NotBranchError:
            # The branch is not present in the Warehouse
            self.logScanFailure(branch, "No branch found")
            return
        try:
            bzrsync.syncBranchAndClose()
        except ConnectionError, e:
            # A network glitch occured. Yes, that does happen.
            self.logScanFailure(branch, "Internal network failure: %s" % e)

    def logScanFailure(self, branch, message="Failed to scan"):
        """Log diagnostic for branches that could not be scanned."""
        request = errorlog.ScriptRequest([
            ('branch.id', branch.id),
            ('branch.unique_name', branch.unique_name),
            ('branch.url', branch.url),
            ('branch.warehouse_url', branch.warehouse_url),
            ('error-explanation', message)])
        request.URL = canonical_url(branch)
        errorlog.globalErrorUtility.raising(sys.exc_info(), request)
        self.log.info('%s: %s (%s)',
            request.oopsid, message, branch.unique_name)
