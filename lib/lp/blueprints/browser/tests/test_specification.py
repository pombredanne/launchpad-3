# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import datetime
import json
import unittest

from BeautifulSoup import BeautifulSoup
import pytz
import soupmatchers
from testtools.matchers import (
    Equals,
    Not,
    )
from testtools.testcase import ExpectedException
import transaction
from zope.component import getUtility
from zope.publisher.interfaces import NotFound
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.app.browser.tales import format_link
from lp.blueprints.browser import specification
from lp.blueprints.enums import SpecificationImplementationStatus
from lp.blueprints.interfaces.specification import (
    ISpecification,
    ISpecificationSet,
    )
from lp.registry.enums import InformationType
from lp.registry.interfaces.person import PersonVisibility
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.interfaces import BrowserNotificationLevel
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    BrowserTestCase,
    FakeLaunchpadRequest,
    login_person,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import DocTestMatches
from lp.testing.pages import (
    extract_text,
    find_tag_by_id,
    setupBrowser,
    setupBrowserForUser,
    )
from lp.testing.views import create_initialized_view


class TestSpecificationSearch(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_search_with_percent(self):
        # Using '%' in a search should not error.
        specs = getUtility(ISpecificationSet)
        form = {'field.search_text': r'%'}
        view = create_initialized_view(specs, '+index', form=form)
        self.assertEqual([], view.errors)


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
        request = FakeLaunchpadRequest([], stack)
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
        self.assertThat(
            extract_text(html), DocTestMatches(
                "... Registered by Some Person ... ago ..."))


class TestSpecificationInformationType(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    portlet_tag = soupmatchers.Tag('info-type-portlet', True,
                                   attrs=dict(id='information-type-summary'))

    def setUp(self):
        super(TestSpecificationInformationType, self).setUp()
        self.useFixture(FeatureFixture({'blueprints.information_type.enabled':
            'true'}))

    def assertBrowserMatches(self, matcher):
        browser = self.getViewBrowser(self.factory.makeSpecification())
        self.assertThat(browser.contents, matcher)

    def test_has_privacy_portlet(self):
        self.assertBrowserMatches(soupmatchers.HTMLContains(self.portlet_tag))

    def test_privacy_portlet_requires_flag(self):
        self.useFixture(FeatureFixture({'blueprints.information_type.enabled':
            ''}))
        self.assertBrowserMatches(
            Not(soupmatchers.HTMLContains(self.portlet_tag)))

    def test_has_privacy_banner(self):
        owner = self.factory.makePerson()
        spec = self.factory.makeSpecification(
            information_type=InformationType.PROPRIETARY, owner=owner)
        browser = self.getViewBrowser(spec, user=owner)
        privacy_banner = soupmatchers.Tag('privacy-banner', True,
                attrs={'class': 'banner-text'})
        self.assertThat(browser.contents,
                        soupmatchers.HTMLContains(privacy_banner))

    def set_secrecy(self, spec, owner, information_type='PROPRIETARY'):
        form = {
            'field.actions.change': 'Change',
            'field.information_type': information_type,
            'field.validate_change': 'off',
        }
        with person_logged_in(owner):
            view = create_initialized_view(
                spec, '+secrecy', form, principal=owner,
                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            body = view.render()
        return view.request.response.getStatus(), body

    def test_secrecy_change(self):
        """Setting the value via '+secrecy' works."""
        owner = self.factory.makePerson()
        spec = self.factory.makeSpecification(owner=owner)
        self.set_secrecy(spec, owner)
        with person_logged_in(owner):
            self.assertEqual(InformationType.PROPRIETARY,
                             spec.information_type)

    def test_secrecy_change_nonsense(self):
        """Invalid values produce sane errors."""
        owner = self.factory.makePerson()
        spec = self.factory.makeSpecification(owner=owner)
        transaction.commit()
        status, body = self.set_secrecy(
            spec, owner, information_type=self.factory.getUniqueString())
        self.assertEqual(400, status)
        error_data = json.loads(body)
        self.assertEqual({u'field.information_type': u'Invalid value'},
                         error_data['errors'])
        self.assertEqual(InformationType.PUBLIC, spec.information_type)

    def test_secrecy_change_unprivileged(self):
        """Unprivileged users cannot change information_type."""
        spec = self.factory.makeSpecification()
        person = self.factory.makePerson()
        with ExpectedException(Unauthorized):
            self.set_secrecy(spec, person)
        self.assertEqual(InformationType.PUBLIC, spec.information_type)


class TestSpecificationViewPrivateArtifacts(BrowserTestCase):
    """ Tests that specifications with private team artifacts can be viewed.

    A Specification may be associated with a private team as follows:
    - a subscriber is a private team

    A logged in user who is not authorised to see the private team(s) still
    needs to be able to view the specification. The private team will be
    rendered in the normal way, displaying the team name and Launchpad URL.
    """

    layer = DatabaseFunctionalLayer

    def _getBrowser(self, user=None):
        if user is None:
            browser = setupBrowser()
            logout()
            return browser
        else:
            login_person(user)
        return setupBrowserForUser(user=user)

    def test_view_specification_with_private_subscriber(self):
        # A specification with a private subscriber is rendered.
        private_subscriber = self.factory.makeTeam(
            name="privateteam",
            visibility=PersonVisibility.PRIVATE)
        spec = self.factory.makeSpecification()
        with person_logged_in(spec.owner):
            spec.subscribe(private_subscriber, spec.owner)
            # Ensure the specification subscriber is rendered.
            url = canonical_url(spec, rootsite='blueprints')
            user = self.factory.makePerson()
            browser = self._getBrowser(user)
            browser.open(url)
            soup = BeautifulSoup(browser.contents)
            subscriber_portlet = soup.find(
                'div', attrs={'id': 'subscribers'})
            self.assertIsNotNone(
                subscriber_portlet.find('a', text='Privateteam'))

    def test_anonymous_view_specification_with_private_subscriber(self):
        # A specification with a private subscriber is not rendered for anon.
        private_subscriber = self.factory.makeTeam(
            name="privateteam",
            visibility=PersonVisibility.PRIVATE)
        spec = self.factory.makeSpecification()
        with person_logged_in(spec.owner):
            spec.subscribe(private_subscriber, spec.owner)
            # Viewing the specification doesn't display private subscriber.
            url = canonical_url(spec, rootsite='blueprints')
            browser = self._getBrowser()
            browser.open(url)
            soup = BeautifulSoup(browser.contents)
            self.assertIsNone(
                soup.find('div', attrs={'id': 'subscriber-privateteam'}))


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
