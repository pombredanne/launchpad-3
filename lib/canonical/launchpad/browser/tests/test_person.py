# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test harness for person views unit tests."""

__metaclass__ = type


from textwrap import dedent
import unittest

from canonical.config import config
from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.browser.person import (
    BranchTraversalMixin, PersonView)
from canonical.launchpad.ftests import login_person
from canonical.launchpad.interfaces import NotFoundError
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.lazr.testing.webservice import FakeRequest


class PersonView_openid_identity_url_TestCase(TestCaseWithFactory):
    """Tests for the public OpenID identifier shown on the profile page."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.user = self.factory.makePerson(name='eris')
        self.request = LaunchpadTestRequest(
            SERVER_URL="http://launchpad.dev/")
        login_person(self.user, self.request)
        self.view = PersonView(self.user, self.request)
        # Marker allowing us to reset the config.
        config.push(self.id(), '')
        self.addCleanup(config.pop, self.id())

    def test_should_be_profile_page_when_delegating(self):
        """The profile page is the OpenID identifier in normal situation."""
        self.assertEquals(
            'http://launchpad.dev/~eris', self.view.openid_identity_url)

    def test_should_be_production_profile_page_when_not_delegating(self):
        """When the profile page is not delegated, the OpenID identity URL
        should be the one on the main production site."""
        config.push('non-delegating', dedent('''
            [vhost.mainsite]
            openid_delegate_profile: False

            [launchpad]
            non_restricted_hostname: prod.launchpad.dev
            '''))
        self.assertEquals(
            'http://prod.launchpad.dev/~eris', self.view.openid_identity_url)


class TestBranchTraversal(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self._redirects = []

    def assertRedirects(self, to_url, function, *args, **kwargs):
        del self._redirects[:]
        function(*args, **kwargs)
        self.assertEqual([to_url], self._redirects)

    def makeTraverser(self, person, traversed=None, stack=None):
        request = FakeRequest(traversed, stack)
        traverser = BranchTraversalMixin()
        traverser.context = person
        traverser.request = request
        traverser.redirectSubTree = self._redirects.append
        return traverser

    def test_redirect_branch(self):
        branch = self.factory.makeBranch()
        segments = branch.unique_name.split('/')[1:]
        segments.reverse()
        traverser = self.makeTraverser(branch.owner, [], segments)
        self.assertRedirects(canonical_url(branch), traverser.redirect_branch)

    def test_redirect_branch_not_found(self):
        person = self.factory.makePerson()
        segments = ['no-branch', 'no-product']
        traverser = self.makeTraverser(person, [], segments)
        self.assertRaises(NotFoundError, traverser.redirect_branch)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    suite.addTest(LayeredDocFileSuite(
        'person-rename-account-with-openid.txt',
        setUp=setUp, tearDown=tearDown,
        layer=DatabaseFunctionalLayer))
    return suite


if __name__ == '__main__':
    unittest.main()

