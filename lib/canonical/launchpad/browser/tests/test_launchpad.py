# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for traversal from the root branch object.."""

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.browser.launchpad import LaunchpadRootNavigation
from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.launchpad.webapp.url import urlappend
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.errors import GoneError
from lp.registry.interfaces.person import (
    IPersonSet,
    PersonVisibility,
    )
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.views import create_view


class TraversalMixin:

    def assertNotFound(self, path):
        self.assertRaises(NotFound, self.traverse, path)

    def assertRedirects(self, segments, url):
        redirection = self.traverse(segments)
        self.assertEqual(url, redirection.target)

    def traverse(self, path, first_segment):
        """Traverse to 'segments' using a 'LaunchpadRootNavigation' object.

        Using the Zope traversal machinery, traverse to the path given by
        'segments', starting at a `LaunchpadRootNavigation` object.

        :param segments: A list of path segments.
        :return: The object found.
        """
        request = LaunchpadTestRequest(
            PATH_INFO=urlappend('/%s' % first_segment, path))
        segments = reversed(path.split('/'))
        request.setTraversalStack(segments)
        traverser = LaunchpadRootNavigation(None, request=request)
        return traverser.publishTraverse(request, first_segment)


class TestBranchTraversal(TestCaseWithFactory, TraversalMixin):
    """Branches are traversed to from IPersons. Test we can reach them.

    This class tests the `PersonNavigation` class to see that we can traverse
    to branches from such objects.
    """

    layer = DatabaseFunctionalLayer

    def traverse(self, path):
        return super(TestBranchTraversal, self).traverse(path, '+branch')

    def test_unique_name_traversal(self):
        # Traversing to /+branch/<unique_name> redirects to the page for that
        # branch.
        branch = self.factory.makeAnyBranch()
        self.assertRedirects(branch.unique_name, canonical_url(branch))

    def test_no_such_unique_name(self):
        # Traversing to /+branch/<unique_name> where 'unique_name' is for a
        # branch that doesn't exist will generate a 404.
        branch = self.factory.makeAnyBranch()
        self.assertNotFound(branch.unique_name + 'wibble')

    def test_product_alias(self):
        # Traversing to /+branch/<product> redirects to the page for the
        # branch that is the development focus branch for that product.
        branch = self.factory.makeProductBranch()
        product = removeSecurityProxy(branch.product)
        product.development_focus.branch = branch
        self.assertRedirects(product.name, canonical_url(branch))

    def test_nonexistent_product(self):
        # Traversing to /+branch/<no-such-product> generates a 404.
        self.assertNotFound('non-existent')

    def test_product_without_dev_focus(self):
        # Traversing to a product without a development focus generates a 404.
        product = self.factory.makeProduct()
        self.assertNotFound(product.name)

    def test_trailing_path_redirect(self):
        # If there are any trailing path segments after the branch identifier,
        # these stick around at the redirected URL.
        branch = self.factory.makeAnyBranch()
        path = urlappend(branch.unique_name, '+edit')
        self.assertRedirects(path, canonical_url(branch, view_name='+edit'))

    def test_product_series_redirect(self):
        # Traversing to /+branch/<product>/<series> redirects to the branch
        # for that series, if there is one.
        branch = self.factory.makeProductBranch()
        product = branch.product
        series = self.factory.makeProductSeries(product=product)
        removeSecurityProxy(series).branch = branch
        self.assertRedirects(
            '%s/%s' % (product.name, series.name), canonical_url(branch))

    def test_nonexistent_product_series(self):
        # /+branch/<product>/<series> generates a 404 if there is no such
        # series.
        product = self.factory.makeProduct()
        self.assertNotFound('%s/nonexistent' % product.name)

    def test_no_branch_for_series(self):
        # If there's no branch for a product series, generate a 404.
        series = self.factory.makeProductSeries()
        self.assertNotFound('%s/%s' % (series.product.name, series.name))

    def test_too_short_branch_name(self):
        # 404 if the thing following +branch is a unique name that's too short
        # to be a real unique name.
        owner = self.factory.makePerson()
        self.assertNotFound('~%s' % owner.name)

    def test_invalid_product_name(self):
        # 404 if the thing following +branch has an invalid product name.
        self.assertNotFound('a')


class TestPersonTraversal(TestCaseWithFactory, TraversalMixin):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonTraversal, self).setUp()
        self.any_user = self.factory.makePerson()
        self.admin = getUtility(IPersonSet).getByName('name16')

    def test_person(self):
        # Verify a user is returned.
        name = 'active-person'
        person = self.factory.makePerson(name=name)
        segment = '~%s' % name
        traversed = self.traverse(segment, segment)
        self.assertEqual(person, traversed)

    def test_suspended_person_visible_to_admin_only(self):
        # Verify a suspended user is only traversable by an admin.
        name = 'suspended-person'
        person = self.factory.makePerson(name=name)
        login_person(self.admin)
        removeSecurityProxy(person).account_status = AccountStatus.SUSPENDED
        segment = '~%s' % name
        # Admins can see the suspended user.
        traversed = self.traverse(segment, segment)
        self.assertEqual(person, traversed)
        # Regular users cannot see the suspended user.
        login_person(self.any_user)
        self.assertRaises(GoneError, self.traverse, segment, segment)

    def test_public_team(self):
        # Verify a public team is returned.
        name = 'public-team'
        team = self.factory.makeTeam(name=name)
        segment = '~%s' % name
        traversed = self.traverse(segment, segment)
        self.assertEqual(team, traversed)

    def test_private_team_visible_to_admin_and_members_only(self):
        # Verify a private team is  team is returned.
        name = 'private-team'
        team = self.factory.makeTeam(name=name)
        login_person(self.admin)
        team.visibility = PersonVisibility.PRIVATE
        segment = '~%s' % name
        # Admins can traverse to the team.
        traversed = self.traverse(segment, segment)
        self.assertEqual(team, traversed)
        # Members can traverse to the team.
        login_person(team.teamowner)
        traversed = self.traverse(segment, segment)
        self.assertEqual(team, traversed)
        # All other user cannot traverse to the team.
        login_person(self.any_user)
        self.assertRaises(NotFound, self.traverse, segment, segment)


class TestErrorViews(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_GoneError(self):
        error = GoneError('User is suspended')
        view = create_view(error, 'index.html')
        self.assertEqual('Error: Page gone', view.page_title)
        self.assertEqual(410, view.request.response.getStatus())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
