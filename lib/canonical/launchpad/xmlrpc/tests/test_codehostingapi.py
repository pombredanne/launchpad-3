# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Unit tests for the public codehosting API."""

__metaclass__ = type
__all__ = []


import unittest

from canonical.codehosting.tests.helpers import BranchTestCase
from canonical.launchpad.ftests import login, logout, ANONYMOUS
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.xmlrpc.branch import PublicCodehostingAPI


class TestExpandURL(BranchTestCase):
    """Test the way that URLs are expanded."""

    def setUp(self):
        BranchTestCase.setUp(self)
        self.relaxSecurityPolicy()
        login(ANONYMOUS)
        self.addCleanup(logout)
        self.api = PublicCodehostingAPI(None, None)
        # BranchType is only signficiant insofar as it is non-IMPORTED.
        self.trunk = self.makeBranch(BranchType.HOSTED)
        self.project = self.trunk.product
        self.owner = self.trunk.owner
        self.project.development_focus.user_branch = self.trunk

    def test_projectOnly(self):
        """lp:project expands to the branch associated with development focus
        of the project.
        """
        self.assertEqual(
            ('bazaar.launchpad.dev', self.trunk.unique_name,
             ('bzr+ssh', 'sftp', 'http')),
            self.api.expand_lp_url('lp:%s' % self.project.name))
        self.assertEqual(
            ('bazaar.launchpad.dev', self.trunk.unique_name,
             ('bzr+ssh', 'sftp', 'http')),
            self.api.expand_lp_url('lp:///%s' % self.project.name))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
