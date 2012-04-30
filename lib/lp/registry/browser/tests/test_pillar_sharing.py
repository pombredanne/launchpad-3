# Copyright 2012 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test views that manage sharing."""

__metaclass__ = type

from BeautifulSoup import BeautifulSoup
from lazr.restful.interfaces import IJSONRequestCache
from lazr.restful.utils import get_current_web_service_request
import simplejson
from testtools.matchers import (
    LessThan,
    MatchesException,
    Not,
    Raises,
    )
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.traversing.browser.absoluteurl import absoluteURL

from lp.app.interfaces.services import IService
from lp.registry.enums import InformationType
from lp.registry.interfaces.accesspolicy import IAccessPolicyGrantFlatSource
from lp.registry.model.pillar import PillarPerson
from lp.services.config import config
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.interfaces import StormRangeFactoryError
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    login_person,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount
from lp.testing.pages import (
    extract_text,
    setupBrowserForUser,
    )
from lp.testing.views import (
    create_initialized_view,
    create_view,
    )


DETAILS_ENABLED_FLAG = {'disclosure.enhanced_sharing_details.enabled': 'true'}
DETAILS_WRITE_FLAG = {
    'disclosure.enhanced_sharing_details.enabled': 'true',
    'disclosure.enhanced_sharing.writable': 'true'}
ENABLED_FLAG = {'disclosure.enhanced_sharing.enabled': 'true'}
WRITE_FLAG = {'disclosure.enhanced_sharing.writable': 'true'}


class PillarSharingDetailsMixin:
    """Test the pillar sharing details view."""

    layer = DatabaseFunctionalLayer

    def _create_sharing(self, grantee, security=False):
            if security:
                owner = self.factory.makePerson()
            else:
                owner = self.pillar.owner
            if self.pillar_type == 'product':
                self.bug = self.factory.makeBug(
                    product=self.pillar,
                    owner=owner,
                    private=True)
                self.branch = self.factory.makeBranch(
                    product=self.pillar,
                    owner=self.pillar.owner,
                    private=True)
            elif self.pillar_type == 'distribution':
                self.branch = None
                self.bug = self.factory.makeBug(
                    distribution=self.pillar,
                    owner=owner,
                    private=True)
            artifact = self.factory.makeAccessArtifact(concrete=self.bug)
            policy = self.factory.makeAccessPolicy(pillar=self.pillar)
            self.factory.makeAccessPolicyArtifact(
                artifact=artifact, policy=policy)
            self.factory.makeAccessArtifactGrant(
                artifact=artifact, grantee=grantee, grantor=self.pillar.owner)

            if self.branch:
                artifact = self.factory.makeAccessArtifact(
                    concrete=self.branch)
                self.factory.makeAccessPolicyArtifact(
                    artifact=artifact, policy=policy)
                self.factory.makeAccessArtifactGrant(
                    artifact=artifact, grantee=grantee,
                    grantor=self.pillar.owner)

    def getPillarPerson(self, person=None, with_sharing=True):
        if person is None:
            person = self.factory.makePerson()
        if with_sharing:
            self._create_sharing(person)

        return PillarPerson(self.pillar, person)

    def test_view_filters_security_wisely(self):
        # There are bugs in the sharingdetails view that not everyone with
        # `launchpad.Driver` -- the permission level for the page -- should be
        # able to see.
        with FeatureFixture(DETAILS_ENABLED_FLAG):
            pillarperson = self.getPillarPerson(with_sharing=False)
            self._create_sharing(grantee=pillarperson.person, security=True)
            view = create_initialized_view(pillarperson, '+index')
            # The page loads
            self.assertEqual(pillarperson.person.displayname, view.page_title)
            # The bug, which is not shared with the owner, is not included.

            self.assertEqual(0, view.shared_bugs_count)

    def test_view_traverses_plus_sharingdetails(self):
        # The traversed url in the app is pillar/+sharing/person
        with FeatureFixture(DETAILS_ENABLED_FLAG):
            # We have to do some fun url hacking to force the traversal a user
            # encounters.
            pillarperson = self.getPillarPerson()
            expected = "Sharing details for %s : Sharing : %s" % (
                    pillarperson.person.displayname,
                    pillarperson.pillar.displayname)
            url = 'http://launchpad.dev/%s/+sharing/%s' % (
                pillarperson.pillar.name, pillarperson.person.name)
            browser = self.getUserBrowser(user=self.owner, url=url)
            self.assertEqual(expected, browser.title)

    def test_no_sharing_message(self):
        # If there is no sharing between pillar and person, a suitable message
        # is displayed.
        with FeatureFixture(DETAILS_ENABLED_FLAG):
            # We have to do some fun url hacking to force the traversal a user
            # encounters.
            pillarperson = self.getPillarPerson(with_sharing=False)
            url = 'http://launchpad.dev/%s/+sharing/%s' % (
                pillarperson.pillar.name, pillarperson.person.name)
            browser = self.getUserBrowser(user=self.owner, url=url)
            self.assertIn(
                'There are no shared bugs or branches.',
                browser.contents)

    def test_init_without_feature_flag(self):
        # We need a feature flag to enable the view.
        pillarperson = self.getPillarPerson()
        self.assertRaises(
            Unauthorized, create_initialized_view, pillarperson, '+index')

    def test_init_with_feature_flag(self):
        # The view works with a feature flag.
        with FeatureFixture(DETAILS_ENABLED_FLAG):
            pillarperson = self.getPillarPerson()
            view = create_initialized_view(pillarperson, '+index')
            self.assertEqual(pillarperson.person.displayname, view.page_title)
            self.assertEqual(1, view.shared_bugs_count)

    def test_view_data_model(self):
        # Test that the json request cache contains the view data model.
        with FeatureFixture(DETAILS_ENABLED_FLAG):
            pillarperson = self.getPillarPerson()
            view = create_initialized_view(pillarperson, '+index')
            cache = IJSONRequestCache(view.request)
            request = get_current_web_service_request()
            self.assertEqual({
                'self_link': absoluteURL(pillarperson.person, request),
                'displayname': pillarperson.person.displayname
            }, cache.objects.get('sharee'))
            self.assertEqual({
                'self_link': absoluteURL(pillarperson.pillar, request),
            }, cache.objects.get('pillar'))
            bugtask = self.bug.default_bugtask
            self.assertEqual({
                'bug_id': self.bug.id,
                'bug_summary': self.bug.title,
                'bug_importance': bugtask.importance.title.lower(),
                'information_type': self.bug.information_type.title,
                'web_link': canonical_url(
                    bugtask, path_only_if_possible=True),
                'self_link': absoluteURL(self.bug, request),
            }, cache.objects.get('bugs')[0])
            if self.pillar_type == 'product':
                self.assertEqual({
                    'branch_id': self.branch.id,
                    'branch_name': self.branch.unique_name,
                    'information_type': InformationType.USERDATA.title,
                    'web_link': canonical_url(
                        self.branch, path_only_if_possible=True),
                    'self_link': absoluteURL(self.branch, request),
                }, cache.objects.get('branches')[0])

    def test_view_write_enabled_without_feature_flag(self):
        # Test that sharing_write_enabled is not set without the feature flag.
        with FeatureFixture(DETAILS_ENABLED_FLAG):
            pillarperson = self.getPillarPerson()
            view = create_initialized_view(pillarperson, '+index')
            cache = IJSONRequestCache(view.request)
            self.assertFalse(cache.objects.get('sharing_write_enabled'))

    def test_view_write_enabled_with_feature_flag(self):
        # Test that sharing_write_enabled is set when required.
        with FeatureFixture(DETAILS_WRITE_FLAG):
            pillarperson = self.getPillarPerson()
            view = create_initialized_view(pillarperson, '+index')
            cache = IJSONRequestCache(view.request)
            self.assertTrue(cache.objects.get('sharing_write_enabled'))


