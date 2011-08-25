# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import datetime
import doctest
import unittest

from lazr.restful.testing.webservice import FakeRequest
import pytz
from testtools.matchers import Equals
from zope.component import getUtility
from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.interfaces import BrowserNotificationLevel
from canonical.launchpad.webapp.servers import StepsToGo
from canonical.launchpad.testing.pages import (
    extract_text,
    find_tag_by_id,
    )
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.browser.tales import format_link
from lp.blueprints.browser import specification
from lp.blueprints.enums import SpecificationImplementationStatus
from lp.blueprints.interfaces.specification import (
    ISpecification,
    ISpecificationSet,
    )
from lp.testing import (
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view
from testtools.matchers import DocTestMatches

class TestSpecificationSearch(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_search_with_percent(self):
        # Using '%' in a search should not error.
        specs = getUtility(ISpecificationSet)
        form = {'field.search_text': r'%'}
        view = create_initialized_view(specs, '+index', form=form)
        self.assertEqual([], view.errors)


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


class TestSpecificationView(TestCaseWithFactory):
    """Test the SpecificationView."""

    layer = DatabaseFunctionalLayer

    def test_offsite_url(self):
        """The specification URL is rendered when present."""
        spec = self.factory.makeSpecification()
        login_person(spec.owner)
        spec.specurl = 'http://eg.dom/parrot'
        view = create_initialized_view(
            spec, name='+index', principal=spec.owner,
            rootsite='blueprints')
        li = find_tag_by_id(view.render(), 'spec-url')
        self.assertEqual('nofollow', li.a['rel'])
        self.assertEqual(spec.specurl, li.a['href'])

    def test_registration_date_displayed(self):
        """The time frame does not prepend on incorrectly."""
        spec = self.factory.makeSpecification(
            owner=self.factory.makePerson(displayname="Some Person"))
        html = create_initialized_view(
                spec, '+index')()
        self.assertThat(extract_text(html), DocTestMatches(extract_text(
            "... Registered by Some Person a moment ago ..."), doctest.ELLIPSIS
            | doctest.NORMALIZE_WHITESPACE | doctest.REPORT_NDIFF))

class TestSpecificationEditStatusView(TestCaseWithFactory):
    """Test the SpecificationEditStatusView."""

    layer = DatabaseFunctionalLayer

    def test_records_started(self):
        not_started = SpecificationImplementationStatus.NOTSTARTED
        spec = self.factory.makeSpecification(
            implementation_status=not_started)
        login_person(spec.owner)
        form = {
            'field.implementation_status': 'STARTED',
            'field.actions.change': 'Change',
            }
        view = create_initialized_view(spec, name='+status', form=form)
        self.assertEqual(
            SpecificationImplementationStatus.STARTED,
            spec.implementation_status)
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
            SpecificationImplementationStatus.SLOW,
            spec.implementation_status)
        self.assertEqual(0, len(view.request.notifications))

    def test_records_unstarting(self):
        # If a spec was started, and is changed to not started,
        # a notice is shown. Also the spec.starter is cleared out.
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
            'Blueprint is now considered "Not started".',
            notification.message)

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


class TestSpecificationFieldXHTMLRepresentations(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_starter_empty(self):
        blueprint = self.factory.makeBlueprint()
        repr_method = specification.starter_xhtml_representation(
            blueprint, ISpecification['starter'], None)
        self.assertThat(repr_method(), Equals(''))

    def test_starter_set(self):
        user = self.factory.makePerson()
        blueprint = self.factory.makeBlueprint(owner=user)
        when = datetime(2011, 1, 1, tzinfo=pytz.UTC)
        with person_logged_in(user):
            blueprint.setImplementationStatus(
                SpecificationImplementationStatus.STARTED, user)
        removeSecurityProxy(blueprint).date_started = when
        repr_method = specification.starter_xhtml_representation(
            blueprint, ISpecification['starter'], None)
        expected = format_link(user) + ' on 2011-01-01'
        self.assertThat(repr_method(), Equals(expected))

    def test_completer_empty(self):
        blueprint = self.factory.makeBlueprint()
        repr_method = specification.completer_xhtml_representation(
            blueprint, ISpecification['completer'], None)
        self.assertThat(repr_method(), Equals(''))

    def test_completer_set(self):
        user = self.factory.makePerson()
        blueprint = self.factory.makeBlueprint(owner=user)
        when = datetime(2011, 1, 1, tzinfo=pytz.UTC)
        with person_logged_in(user):
            blueprint.setImplementationStatus(
                SpecificationImplementationStatus.IMPLEMENTED, user)
        removeSecurityProxy(blueprint).date_completed = when
        repr_method = specification.completer_xhtml_representation(
            blueprint, ISpecification['completer'], None)
        expected = format_link(user) + ' on 2011-01-01'
        self.assertThat(repr_method(), Equals(expected))
