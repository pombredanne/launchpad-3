#!/usr/bin/python2.4
# Copyright 2005 Canonical Ltd.  All rights reserved.
# Author: Gustavo Niemeyer <gustavo@niemeyer.net>
#         David Allouche <david@allouche.net>

"""Internal helpers for cronscripts/branches-scanner.py"""

__metaclass__ = type

__all__ = ['BranchScanner']


import sys
from xmlrpclib import ServerProxy

from bzrlib.errors import NotBranchError, ConnectionError
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import IBranchSet
from canonical.codehosting.scanner.bzrsync import BzrSync
from canonical.codehosting.transport import (
    BlockingProxy, get_chrooted_transport, LaunchpadInternalServer)
from canonical.launchpad.webapp import canonical_url, errorlog


class BranchScanner:
    """Scan bzr branches for meta data and insert them into content objects.

    This class is used by cronscripts/branch-scanner.py to perform its task.
    """

    def __init__(self, ztm, log):
        self.ztm = ztm
        self.log = log

    def _getLaunchpadServer(self):
        """Get a Launchpad internal transport for scanning branches."""
        authserver = BlockingProxy(ServerProxy(config.codehosting.authserver))
        branch_transport = get_chrooted_transport(
            config.supermirror.warehouse_root_url)
        return LaunchpadInternalServer(
            'lp-internal:///', authserver, branch_transport)

    def scanAllBranches(self):
        """Run Bzrsync on all branches, and intercept most exceptions."""
        self.log.info('Starting branch scanning')
        server = self._getLaunchpadServer()
        server.setUp()
        try:
            for branch in getUtility(IBranchSet).getBranchesToScan():
                try:
                    self.scanOneBranch(branch)
                except (KeyboardInterrupt, SystemExit):
                    # If either was raised, something really wants us to
                    # finish. Any other Exception is an error condition and
                    # must not terminate the script.
                    raise
                except:
                    # Yes, bare except. Bugs or error conditions when scanning
                    # any given branch must not prevent scanning the other
                    # branches.
                    self.logScanFailure(branch)
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
        except ConnectionError:
            # A network glitch occured. Yes, that does happen.
            self.logScanFailure(branch, "Internal network failure")

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
        self.log.info('%s: %s', request.oopsid, message)
