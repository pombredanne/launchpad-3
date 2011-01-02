# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from lazr.restful.testing.webservice import FakeRequest
from zope.publisher.interfaces import NotFound

from canonical.launchpad.webapp.interfaces import BrowserNotificationLevel
from canonical.launchpad.webapp.servers import StepsToGo
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.blueprints.browser import specification
from lp.blueprints.enums import SpecificationImplementationStatus
from lp.testing import login_person, TestCaseWithFactory
from lp.testing.views import create_initialized_view


class LocalFakeRequest(FakeRequest):

    @property
    def stepstogo(self):
        """See IBasicLaunchpadRequest.

        This method is called by traversal machinery.
        """
        return StepsToGo(self)


class TestBranchTraversal(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.specification = self.factory.makeSpecification()

    def assertRedirects(self, segments, url):
        redirection = self.traverse(segments)
        self.assertEqual(url, redirection.target)

    def linkBranch(self, branch):
        self.specification.linkBranch(branch, self.factory.makePerson())

    def traverse(self, segments):
        stack = list(reversed(['+branch'] + segments))
        name = stack.pop()
        request = LocalFakeRequest([], stack)
        traverser = specification.SpecificationNavigation(
            self.specification, request)
        return traverser.publishTraverse(request, name)

    def test_junk_branch(self):
        branch = self.factory.makePersonalBranch()
        self.linkBranch(branch)
        segments = [branch.owner.name, '+junk', branch.name]
        self.assertEqual(
            self.specification.getBranchLink(branch), self.traverse(segments))

    def test_junk_branch_no_such_person(self):
        person_name = self.factory.getUniqueString()
        branch_name = self.factory.getUniqueString()
        self.assertRaises(
            NotFound, self.traverse, [person_name, '+junk', branch_name])

    def test_junk_branch_no_such_branch(self):
        person = self.factory.makePerson()
        branch_name = self.factory.getUniqueString()
        self.assertRaises(
            NotFound, self.traverse, [person.name, '+junk', branch_name])

    def test_product_branch(self):
        branch = self.factory.makeProductBranch()
        self.linkBranch(branch)
        segments = [branch.owner.name, branch.product.name, branch.name]
        self.assertEqual(
            self.specification.getBranchLink(branch), self.traverse(segments))

    def test_product_branch_no_such_person(self):
        person_name = self.factory.getUniqueString()
        product_name = self.factory.getUniqueString()
        branch_name = self.factory.getUniqueString()
        self.assertRaises(
            NotFound, self.traverse, [person_name, product_name, branch_name])

    def test_product_branch_no_such_product(self):
        person = self.factory.makePerson()
        product_name = self.factory.getUniqueString()
        branch_name = self.factory.getUniqueString()
        self.assertRaises(
            NotFound, self.traverse, [person.name, product_name, branch_name])

    def test_product_branch_no_such_branch(self):
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        branch_name = self.factory.getUniqueString()
        self.assertRaises(
            NotFound, self.traverse, [person.name, product.name, branch_name])

    def test_package_branch(self):
        branch = self.factory.makePackageBranch()
        self.linkBranch(branch)
        segments = [
            branch.owner.name,
            branch.distribution.name,
            branch.distroseries.name,
            branch.sourcepackagename.name,
            branch.name]
        self.assertEqual(
            self.specification.getBranchLink(branch), self.traverse(segments))


class TestSpecificationEditStatusView(TestCaseWithFactory):
    """Test the SpecificationEditStatusView."""

    layer = DatabaseFunctionalLayer

    def test_records_started(self):
        spec = self.factory.makeSpecification(
            implementation_status=SpecificationImplementationStatus.NOTSTARTED)
        login_person(spec.owner)
        form = {
            'field.implementation_status': 'STARTED',
            'field.actions.change': 'Change',
            }
        view = create_initialized_view(spec, name='+status', form=form)
        self.assertEqual(
            SpecificationImplementationStatus.STARTED, spec.implementation_status)
        self.assertEqual(spec.owner, spec.starter)
        [notification] = view.request.notifications
        self.assertEqual(BrowserNotificationLevel.INFO, notification.level)
        self.assertEqual(
            'Blueprint is now considered "Started".', notification.message)

    def test_unchanged_lifecycle_has_no_notification(self):
        spec = self.factory.makeSpecification(
            implementation_status=SpecificationImplementationStatus.STARTED)
        login_person(spec.owner)
        form = {
            'field.implementation_status': 'SLOW',
            'field.actions.change': 'Change',
            }
        view = create_initialized_view(spec, name='+status', form=form)
        self.assertEqual(
            SpecificationImplementationStatus.SLOW, spec.implementation_status)
        self.assertEqual(0, len(view.request.notifications))

    def test_records_unstarting(self):
        # If a spec was started, and is changed to not started, a notice is shown.
        # Also the spec.starter is cleared out.
        spec = self.factory.makeSpecification(
            implementation_status=SpecificationImplementationStatus.STARTED)
        login_person(spec.owner)
        form = {
            'field.implementation_status': 'NOTSTARTED',
            'field.actions.change': 'Change',
            }
        view = create_initialized_view(spec, name='+status', form=form)
        self.assertEqual(
            SpecificationImplementationStatus.NOTSTARTED,
            spec.implementation_status)
        self.assertIs(None, spec.starter)
        [notification] = view.request.notifications
        self.assertEqual(BrowserNotificationLevel.INFO, notification.level)
        self.assertEqual(
            'Blueprint is now considered "Not started".', notification.message)

    def test_records_completion(self):
        # If a spec is marked as implemented the user is notifiec it is now
        # complete.
        spec = self.factory.makeSpecification(
            implementation_status=SpecificationImplementationStatus.STARTED)
        login_person(spec.owner)
        form = {
            'field.implementation_status': 'IMPLEMENTED',
            'field.actions.change': 'Change',
            }
        view = create_initialized_view(spec, name='+status', form=form)
        self.assertEqual(
            SpecificationImplementationStatus.IMPLEMENTED,
            spec.implementation_status)
        self.assertEqual(spec.owner, spec.completer)
        [notification] = view.request.notifications
        self.assertEqual(BrowserNotificationLevel.INFO, notification.level)
        self.assertEqual(
            'Blueprint is now considered "Complete".', notification.message)


class TestSecificationHelpers(unittest.TestCase):
    """Test specification helper functions."""

    def test_dict_to_DOT_attrs(self):
        """Verify that dicts are converted to a sorted DOT attr string."""
        expected_attrs = (
            u'  [\n'
            u'  "bar"="bar \\" \\n bar",\n'
            u'  "baz"="zab",\n'
            u'  "foo"="foo"\n'
            u'  ]')
        dict_attrs = dict(
            foo="foo",
            bar="bar \" \n bar",
            baz="zab")
        dot_attrs = specification.dict_to_DOT_attrs(dict_attrs, indent='  ')
        self.assertEqual(dot_attrs, expected_attrs)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())