class TestProductSharingDetailsView(
    TestCaseWithFactory, PillarSharingDetailsMixin):

    pillar_type = 'product'

    def setUp(self):
        super(TestProductSharingDetailsView, self).setUp()
        self.owner = self.factory.makePerson()
        self.pillar = self.factory.makeProduct(owner=self.owner)
        login_person(self.owner)


class TestDistributionSharingDetailsView(
    TestCaseWithFactory, PillarSharingDetailsMixin):

    pillar_type = 'distribution'

    def setUp(self):
        super(TestDistributionSharingDetailsView, self).setUp()
        self.owner = self.factory.makePerson()
        self.pillar = self.factory.makeProduct(owner=self.owner)
        login_person(self.owner)


class PillarSharingViewTestMixin:
    """Test the PillarSharingView."""

    layer = DatabaseFunctionalLayer

    def createSharees(self):
        login_person(self.owner)
        self.access_policy = self.factory.makeAccessPolicy(
            pillar=self.pillar,
            type=InformationType.PROPRIETARY)
        self.grantees = []

        def makeGrants(name):
            grantee = self.factory.makePerson(name=name)
            self.grantees.append(grantee)
            # Make access policy grant so that 'All' is returned.
            self.factory.makeAccessPolicyGrant(self.access_policy, grantee)
            # Make access artifact grants so that 'Some' is returned.
            artifact_grant = self.factory.makeAccessArtifactGrant()
            self.factory.makeAccessPolicyArtifact(
                artifact=artifact_grant.abstract_artifact,
                policy=self.access_policy)
        # Make grants for grantees in ascending order so we can slice off the
        # first elements in the pillar observer results to check batching.
        for x in range(10):
            makeGrants('name%s' % x)

    def test_init_without_feature_flag(self):
        # We need a feature flag to enable the view.
        self.assertRaises(
            Unauthorized, create_initialized_view, self.pillar, '+sharing')

    def test_init_with_feature_flag(self):
        # The view works with a feature flag.
        with FeatureFixture(ENABLED_FLAG):
            view = create_initialized_view(self.pillar, '+sharing')
            self.assertEqual('Sharing', view.page_title)

    def test_sharing_menu_without_feature_flag(self):
        url = canonical_url(self.pillar)
        browser = setupBrowserForUser(user=self.driver)
        browser.open(url)
        soup = BeautifulSoup(browser.contents)
        sharing_menu = soup.find('a', {'class': 'menu-link-sharing'})
        self.assertIsNone(sharing_menu)

    def test_sharing_menu_with_feature_flag(self):
        with FeatureFixture(ENABLED_FLAG):
            url = canonical_url(self.pillar)
            browser = setupBrowserForUser(user=self.driver)
            browser.open(url)
            soup = BeautifulSoup(browser.contents)
            sharing_url = canonical_url(self.pillar, view_name='+sharing')
            sharing_menu = soup.find('a', {'href': sharing_url})
            self.assertIsNotNone(sharing_menu)

    def test_picker_config(self):
        # Test the config passed to the disclosure sharing picker.
        with FeatureFixture(ENABLED_FLAG):
            view = create_view(self.pillar, name='+sharing')
            picker_config = simplejson.loads(view.json_sharing_picker_config)
            self.assertTrue('vocabulary_filters' in picker_config)
            self.assertEqual(
                'Grant access to project artifacts',
                picker_config['header'])
            self.assertEqual(
                'Search for user or exclusive team with whom to share',
                picker_config['steptitle'])
            self.assertEqual(
                'NewPillarSharee', picker_config['vocabulary'])

    def test_view_data_model(self):
        # Test that the json request cache contains the view data model.
        with FeatureFixture(ENABLED_FLAG):
            view = create_initialized_view(self.pillar, name='+sharing')
            cache = IJSONRequestCache(view.request)
            self.assertIsNotNone(cache.objects.get('information_types'))
            self.assertIsNotNone(cache.objects.get('sharing_permissions'))
            batch_size = config.launchpad.default_batch_size
            apgfs = getUtility(IAccessPolicyGrantFlatSource)
            sharees = apgfs.findGranteePermissionsByPolicy(
                [self.access_policy], self.grantees[:batch_size])
            sharing_service = getUtility(IService, 'sharing')
            sharee_data = sharing_service.jsonShareeData(sharees)
            self.assertContentEqual(
                sharee_data, cache.objects.get('sharee_data'))

    def test_view_batch_data(self):
        # Test the expected batching data is in the json request cache.
        with FeatureFixture(ENABLED_FLAG):
            view = create_initialized_view(self.pillar, name='+sharing')
            cache = IJSONRequestCache(view.request)
            # Test one expected data value (there are many).
            next_batch = view.sharees().batch.nextBatch()
            self.assertContentEqual(
                next_batch.range_memo, cache.objects.get('next')['memo'])

    def test_view_range_factory(self):
        # Test the view range factory is properly configured.
        with FeatureFixture(ENABLED_FLAG):
            view = create_initialized_view(self.pillar, name='+sharing')
            range_factory = view.sharees().batch.range_factory

            def test_range_factory():
                row = range_factory.resultset.get_plain_result_set()[0]
                range_factory.getOrderValuesFor(row)

            self.assertThat(
                test_range_factory,
                Not(Raises(MatchesException(StormRangeFactoryError))))

    def test_view_query_count(self):
        # Test the query count is within expected limit.
        with FeatureFixture(ENABLED_FLAG):
            view = create_view(self.pillar, name='+sharing')
            with StormStatementRecorder() as recorder:
                view.initialize()
            self.assertThat(recorder, HasQueryCount(LessThan(6)))

    def test_view_write_enabled_without_feature_flag(self):
        # Test that sharing_write_enabled is not set without the feature flag.
        with FeatureFixture(ENABLED_FLAG):
            login_person(self.owner)
            view = create_initialized_view(self.pillar, name='+sharing')
            cache = IJSONRequestCache(view.request)
            self.assertFalse(cache.objects.get('sharing_write_enabled'))

    def test_view_write_enabled_with_feature_flag(self):
        # Test that sharing_write_enabled is set when required.
        with FeatureFixture(WRITE_FLAG):
            view = create_initialized_view(self.pillar, name='+sharing')
            cache = IJSONRequestCache(view.request)
            self.assertFalse(cache.objects.get('sharing_write_enabled'))
            login_person(self.owner)
            view = create_initialized_view(self.pillar, name='+sharing')
            cache = IJSONRequestCache(view.request)
            self.assertTrue(cache.objects.get('sharing_write_enabled'))


class TestProductSharingView(PillarSharingViewTestMixin,
                                 TestCaseWithFactory):
    """Test the PillarSharingView with products."""

    def setUp(self):
        super(TestProductSharingView, self).setUp()
        self.driver = self.factory.makePerson()
        self.owner = self.factory.makePerson()
        self.pillar = self.factory.makeProduct(
            owner=self.owner, driver=self.driver)
        self.createSharees()
        login_person(self.driver)


class TestDistributionSharingView(PillarSharingViewTestMixin,
                                      TestCaseWithFactory):
    """Test the PillarSharingView with distributions."""

    def setUp(self):
        super(TestDistributionSharingView, self).setUp()
        self.driver = self.factory.makePerson()
        self.owner = self.factory.makePerson()
        self.pillar = self.factory.makeDistribution(
            owner=self.owner, driver=self.driver)
        self.createSharees()
        login_person(self.driver)
