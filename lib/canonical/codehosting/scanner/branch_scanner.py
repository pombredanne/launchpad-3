#!/usr/bin/python2.4
# Copyright 2005-2008 Canonical Ltd.  All rights reserved.

"""Internal helpers for cronscripts/branches-scanner.py"""

__metaclass__ = type

__all__ = ['BranchScanner']


import sys

from bzrlib.errors import NotBranchError, ConnectionError
# This non-standard import is necessary to hook up the event system.
import zope.component.event
from zope.component import getGlobalSiteManager, getUtility, provideHandler

from lp.code.interfaces.branchscanner import IBranchScanner
from canonical.codehosting.vfs import get_scanner_server
from canonical.codehosting.scanner import buglinks, email
from canonical.codehosting.scanner.bzrsync import BzrSync
from canonical.codehosting.scanner.fixture import (
    Fixtures, FixtureWithCleanup, run_with_fixture)
from canonical.launchpad.webapp import canonical_url, errorlog


class ZopeEventFixture(FixtureWithCleanup):

    def __init__(self, handler):
        self._handler = handler

    def setUp(self):
        super(ZopeEventFixture, self).setUp()
        gsm = getGlobalSiteManager()
        provideHandler(self._handler)
        self.addCleanup(gsm.unregisterHandler, self._handler)


def make_zope_event_fixture(*handlers):
    return Fixtures(map(ZopeEventFixture, handlers))


class BranchScanner:
    """Scan bzr branches for meta data and insert them into content objects.

    This class is used by cronscripts/branch-scanner.py to perform its task.
    """

    def __init__(self, ztm, log):
        self.ztm = ztm
        self.log = log

    def scanBranches(self, branches):
        """Scan 'branches'."""
        for branch in branches:
            try:
                self.scanOneBranch(branch)
            except (KeyboardInterrupt, SystemExit):
                # If either was raised, something really wants us to finish.
                # Any other Exception is an error condition and must not
                # terminate the script.
                raise
            except Exception, e:
                # Yes, bare except. Bugs or error conditions when scanning any
                # given branch must not prevent scanning the other branches.
                self.logScanFailure(branch, str(e))

    def scanAllBranches(self):
        """Run Bzrsync on all branches, and intercept most exceptions."""
        self.log.info('Starting branch scanning')
        server = get_scanner_server()
        fixture = Fixtures(
            [server, make_zope_event_fixture(
                email.create_revision_added_job, buglinks.got_new_revision)])
        branches = getUtility(IBranchScanner).getBranchesToScan()
        run_with_fixture(fixture, self.scanBranches, branches)
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
