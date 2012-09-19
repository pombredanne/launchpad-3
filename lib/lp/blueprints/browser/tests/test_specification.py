# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import datetime
import json
import re
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
from lp.app.interfaces.services import IService
from lp.blueprints.browser import specification
from lp.blueprints.browser.specification import INFORMATION_TYPE_FLAG
from lp.blueprints.enums import SpecificationImplementationStatus
from lp.blueprints.interfaces.specification import (
    ISpecification,
    ISpecificationSet,
    )
from lp.registry.enums import (
    InformationType,
    SpecificationSharingPolicy,
    )
from lp.registry.interfaces.person import PersonVisibility
from lp.registry.interfaces.product import (
    IProduct,
    IProductSeries,
    )
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


def set_blueprint_information_type(test_case, enabled):
    value = 'true' if enabled else ''
    fixture = FeatureFixture({INFORMATION_TYPE_FLAG: value})
    test_case.useFixture(fixture)


class TestSpecificationSet(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def test_index_with_proprietary(self):
        """Blueprints home page tolerates proprietary Specifications."""
        specs = getUtility(ISpecificationSet)
        product = self.factory.makeProduct(
            specification_sharing_policy=
                SpecificationSharingPolicy.PUBLIC_OR_PROPRIETARY)
        spec = self.factory.makeSpecification(product=product)
        spec_name = spec.name
        spec_owner = spec.owner
        browser = self.getViewBrowser(specs)
        self.assertNotIn('Not allowed', browser.contents)
        self.assertIn(spec_name, browser.contents)
        with person_logged_in(spec_owner):
            removeSecurityProxy(spec.target)._ensurePolicies(
                [InformationType.PROPRIETARY])
            spec.transitionToInformationType(InformationType.PROPRIETARY,
                                             spec.owner)
        browser = self.getViewBrowser(specs)
        self.assertNotIn('Not allowed', browser.contents)
        self.assertNotIn(spec_name, browser.contents)


class TestSpecificationInformationType(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    portlet_tag = soupmatchers.Tag('info-type-portlet', True,
                                   attrs=dict(id='information-type-summary'))

    def setUp(self):
        super(TestSpecificationInformationType, self).setUp()
        set_blueprint_information_type(self, True)

    def assertBrowserMatches(self, matcher):
        browser = self.getViewBrowser(self.factory.makeSpecification())
        self.assertThat(browser.contents, matcher)

    def test_has_privacy_portlet(self):
        self.assertBrowserMatches(soupmatchers.HTMLContains(self.portlet_tag))

    def test_privacy_portlet_requires_flag(self):
        set_blueprint_information_type(self, False)
        self.assertBrowserMatches(
            Not(soupmatchers.HTMLContains(self.portlet_tag)))

    def test_has_privacy_banner(self):
        owner = self.factory.makePerson()
        target = self.factory.makeProduct(
            specification_sharing_policy=
                SpecificationSharingPolicy.PUBLIC_OR_PROPRIETARY)
        removeSecurityProxy(target)._ensurePolicies(
            [InformationType.PROPRIETARY])
        spec = self.factory.makeSpecification(
            information_type=InformationType.PROPRIETARY, owner=owner,
            product=target)
        with person_logged_in(target.owner):
            getUtility(IService, 'sharing').ensureAccessGrants(
                [owner], target.owner, specifications=[spec])
        with person_logged_in(owner):
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
        product = self.factory.makeProduct(
            specification_sharing_policy=
                SpecificationSharingPolicy.PUBLIC_OR_PROPRIETARY)
        spec = self.factory.makeSpecification(owner=owner, product=product)
        removeSecurityProxy(spec.target)._ensurePolicies(
            [InformationType.PROPRIETARY])
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
        product = self.factory.makeProduct(
            specification_sharing_policy=
                SpecificationSharingPolicy.PUBLIC_OR_PROPRIETARY)
        spec = self.factory.makeSpecification(product=product)
        person = self.factory.makePerson()
        with ExpectedException(Unauthorized):
            self.set_secrecy(spec, person)
        self.assertEqual(InformationType.PUBLIC, spec.information_type)

    def test_view_banner(self):
        """The privacy banner should reflect the information_type."""
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(
            owner=owner,
            specification_sharing_policy=
                SpecificationSharingPolicy.PUBLIC_OR_PROPRIETARY)
        spec = self.factory.makeSpecification(
            information_type=InformationType.PROPRIETARY, owner=owner,
            product=product)

        privacy_banner = soupmatchers.Tag('privacy-banner', True,
                attrs={'class': 'banner-text'},
                text=re.compile('This page contains Proprietary information'))

        getUtility(IService, 'sharing').ensureAccessGrants(
              [owner], owner, specifications=[spec],
              ignore_permissions=True)

        browser = self.getViewBrowser(spec, '+index', user=owner)
        self.assertThat(browser.contents,
                        soupmatchers.HTMLContains(privacy_banner))
        browser = self.getViewBrowser(spec, '+subscribe', user=owner)
        self.assertThat(browser.contents,
                        soupmatchers.HTMLContains(privacy_banner))


# canonical_url erroneously returns http://blueprints.launchpad.dev/+new
NEW_SPEC_FROM_ROOT_URL = 'http://blueprints.launchpad.dev/specs/+new'


class TestNewSpecificationInformationType(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestNewSpecificationInformationType, self).setUp()
        set_blueprint_information_type(self, True)
        it_field = soupmatchers.Tag('it-field', True,
                                    attrs=dict(name='field.information_type'))
        self.match_it = soupmatchers.HTMLContains(it_field)

    def test_from_root(self):
        """Information_type is included creating from root."""
        browser = self.getUserBrowser(NEW_SPEC_FROM_ROOT_URL)
        self.assertThat(browser.contents, self.match_it)

    def test_from_root_no_flag(self):
        """Information_type is excluded with no flag."""
        set_blueprint_information_type(self, False)
        browser = self.getUserBrowser(NEW_SPEC_FROM_ROOT_URL)
        self.assertThat(browser.contents, Not(self.match_it))

    def test_from_sprint(self):
        """Information_type is included creating from a sprint."""
        sprint = self.factory.makeSprint()
        browser = self.getViewBrowser(sprint, view_name='+addspec')
        self.assertThat(browser.contents, self.match_it)

    def test_from_sprint_no_flag(self):
        """Information_type is excluded with no flag."""
        set_blueprint_information_type(self, False)
        sprint = self.factory.makeSprint()
        browser = self.getViewBrowser(sprint, view_name='+addspec')
        self.assertThat(browser.contents, Not(self.match_it))

    def submitSpec(self, browser):
        """Submit a Specification via a browser."""
        name = self.factory.getUniqueString()
        browser.getControl('Name').value = name
        browser.getControl('Title').value = self.factory.getUniqueString()
        browser.getControl('Summary').value = self.factory.getUniqueString()
        browser.getControl('Register Blueprint').click()
        return name

    def createSpec(self, information_type, sharing_policy=None):
        """Create a specification via a browser."""
        with person_logged_in(self.user):
            product = self.factory.makeProduct(owner=self.user)
            if sharing_policy is not None:
                self.factory.makeCommercialSubscription(product)
                product.setSpecificationSharingPolicy(sharing_policy)
            policy = self.factory.makeAccessPolicy(product, information_type)
            self.factory.makeAccessPolicyGrant(
                policy, grantee=self.user, grantor=self.user)
            browser = self.getViewBrowser(product, view_name='+addspec')
            control = browser.getControl(information_type.title)
            if not control.selected:
                control.click()
            return product.getSpecification(self.submitSpec(browser))

    def test_supplied_information_types(self):
        """Creating honours information types."""
        spec = self.createSpec(
            InformationType.PUBLIC,
            sharing_policy=SpecificationSharingPolicy.PUBLIC_OR_PROPRIETARY)
        self.assertEqual(InformationType.PUBLIC, spec.information_type)
        spec = self.createSpec(
            InformationType.PROPRIETARY,
            sharing_policy=SpecificationSharingPolicy.PUBLIC_OR_PROPRIETARY)
        self.assertEqual(InformationType.PROPRIETARY, spec.information_type)
        spec = self.createSpec(
            InformationType.EMBARGOED,
            SpecificationSharingPolicy.EMBARGOED_OR_PROPRIETARY)
        self.assertEqual(InformationType.EMBARGOED, spec.information_type)

    def test_from_product_no_flag(self):
        """information_type is excluded with no flag."""
        set_blueprint_information_type(self, False)
        product = self.factory.makeProduct()
        browser = self.getViewBrowser(product, view_name='+addspec')
        self.assertThat(browser.contents, Not(self.match_it))

    def test_from_productseries(self):
        """Information_type is included creating from productseries."""
        product = self.factory.makeProduct(
            specification_sharing_policy=
                SpecificationSharingPolicy.PUBLIC_OR_PROPRIETARY)
        series = self.factory.makeProductSeries(product=product)
        browser = self.getViewBrowser(series, view_name='+addspec')
        self.assertThat(browser.contents, self.match_it)

    def test_from_productseries_no_flag(self):
        """information_type is excluded with no flag."""
        set_blueprint_information_type(self, False)
        series = self.factory.makeProductSeries()
        browser = self.getViewBrowser(series, view_name='+addspec')
        self.assertThat(browser.contents, Not(self.match_it))

    def test_from_distribution(self):
        """information_type is excluded creating from distro."""
        distro = self.factory.makeDistribution()
        browser = self.getViewBrowser(distro, view_name='+addspec')
        self.assertThat(browser.contents, Not(self.match_it))

    def test_from_distroseries(self):
        """information_type is excluded creating from distroseries."""
        series = self.factory.makeDistroSeries()
        browser = self.getViewBrowser(series, view_name='+addspec')
        self.assertThat(browser.contents, Not(self.match_it))


class BaseNewSpecificationInformationTypeDefaultTest(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(BaseNewSpecificationInformationTypeDefaultTest, self).setUp()
        set_blueprint_information_type(self, True)
        it_field = soupmatchers.Tag('it-field', True,
                                    attrs=dict(name='field.information_type'))
        self.match_it = soupmatchers.HTMLContains(it_field)

    def makeTarget(self, policy, owner=None):
        raise NotImplementedError('makeTarget')

    def ensurePolicy(self, target, information_type):
        """Helper to call _ensurePolicies

        Useful because we need to follow to product from
        ProductSeries to get to _ensurePolicies.
        """
        if IProduct.providedBy(target):
            removeSecurityProxy(target)._ensurePolicies(information_type)
        elif IProductSeries.providedBy(target):
            removeSecurityProxy(target.product)._ensurePolicies(
                information_type)

    def getSpecification(self, target, name):
        """Helper to get the specification.

        Useful because we need to follow to product from a
        ProductSeries.
        """
        if IProductSeries.providedBy(target):
            return target.product.getSpecification(name)
        return target.getSpecification(name)

    def submitSpec(self, browser):
        """Submit a Specification via a browser."""
        name = self.factory.getUniqueString()
        browser.getControl('Name').value = name
        browser.getControl('Title').value = self.factory.getUniqueString()
        browser.getControl('Summary').value = self.factory.getUniqueString()
        browser.getControl('Register Blueprint').click()
        return name

    def test_public(self):
        """Creating from PUBLIC policy allows only PUBLIC."""
        policy = SpecificationSharingPolicy.PUBLIC
        target = self.makeTarget(policy)
        browser = self.getViewBrowser(target, view_name='+addspec')
        self.assertThat(browser.contents, Not(self.match_it))
        spec = self.getSpecification(target, self.submitSpec(browser))
        self.assertEqual(spec.information_type, InformationType.PUBLIC)

    def test_public_or_proprietary(self):
        """Creating from PUBLIC_OR_PROPRIETARY defaults to PUBLIC."""
        policy = SpecificationSharingPolicy.PUBLIC_OR_PROPRIETARY
        target = self.makeTarget(policy)
        browser = self.getViewBrowser(target, view_name='+addspec')
        self.assertThat(browser.contents, self.match_it)
        spec = self.getSpecification(target, self.submitSpec(browser))
        self.assertEqual(spec.information_type, InformationType.PUBLIC)

    def test_proprietary_or_public(self):
        """Creating from PROPRIETARY_OR_PUBLIC defaults to PROPRIETARY."""
        policy = SpecificationSharingPolicy.PROPRIETARY_OR_PUBLIC
        owner = self.factory.makePerson()
        target = self.makeTarget(policy, owner=owner)
        self.ensurePolicy(target, [InformationType.PROPRIETARY])
        browser = self.getViewBrowser(
            target, view_name='+addspec', user=owner)
        self.assertThat(browser.contents, self.match_it)
        spec = self.getSpecification(target, self.submitSpec(browser))
        self.assertEqual(spec.information_type, InformationType.PROPRIETARY)

    def test_proprietary(self):
        """PROPRIETARY only allows proprietary when creating blueprints."""
        policy = SpecificationSharingPolicy.PROPRIETARY
        owner = self.factory.makePerson()
        target = self.makeTarget(policy, owner=owner)
        self.ensurePolicy(target, [InformationType.PROPRIETARY])
        browser = self.getViewBrowser(
            target, view_name='+addspec', user=owner)
        self.assertThat(browser.contents, Not(self.match_it))
        spec = self.getSpecification(target, self.submitSpec(browser))
        self.assertEqual(spec.information_type, InformationType.PROPRIETARY)

    def test_embargoed_or_proprietary(self):
        """Creating from EMBARGOED_OR_PROPRIETARY defaults to embargoed."""
        policy = SpecificationSharingPolicy.EMBARGOED_OR_PROPRIETARY
        owner = self.factory.makePerson()
        target = self.makeTarget(policy, owner=owner)
        self.ensurePolicy(target, [InformationType.EMBARGOED])
        browser = self.getViewBrowser(
            target, view_name='+addspec', user=owner)
        self.assertThat(browser.contents, self.match_it)
        spec = self.getSpecification(target, self.submitSpec(browser))
        self.assertEqual(spec.information_type, InformationType.EMBARGOED)



class TestNewSpecificationDefaultInformationTypeProduct(
    BaseNewSpecificationInformationTypeDefaultTest):

    def makeTarget(self, policy, owner=None):
        if owner is None:
            owner = self.factory.makePerson()
        return self.factory.makeProduct(
            owner=owner, specification_sharing_policy=policy)


class TestNewSpecificationDefaultInformationTypeProductSeries(
    BaseNewSpecificationInformationTypeDefaultTest):

    def makeTarget(self, policy, owner=None):
        if owner is None:
            owner = self.factory.makePerson()
        product = self.factory.makeProduct(
            owner=owner, specification_sharing_policy=policy)
        return self.factory.makeProductSeries(product=product)


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
