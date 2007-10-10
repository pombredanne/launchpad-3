# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Unit tests for the public codehosting API."""

__metaclass__ = type
__all__ = []


import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.codehosting.tests.helpers import BranchTestCase
from canonical.launchpad.ftests import login, logout, ANONYMOUS
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.webapp.uri import URI
from canonical.launchpad.xmlrpc.branch import PublicCodehostingAPI
from canonical.launchpad.xmlrpc import faults


class TestExpandURL(BranchTestCase):
    """Test the way that URLs are expanded."""

    def setUp(self):
        BranchTestCase.setUp(self)
        login(ANONYMOUS)
        self.addCleanup(logout)
        self.api = PublicCodehostingAPI(None, None)
        # BranchType is only signficiant insofar as it is non-IMPORTED.
        self.trunk = self.makeBranch(BranchType.HOSTED)
        self.project = self.trunk.product
        self.owner = self.trunk.owner
        series = removeSecurityProxy(self.project).development_focus
        series.user_branch = self.trunk

    def assertExpands(self, lp_url_path, branch):
        """Assert that the given lp URL path expands to the unique name of
        'branch'.
        """
        results = self.api.resolve_lp_path(lp_url_path)
        self.assertEqual(
            branch.unique_name, results['path'],
            "Expected %r to expand to %r, got %r"
            % (lp_url_path, branch.unique_name, results['path']))

    def assertFault(self, lp_url_path, expected_fault):
        """Assert that trying to resolve lp_url_path returns the expected
        fault.
        """
        fault = self.api.resolve_lp_path(lp_url_path)
        self.assertEqual(expected_fault.__class__, fault.__class__)
        self.assertEqual(expected_fault.faultString, fault.faultString)

    def test_hostnameAndSchemes(self):
        """resolve_lp_path returns a dict that contains the hostname, a list
        of supported schemes and the unique name of the requested branch.
        """
        results = self.api.resolve_lp_path(self.project.name)
        self.assertEqual(
            dict(host='bazaar.launchpad.dev',
                 path=self.trunk.unique_name,
                 supported_schemes=('bzr+ssh', 'sftp', 'http')),
            results)

    def test_projectOnly(self):
        """lp:project expands to the branch associated with development focus
        of the project.
        """
        self.assertExpands(self.project.name, self.trunk)

    def test_projectDoesntExist(self):
        """Return a NoSuchProduct fault if the product doesn't exist."""
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
        """Return a NoBranchForSeries fault if the series has no branch
        associated with it.
        """
        project = self.makeProduct()
        self.assertFault(
            project.name, faults.NoBranchForSeries(project.development_focus))
        self.assertFault(
            '%s/%s' % (project.name, project.development_focus.name),
            faults.NoBranchForSeries(project.development_focus))

    def test_noSuchSeries(self):
        """Return a NoSuchSeries fault there is no series of the given name
        associated with the project.
        """
        self.assertFault(
            '%s/%s' % (self.project.name, "doesntexist"),
            faults.NoSuchSeries("doesntexist", self.project))

    def test_branch(self):
        """The unique name of a branch resolves to the unique name of the
        branch.
        """
        self.assertExpands(self.trunk.unique_name, self.trunk)

    def test_noSuchBranch(self):
        """Return a NoSuchBranch fault if there is no such... branch."""
        self.assertFault('~foo/bar/baz', faults.NoSuchBranch('~foo/bar/baz'))

    def test_tooManySegments(self):
        """A path with more than three segments is invalid."""
        self.assertFault(
            'foo/bar/baz/qux',
            faults.InvalidBranchIdentifier('foo/bar/baz/qux'))

    def test_emptyPath(self):
        """An empty path is an invalid identifier."""
        self.assertFault('', faults.InvalidBranchIdentifier(''))

    def test_missingTilde(self):
        """If it looks like a branch's unique name, but is missing a tilde,
        then it is an invalid branch identifier.
        """
        self.assertFault(
            'foo/bar/baz', faults.InvalidBranchIdentifier('foo/bar/baz'))
        unique_name = self.trunk.unique_name.lstrip('~')
        self.assertFault(
            unique_name, faults.InvalidBranchIdentifier(unique_name))

    def test_allSlashes(self):
        """A path of all slashes is an invalid identifier."""
        self.assertFault('///', faults.InvalidBranchIdentifier('///'))

    def test_trailingSlashes(self):
        """Trailing slashes are trimmed."""
        self.assertExpands(self.project.name + '/', self.trunk)
        self.assertExpands(self.project.name + '//', self.trunk)
        self.assertExpands(self.trunk.unique_name + '/', self.trunk)
        self.assertExpands(self.trunk.unique_name + '//', self.trunk)

    def test_privateBranch(self):
        """If a branch is not visible then it looks like it doesn't exist."""
        naked_trunk = removeSecurityProxy(self.trunk)
        naked_trunk.private = True
        self.assertFault(
            naked_trunk.unique_name,
            faults.NoSuchBranch(naked_trunk.unique_name))
        self.assertFault(
            self.project.name,
            faults.NoBranchForSeries(self.project.development_focus))

    def test_remoteBranch(self):
        """For remote branches, return results that link to the actual remote
        branch URL.
        """
        branch = self.makeBranch(BranchType.REMOTE)
        url = URI(branch.url)
        result = self.api.resolve_lp_path(branch.unique_name)
        self.assertEqual(url.host, result['host'])
        self.assertEqual(url.path, result['path'])
        self.assertEqual([url.scheme], result['supported_schemes'])

    def test_remoteBranchWithPort(self):
        """For remote branches, return results that link to the actual remote
        branch URL, including the port number if provided.
        """
        branch = self.makeBranch(BranchType.REMOTE)
        # Set the port so we can confirm port is included set.
        url = URI(branch.url)
        url.port = 8080
        removeSecurityProxy(branch).url = str(url)

        result = self.api.resolve_lp_path(branch.unique_name)
        self.assertEqual(url.authority, result['host'])
        self.assertEqual(url.path, result['path'])
        self.assertEqual([url.scheme], result['supported_schemes'])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
