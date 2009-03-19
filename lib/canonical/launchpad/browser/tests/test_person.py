# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test harness for person views unit tests."""

__metaclass__ = type


from textwrap import dedent
import unittest

from zope.security.proxy import removeSecurityProxy
from zope.publisher.interfaces import NotFound

from canonical.config import config
from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.browser.person import PersonNavigation, PersonView
from canonical.launchpad.ftests import login_person
from canonical.launchpad.interfaces.personproduct import IPersonProduct
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.launchpad.webapp.publisher import canonical_url
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
    """Branches are traversed to from IPersons. Test we can reach them.

    This class tests the `PersonNavigation` class to see that we can traverse
    to branches from such objects.
    """

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.person = self.factory.makePerson()

    def assertRedirects(self, segments, url):
        redirection = self.traverse(segments)
        self.assertEqual(url, redirection.target)

    def traverse(self, segments):
        """Traverse to 'segments' using a 'PersonNavigation' object.

        Using the Zope traversal machinery, traverse to the path given by
        'segments', starting at a `PersonNavigation` object wrapped around the
        'person' attribute.

        :param segments: A list of path segments.
        :return: The object found.
        """
        stack = list(reversed(segments))
        name = stack.pop()
        request = FakeRequest(['~' + self.person.name], stack)
        traverser = PersonNavigation(self.person, request)
        return traverser.publishTraverse(request, name)

    def test_redirect_product_branch(self):
        branch = self.factory.makeProductBranch(owner=self.person)
        segments = ['+branch', branch.product.name, branch.name]
        self.assertRedirects(segments, canonical_url(branch))

    def test_redirect_junk_branch(self):
        branch = self.factory.makePersonalBranch(owner=self.person)
        segments = ['+branch', '+junk', branch.name]
        self.assertRedirects(segments, canonical_url(branch))

    def test_redirect_branch_not_found(self):
        self.assertRaises(
            NotFound, self.traverse, ['+branch', 'no-product', 'no-branch'])

    def test_redirect_on_package_branch_aliases(self):
        branch = self.factory.makePackageBranch(owner=self.person)
        distro = removeSecurityProxy(branch.distribution)
        distro.setAliases(['foo'])
        self.assertRedirects(
            ['foo', branch.distroseries.name, branch.sourcepackagename.name,
             branch.name],
            canonical_url(branch))

    def test_junk_branch(self):
        branch = self.factory.makePersonalBranch(owner=self.person)
        segments = ['+junk', branch.name]
        self.assertEqual(branch, self.traverse(segments))

    def test_junk_branch_no_such_branch(self):
        branch_name = self.factory.getUniqueString()
        self.assertRaises(NotFound, self.traverse, ['+junk', branch_name])

    def test_product_branch(self):
        branch = self.factory.makeProductBranch(owner=self.person)
        segments = [branch.product.name, branch.name]
        self.assertEqual(branch, self.traverse(segments))

    def test_product_only(self):
        # Traversal to the product returns an IPersonProduct.
        product = self.factory.makeProduct()
        target = self.traverse([product.name])
        self.assertTrue(IPersonProduct.providedBy(target))

    def test_product_branch_no_such_product(self):
        product_name = self.factory.getUniqueString()
        branch_name = self.factory.getUniqueString()
        self.assertRaises(
            NotFound, self.traverse, [product_name, branch_name])

    def test_product_branch_no_such_branch(self):
        # Since the branch is not found, an IPersonProduct is returned.
        product = self.factory.makeProduct()
        branch_name = self.factory.getUniqueString()
        target = self.traverse([product.name, branch_name])
        self.assertTrue(IPersonProduct.providedBy(target))

    def test_package_branch(self):
        branch = self.factory.makePackageBranch(owner=self.person)
        segments = [
            branch.distribution.name,
            branch.distroseries.name,
            branch.sourcepackagename.name,
            branch.name]
        self.assertEqual(branch, self.traverse(segments))


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

