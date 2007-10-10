# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Unit tests for the public codehosting API."""

__metaclass__ = type
__all__ = []


import unittest

from canonical.codehosting.tests.helpers import BranchTestCase
from canonical.launchpad.ftests import login, logout, ANONYMOUS
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.xmlrpc.branch import PublicCodehostingAPI
from canonical.launchpad.xmlrpc import faults


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

    def assertExpands(self, lp_url_path, branch):
        """Assert that the given lp URL path expands to the unique name of
        'branch'.
        """
        for prefix in 'lp:', 'lp:///':
            url = '%s%s' % (prefix, lp_url_path)
            results = self.api.expand_lp_url(url)
            self.assertEqual(
                branch.unique_name, results['path'],
                "Expected %r to expand to %r, got %r"
                % (url, branch.unique_name, results['path']))

    def assertFault(self, lp_url_path, expected_fault):
        for prefix in 'lp:', 'lp:///':
            url = '%s%s' % (prefix, lp_url_path)
            fault = self.api.expand_lp_url(url)
            self.assertEqual(expected_fault.__class__, fault.__class__)
            self.assertEqual(expected_fault.faultString, fault.faultString)

#     def test_hostname(self):
#         pass

#     def test_supportedProtocols(self):
#         pass

    def test_projectOnly(self):
        """lp:project expands to the branch associated with development focus
        of the project.
        """
        self.assertExpands(self.project.name, self.trunk)

    def test_projectDoesntExist(self):
        self.assertFault(
            'doesntexist', faults.NoSuchProduct('doesntexist'))
        self.assertFault(
            'doesntexist/trunk', faults.NoSuchProduct('doesntexist'))

    def test_projectAndSeries(self):
        """lp:project/series expands to the branch associated with the product
        series 'series' on 'project'.
        """
        self.assertExpands(
            '%s/%s' % (self.project.name,
                       self.project.development_focus.name),
            self.trunk)

    def test_seriesHasNoBranch(self):
        project = self.makeProduct()
        self.assertFault(
            project.name, faults.NoBranchForSeries(project.development_focus))
        self.assertFault(
            '%s/%s' % (project.name, project.development_focus.name),
            faults.NoBranchForSeries(project.development_focus))

    def test_noSuchSeries(self):
        self.assertFault(
            '%s/%s' % (self.project.name, "doesntexist"),
            faults.NoSuchSeries("doesntexist", self.project))

    def test_branch(self):
        self.assertExpands(self.trunk.unique_name, self.trunk)

    def test_noSuchBranch(self):
        self.assertFault('~foo/bar/baz', faults.NoSuchBranch('~foo/bar/baz'))

    # TODO:
    # - more than three path segments
    # - empty URL
    # - three part URL not starting with tilde
    # - URL consisting entirely of slashes
    # - Trailing slashes

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
