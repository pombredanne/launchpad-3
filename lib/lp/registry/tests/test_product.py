# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from cStringIO import StringIO
import datetime

import pytz
from storm.locals import Store
from testtools.matchers import MatchesAll
from testtools.testcase import ExpectedException
import transaction
from zope.component import getUtility
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.security.checker import (
    CheckerPublic,
    getChecker,
    )
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.answers.interfaces.faqtarget import IFAQTarget
from lp.app.enums import (
    FREE_INFORMATION_TYPES,
    InformationType,
    PUBLIC_PROPRIETARY_INFORMATION_TYPES,
    PROPRIETARY_INFORMATION_TYPES,
    ServiceUsage,
    )
from lp.app.errors import ServiceUsageForbidden
from lp.app.interfaces.launchpad import (
    IHasIcon,
    IHasLogo,
    IHasMugshot,
    ILaunchpadCelebrities,
    ILaunchpadUsage,
    IServiceUsage,
    )
from lp.app.interfaces.informationtype import IInformationType
from lp.app.interfaces.services import IService
from lp.bugs.interfaces.bugsummary import IBugSummaryDimension
from lp.bugs.interfaces.bugsupervisor import IHasBugSupervisor
from lp.registry.enums import (
    BranchSharingPolicy,
    BugSharingPolicy,
    EXCLUSIVE_TEAM_POLICY,
    INCLUSIVE_TEAM_POLICY,
    SharingPermission,
    SpecificationSharingPolicy,
    )
from lp.registry.errors import (
    CannotChangeInformationType,
    CommercialSubscribersOnly,
    InclusiveTeamLinkageError,
    )
from lp.registry.interfaces.accesspolicy import (
    IAccessPolicyGrantSource,
    IAccessPolicySource,
    )
from lp.registry.interfaces.oopsreferences import IHasOOPSReferences
from lp.registry.interfaces.product import (
    IProduct,
    IProductSet,
    License,
    )
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.model.product import (
    Product,
    ProductSet,
    UnDeactivateable,
    )
from lp.registry.model.productlicense import ProductLicense
from lp.services.database.lpstorm import IStore
from lp.services.webapp.authorization import check_permission
from lp.testing import (
    celebrity_logged_in,
    login,
    person_logged_in,
    StormStatementRecorder,
    TestCase,
    TestCaseWithFactory,
    WebServiceTestCase,
    )
from lp.testing.event import TestEventListener
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    ZopelessDatabaseLayer,
    )
from lp.testing.matchers import (
    DoesNotSnapshot,
    Provides,
    )
from lp.testing.pages import (
    find_main_content,
    get_feedback_messages,
    setupBrowser,
    )
from lp.translations.enums import TranslationPermission
from lp.translations.interfaces.customlanguagecode import (
    IHasCustomLanguageCodes,
    )


class TestProduct(TestCaseWithFactory):
    """Tests product object."""

    layer = DatabaseFunctionalLayer

    def test_pillar_category(self):
        # Products are really called Projects
        product = self.factory.makeProduct()
        self.assertEqual("Project", product.pillar_category)

    def test_implements_interfaces(self):
        # Product fully implements its interfaces.
        product = removeSecurityProxy(self.factory.makeProduct())
        expected_interfaces = [
            IProduct,
            IBugSummaryDimension,
            IFAQTarget,
            IHasBugSupervisor,
            IHasCustomLanguageCodes,
            IHasIcon,
            IHasLogo,
            IHasMugshot,
            IHasOOPSReferences,
            IInformationType,
            ILaunchpadUsage,
            IServiceUsage,
            ]
        provides_all = MatchesAll(*map(Provides, expected_interfaces))
        self.assertThat(product, provides_all)

    def test_deactivation_failure(self):
        # Ensure that a product cannot be deactivated if
        # it is linked to source packages.
        login('admin@canonical.com')
        product = self.factory.makeProduct()
        source_package = self.factory.makeSourcePackage()
        self.assertEqual(True, product.active)
        source_package.setPackaging(
            product.development_focus, self.factory.makePerson())
        self.assertRaises(
            UnDeactivateable,
            setattr, product, 'active', False)

    def test_deactivation_success(self):
        # Ensure that a product can be deactivated if
        # it is not linked to source packages.
        login('admin@canonical.com')
        product = self.factory.makeProduct()
        self.assertEqual(True, product.active)
        product.active = False
        self.assertEqual(False, product.active)

    def test_milestone_sorting_getMilestonesAndReleases(self):
        product = self.factory.makeProduct()
        series = self.factory.makeProductSeries(product=product)
        milestone_0_1 = self.factory.makeMilestone(
            product=product,
            productseries=series,
            name='0.1')
        milestone_0_2 = self.factory.makeMilestone(
            product=product,
            productseries=series,
            name='0.2')
        release_1 = self.factory.makeProductRelease(
            product=product,
            milestone=milestone_0_1)
        release_2 = self.factory.makeProductRelease(
            product=product,
            milestone=milestone_0_2)
        expected = [(milestone_0_2, release_2), (milestone_0_1, release_1)]
        self.assertEqual(
            expected,
            list(product.getMilestonesAndReleases()))

    def test_getTimeline_limit(self):
        # Only 20 milestones/releases per series should be included in the
        # getTimeline() results. The results are sorted by
        # descending dateexpected and name, so the presumed latest
        # milestones should be included.
        product = self.factory.makeProduct(name='foo')
        for i in range(25):
            self.factory.makeMilestone(
                product=product,
                productseries=product.development_focus,
                name=str(i))

        # 0 through 4 should not be in the list.
        expected_milestones = [
            '/foo/+milestone/24',
            '/foo/+milestone/23',
            '/foo/+milestone/22',
            '/foo/+milestone/21',
            '/foo/+milestone/20',
            '/foo/+milestone/19',
            '/foo/+milestone/18',
            '/foo/+milestone/17',
            '/foo/+milestone/16',
            '/foo/+milestone/15',
            '/foo/+milestone/14',
            '/foo/+milestone/13',
            '/foo/+milestone/12',
            '/foo/+milestone/11',
            '/foo/+milestone/10',
            '/foo/+milestone/9',
            '/foo/+milestone/8',
            '/foo/+milestone/7',
            '/foo/+milestone/6',
            '/foo/+milestone/5',
            ]

        [series] = product.getTimeline()
        timeline_milestones = [
            landmark['uri']
            for landmark in series.landmarks]
        self.assertEqual(
            expected_milestones,
            timeline_milestones)

    def test_getVersionSortedSeries(self):
        # The product series should be sorted with the development focus
        # series first, the series starting with a number in descending
        # order, and then the series starting with a letter in
        # descending order.
        product = self.factory.makeProduct()
        for name in ('1', '2', '3', '3a', '3b', 'alpha', 'beta'):
            self.factory.makeProductSeries(product=product, name=name)
        self.assertEqual(
            [u'trunk', u'3b', u'3a', u'3', u'2', u'1', u'beta', u'alpha'],
            [series.name for series in product.getVersionSortedSeries()])

    def test_getVersionSortedSeries_with_specific_statuses(self):
        # The obsolete series should be included in the results if
        # statuses=[SeriesStatus.OBSOLETE]. The development focus will
        # also be included since it does not get filtered.
        login('admin@canonical.com')
        product = self.factory.makeProduct()
        self.factory.makeProductSeries(
            product=product, name='frozen-series')
        obsolete_series = self.factory.makeProductSeries(
            product=product, name='obsolete-series')
        obsolete_series.status = SeriesStatus.OBSOLETE
        active_series = product.getVersionSortedSeries(
            statuses=[SeriesStatus.OBSOLETE])
        self.assertEqual(
            [u'trunk', u'obsolete-series'],
            [series.name for series in active_series])

    def test_getVersionSortedSeries_without_specific_statuses(self):
        # The obsolete series should not be included in the results if
        # filter_statuses=[SeriesStatus.OBSOLETE]. The development focus will
        # always be included since it does not get filtered.
        login('admin@canonical.com')
        product = self.factory.makeProduct()
        self.factory.makeProductSeries(product=product, name='active-series')
        obsolete_series = self.factory.makeProductSeries(
            product=product, name='obsolete-series')
        obsolete_series.status = SeriesStatus.OBSOLETE
        product.development_focus.status = SeriesStatus.OBSOLETE
        active_series = product.getVersionSortedSeries(
            filter_statuses=[SeriesStatus.OBSOLETE])
        self.assertEqual(
            [u'trunk', u'active-series'],
            [series.name for series in active_series])

    def test_owner_cannot_be_open_team(self):
        """Product owners cannot be open teams."""
        for policy in INCLUSIVE_TEAM_POLICY:
            open_team = self.factory.makeTeam(membership_policy=policy)
            self.assertRaises(
                InclusiveTeamLinkageError, self.factory.makeProduct,
                owner=open_team)

    def test_owner_can_be_closed_team(self):
        """Product owners can be exclusive teams."""
        for policy in EXCLUSIVE_TEAM_POLICY:
            closed_team = self.factory.makeTeam(membership_policy=policy)
            self.factory.makeProduct(owner=closed_team)

    def test_private_bugs_on_not_allowed_for_anonymous(self):
        # Anonymous cannot turn on private bugs.
        product = self.factory.makeProduct()
        self.assertRaises(
            CommercialSubscribersOnly,
            product.checkPrivateBugsTransitionAllowed, True, None)

    def test_private_bugs_off_not_allowed_for_anonymous(self):
        # Anonymous cannot turn private bugs off.
        product = self.factory.makeProduct()
        self.assertRaises(
            Unauthorized,
            product.checkPrivateBugsTransitionAllowed, False, None)

    def test_private_bugs_on_not_allowed_for_unauthorised(self):
        # Unauthorised users cannot turn on private bugs.
        product = self.factory.makeProduct()
        someone = self.factory.makePerson()
        self.assertRaises(
            CommercialSubscribersOnly,
            product.checkPrivateBugsTransitionAllowed, True, someone)

    def test_private_bugs_off_not_allowed_for_unauthorised(self):
        # Unauthorised users cannot turn private bugs off.
        product = self.factory.makeProduct()
        someone = self.factory.makePerson()
        self.assertRaises(
            Unauthorized,
            product.checkPrivateBugsTransitionAllowed, False, someone)

    def test_private_bugs_on_allowed_for_moderators(self):
        # Moderators can turn on private bugs.
        product = self.factory.makeProduct()
        registry_expert = self.factory.makeRegistryExpert()
        product.checkPrivateBugsTransitionAllowed(True, registry_expert)

    def test_private_bugs_off_allowed_for_moderators(self):
        # Moderators can turn private bugs off.
        product = self.factory.makeProduct()
        registry_expert = self.factory.makeRegistryExpert()
        product.checkPrivateBugsTransitionAllowed(False, registry_expert)

    def test_private_bugs_on_allowed_for_commercial_subscribers(self):
        # Commercial subscribers can turn on private bugs.
        bug_supervisor = self.factory.makePerson()
        product = self.factory.makeProduct(bug_supervisor=bug_supervisor)
        self.factory.makeCommercialSubscription(product)
        product.checkPrivateBugsTransitionAllowed(True, bug_supervisor)

    def test_private_bugs_on_not_allowed_for_expired_subscribers(self):
        # Expired Commercial subscribers cannot turn on private bugs.
        bug_supervisor = self.factory.makePerson()
        product = self.factory.makeProduct(bug_supervisor=bug_supervisor)
        self.factory.makeCommercialSubscription(product, expired=True)
        self.assertRaises(
            CommercialSubscribersOnly,
            product.setPrivateBugs, True, bug_supervisor)

    def test_private_bugs_off_allowed_for_bug_supervisors(self):
        # Bug supervisors can turn private bugs off.
        bug_supervisor = self.factory.makePerson()
        product = self.factory.makeProduct(bug_supervisor=bug_supervisor)
        product.checkPrivateBugsTransitionAllowed(False, bug_supervisor)

    def test_unauthorised_set_private_bugs_raises(self):
        # Test Product.setPrivateBugs raises an error if user unauthorised.
        product = self.factory.makeProduct()
        someone = self.factory.makePerson()
        self.assertRaises(
            CommercialSubscribersOnly,
            product.setPrivateBugs, True, someone)

    def test_set_private_bugs(self):
        # Test Product.setPrivateBugs()
        bug_supervisor = self.factory.makePerson()
        product = self.factory.makeProduct(bug_supervisor=bug_supervisor)
        self.factory.makeCommercialSubscription(product)
        product.setPrivateBugs(True, bug_supervisor)
        self.assertTrue(product.private_bugs)

    def test_product_creation_grants_maintainer_access(self):
        # Creating a new product creates an access grant for the maintainer
        # for all default policies.
        owner = self.factory.makePerson()
        product = getUtility(IProductSet).createProduct(
            owner, 'carrot', 'Carrot', 'Carrot', 'testing',
            licenses=[License.MIT])
        policies = getUtility(IAccessPolicySource).findByPillar((product,))
        grants = getUtility(IAccessPolicyGrantSource).findByPolicy(policies)
        expected_grantess = set([product.owner])
        grantees = set([grant.grantee for grant in grants])
        self.assertEqual(expected_grantess, grantees)

    def test_open_product_creation_sharing_policies(self):
        # Creating a new open (non-proprietary) product sets the bug and
        # branch sharing polices to public, and creates policies if required.
        owner = self.factory.makePerson()
        with person_logged_in(owner):
            product = getUtility(IProductSet).createProduct(
                owner, 'carrot', 'Carrot', 'Carrot', 'testing',
                licenses=[License.MIT])
        self.assertEqual(BugSharingPolicy.PUBLIC, product.bug_sharing_policy)
        self.assertEqual(
            BranchSharingPolicy.PUBLIC, product.branch_sharing_policy)
        self.assertEqual(
            SpecificationSharingPolicy.PUBLIC,
            product.specification_sharing_policy)
        aps = getUtility(IAccessPolicySource).findByPillar([product])
        expected = [
            InformationType.USERDATA, InformationType.PRIVATESECURITY]
        self.assertContentEqual(expected, [policy.type for policy in aps])

    def test_proprietary_product_creation_sharing_policies(self):
        # Creating a new proprietary product sets the bug, branch, and
        # specification sharing polices to proprietary.
        owner = self.factory.makePerson()
        with person_logged_in(owner):
            product = getUtility(IProductSet).createProduct(
                owner, 'carrot', 'Carrot', 'Carrot', 'testing',
                licenses=[License.OTHER_PROPRIETARY],
                information_type=InformationType.PROPRIETARY)
            self.assertEqual(
                BugSharingPolicy.PROPRIETARY, product.bug_sharing_policy)
            self.assertEqual(
                BranchSharingPolicy.PROPRIETARY, product.branch_sharing_policy)
            self.assertEqual(
                SpecificationSharingPolicy.PROPRIETARY,
                product.specification_sharing_policy)
        aps = getUtility(IAccessPolicySource).findByPillar([product])
        expected = [InformationType.PROPRIETARY]
        self.assertContentEqual(expected, [policy.type for policy in aps])

    def test_embargoed_product_creation_sharing_policies(self):
        # Creating a new embargoed product sets the branch and
        # specification sharing polices to embargoed or proprietary, and the
        # bug sharing policy to proprietary.
        owner = self.factory.makePerson()
        with person_logged_in(owner):
            product = getUtility(IProductSet).createProduct(
                owner, 'carrot', 'Carrot', 'Carrot', 'testing',
                licenses=[License.OTHER_PROPRIETARY],
                information_type=InformationType.EMBARGOED)
            self.assertEqual(
                BugSharingPolicy.PROPRIETARY,
                product.bug_sharing_policy)
            self.assertEqual(
                BranchSharingPolicy.EMBARGOED_OR_PROPRIETARY,
                product.branch_sharing_policy)
            self.assertEqual(
                SpecificationSharingPolicy.EMBARGOED_OR_PROPRIETARY,
                product.specification_sharing_policy)
        aps = getUtility(IAccessPolicySource).findByPillar([product])
        expected = [InformationType.PROPRIETARY, InformationType.EMBARGOED]
        self.assertContentEqual(expected, [policy.type for policy in aps])

    def test_other_proprietary_product_creation_sharing_policies(self):
        # Creating a new product with other/proprietary license leaves bug
        # and branch sharing polices at their default.
        owner = self.factory.makePerson()
        with person_logged_in(owner):
            product = getUtility(IProductSet).createProduct(
                owner, 'carrot', 'Carrot', 'Carrot', 'testing',
                licenses=[License.OTHER_PROPRIETARY])
            self.assertEqual(
                BugSharingPolicy.PUBLIC, product.bug_sharing_policy)
            self.assertEqual(
                BranchSharingPolicy.PUBLIC, product.branch_sharing_policy)
        aps = getUtility(IAccessPolicySource).findByPillar([product])
        expected = [InformationType.USERDATA, InformationType.PRIVATESECURITY]
        self.assertContentEqual(expected, [policy.type for policy in aps])

    def createProduct(self, information_type=None, license=None):
        # convenience method for testing IProductSet.createProduct rather than
        # self.factory.makeProduct
        owner = self.factory.makePerson()
        kwargs = {}
        if information_type is not None:
            kwargs['information_type'] = information_type
        if license is not None:
            kwargs['licenses'] = [license]
        with person_logged_in(owner):
            return getUtility(IProductSet).createProduct(
                owner, self.factory.getUniqueString('product'),
                'Fnord', 'Fnord', 'test 1', 'test 2', **kwargs)

    def test_product_information_type(self):
        # Product is created with specified information_type
        product = self.createProduct(
            information_type=InformationType.EMBARGOED,
            license=License.OTHER_PROPRIETARY)
        self.assertEqual(InformationType.EMBARGOED, product.information_type)
        # Owner can set information_type
        with person_logged_in(removeSecurityProxy(product).owner):
            product.information_type = InformationType.PROPRIETARY
        self.assertEqual(InformationType.PROPRIETARY, product.information_type)
        # Database persists information_type value
        store = Store.of(product)
        store.flush()
        store.reset()
        product = store.get(Product, product.id)
        self.assertEqual(InformationType.PROPRIETARY, product.information_type)

    def test_product_information_type_default(self):
        # Default information_type is PUBLIC
        owner = self.factory.makePerson()
        product = getUtility(IProductSet).createProduct(
            owner, 'fnord', 'Fnord', 'Fnord', 'test 1', 'test 2')
        self.assertEqual(InformationType.PUBLIC, product.information_type)

    invalid_information_types = [info_type for info_type in
            InformationType.items if info_type not in
            PUBLIC_PROPRIETARY_INFORMATION_TYPES]

    def test_product_information_type_init_invalid_values(self):
        # Cannot create Product.information_type with invalid values.
        for info_type in self.invalid_information_types:
            with ExpectedException(
                CannotChangeInformationType, 'Not supported for Projects.'):
                self.createProduct(information_type=info_type)

    def test_product_information_type_set_invalid_values(self):
        # Cannot set Product.information_type to invalid values.
        product = self.factory.makeProduct()
        for info_type in self.invalid_information_types:
            with ExpectedException(
                CannotChangeInformationType, 'Not supported for Projects.'):
                with person_logged_in(product.owner):
                    product.information_type = info_type

    def test_product_information_set_proprietary_requires_commercial(self):
        # Cannot set Product.information_type to proprietary values if no
        # commercial subscription.
        product = self.factory.makeProduct()
        self.useContext(person_logged_in(product.owner))
        for info_type in PROPRIETARY_INFORMATION_TYPES:
            with ExpectedException(
                CommercialSubscribersOnly,
                'A valid commercial subscription is required for private'
                ' Projects.'):
                product.information_type = info_type
        product.redeemSubscriptionVoucher(
            'hello', product.owner, product.owner, 1)
        for info_type in PROPRIETARY_INFORMATION_TYPES:
            product.information_type = info_type

    def test_product_information_init_proprietary_requires_commercial(self):
        # Cannot create a product with proprietary types without specifying
        # Other/Proprietary license.
        for info_type in PROPRIETARY_INFORMATION_TYPES:
            with ExpectedException(
                CommercialSubscribersOnly,
                'A valid commercial subscription is required for private'
                ' Projects.'):
                self.createProduct(info_type)
        for info_type in PROPRIETARY_INFORMATION_TYPES:
            product = self.createProduct(info_type, License.OTHER_PROPRIETARY)
            self.assertEqual(info_type, product.information_type)

    def test_no_answers_for_proprietary(self):
        # Enabling Answers is forbidden while information_type is proprietary.
        for info_type in PROPRIETARY_INFORMATION_TYPES:
            product = self.factory.makeProduct(information_type=info_type)
            with person_logged_in(removeSecurityProxy(product).owner):
                self.assertEqual(ServiceUsage.UNKNOWN, product.answers_usage)
                for usage in ServiceUsage.items:
                    if usage == ServiceUsage.LAUNCHPAD:
                        with ExpectedException(
                            ServiceUsageForbidden,
                            "Answers not allowed for non-public projects."):
                            product.answers_usage = ServiceUsage.LAUNCHPAD
                    else:
                        # all other values are permitted.
                        product.answers_usage = usage

    def test_answers_for_public(self):
        # Enabling answers is permitted while information_type is PUBLIC
        product = self.factory.makeProduct(
            information_type=InformationType.PUBLIC)
        self.assertEqual(ServiceUsage.UNKNOWN, product.answers_usage)
        with person_logged_in(product.owner):
            for usage in ServiceUsage.items:
                # all values are permitted.
                product.answers_usage = usage

    def test_no_proprietary_if_answers(self):
        # Information type cannot be set to proprietary while Answers are
        # enabled.
        product = self.factory.makeProduct(
            licenses=[License.OTHER_PROPRIETARY])
        with person_logged_in(product.owner):
            product.answers_usage = ServiceUsage.LAUNCHPAD
            with ExpectedException(
                CannotChangeInformationType, 'Answers is enabled.'):
                product.information_type = InformationType.PROPRIETARY

    def check_permissions(self, expected_permissions, used_permissions,
                          type_):
        expected = set(expected_permissions.keys())
        self.assertEqual(
            expected, set(used_permissions.values()),
            'Unexpected %s permissions' % type_)
        for permission in expected_permissions:
            attribute_names = set(
                name for name, value in used_permissions.items()
                if value == permission)
            self.assertEqual(
                expected_permissions[permission], attribute_names,
                'Unexpected set of attributes with %s permission %s:\n'
                'Defined but not expected: %s\n'
                'Expected but not defined: %s'
                % (
                    type_, permission,
                    sorted(
                        attribute_names - expected_permissions[permission]),
                    sorted(
                        expected_permissions[permission] - attribute_names)))

    expected_get_permissions = {
        CheckerPublic: set((
            'active', 'id', 'information_type', 'pillar_category', 'private',
            'userCanView',)),
        'launchpad.View': set((
            '_getOfficialTagClause', '_all_specifications',
            '_valid_specifications', 'active_or_packaged_series',
            'aliases', 'all_milestones',
            'allowsTranslationEdits', 'allowsTranslationSuggestions',
            'announce', 'answer_contacts', 'answers_usage', 'autoupdate',
            'blueprints_usage', 'branch_sharing_policy',
            'bug_reported_acknowledgement', 'bug_reporting_guidelines',
            'bug_sharing_policy', 'bug_subscriptions', 'bug_supervisor',
            'bug_tracking_usage', 'bugtargetdisplayname', 'bugtargetname',
            'bugtracker', 'canUserAlterAnswerContact',
            'checkPrivateBugsTransitionAllowed', 'codehosting_usage',
            'coming_sprints', 'commercial_subscription',
            'commercial_subscription_is_due', 'createBug',
            'createCustomLanguageCode', 'custom_language_codes',
            'date_next_suggest_packaging', 'datecreated', 'description',
            'development_focus', 'development_focusID',
            'direct_answer_contacts', 'displayname', 'distrosourcepackages',
            'downloadurl', 'driver', 'drivers', 'enable_bug_expiration',
            'enable_bugfiling_duplicate_search', 'findReferencedOOPS',
            'findSimilarFAQs', 'findSimilarQuestions', 'freshmeatproject',
            'getAllowedBugInformationTypes',
            'getAllowedSpecificationInformationTypes', 'getAnnouncement',
            'getAnnouncements', 'getAnswerContactsForLanguage',
            'getAnswerContactRecipients', 'getBaseBranchVisibilityRule',
            'getBranchVisibilityRuleForBranch',
            'getBranchVisibilityRuleForTeam',
            'getBranchVisibilityTeamPolicies', 'getBranches',
            'getBugSummaryContextWhereClause', 'getBugTaskWeightFunction',
            'getCustomLanguageCode', 'getDefaultBugInformationType',
            'getDefaultSpecificationInformationType',
            'getEffectiveTranslationPermission', 'getExternalBugTracker',
            'getFAQ', 'getFirstEntryToImport', 'getLinkedBugWatches',
            'getMergeProposals', 'getMilestone', 'getMilestonesAndReleases',
            'getQuestion', 'getQuestionLanguages', 'getPackage', 'getRelease',
            'getSeries', 'getSpecification', 'getSubscription',
            'getSubscriptions', 'getSupportedLanguages', 'getTimeline',
            'getTopContributors', 'getTopContributorsGroupedByCategory',
            'getTranslationGroups', 'getTranslationImportQueueEntries',
            'getTranslators', 'getUsedBugTagsWithOpenCounts',
            'getVersionSortedSeries',
            'has_current_commercial_subscription',
            'has_custom_language_codes', 'has_milestones', 'homepage_content',
            'homepageurl', 'icon', 'invitesTranslationEdits',
            'invitesTranslationSuggestions',
            'isUsingInheritedBranchVisibilityPolicy',
            'license_info', 'license_status', 'licenses', 'logo', 'milestones',
            'mugshot', 'name', 'name_with_project', 'newCodeImport',
            'obsolete_translatable_series', 'official_answers',
            'official_anything', 'official_blueprints', 'official_bug_tags',
            'official_codehosting', 'official_malone', 'owner',
            'parent_subscription_target', 'packagedInDistros', 'packagings',
            'past_sprints', 'personHasDriverRights', 'pillar',
            'primary_translatable', 'private_bugs',
            'programminglang', 'project', 'qualifies_for_free_hosting',
            'recipes', 'redeemSubscriptionVoucher', 'registrant', 'releases',
            'remote_product', 'removeCustomLanguageCode',
            'removeTeamFromBranchVisibilityPolicy', 'screenshotsurl',
            'searchFAQs', 'searchQuestions', 'searchTasks', 'security_contact',
            'series', 'setBranchVisibilityTeamPolicy', 'setPrivateBugs',
            'sharesTranslationsWithOtherSide', 'sourceforgeproject',
            'sourcepackages', 'specification_sharing_policy', 'specifications',
            'sprints', 'summary', 'target_type_display', 'title',
            'translatable_packages', 'translatable_series',
            'translation_focus', 'translationgroup', 'translationgroups',
            'translationpermission', 'translations_usage', 'ubuntu_packages',
            'userCanAlterBugSubscription', 'userCanAlterSubscription',
            'userCanEdit', 'userHasBugSubscriptions', 'uses_launchpad',
            'wikiurl')),
        'launchpad.AnyAllowedPerson': set((
            'addAnswerContact', 'addBugSubscription',
            'addBugSubscriptionFilter', 'addSubscription',
            'createQuestionFromBug', 'newQuestion', 'removeAnswerContact',
            'removeBugSubscription')),
        'launchpad.Append': set(('newFAQ', )),
        'launchpad.Driver': set(('newSeries', )),
        'launchpad.Edit': set((
            'addOfficialBugTag', 'removeOfficialBugTag',
            'setBranchSharingPolicy', 'setBugSharingPolicy',
            'setSpecificationSharingPolicy')),
        'launchpad.Moderate': set((
            'is_permitted', 'license_approved', 'project_reviewed',
            'reviewer_whiteboard', 'setAliases')),
        }

    def test_get_permissions(self):
        product = self.factory.makeProduct()
        checker = getChecker(product)
        self.check_permissions(
            self.expected_get_permissions, checker.get_permissions, 'get')

    def test_set_permissions(self):
        expected_set_permissions = {
            'launchpad.BugSupervisor': set((
                'bug_reported_acknowledgement', 'bug_reporting_guidelines',
                'bugtracker', 'enable_bug_expiration',
                'enable_bugfiling_duplicate_search', 'official_bug_tags',
                'official_malone', 'remote_product')),
            'launchpad.Edit': set((
                'answers_usage', 'blueprints_usage', 'bug_supervisor',
                'bug_tracking_usage', 'codehosting_usage',
                'commercial_subscription', 'description', 'development_focus',
                'displayname', 'downloadurl', 'driver', 'freshmeatproject',
                'homepage_content', 'homepageurl', 'icon', 'information_type',
                'license_info', 'licenses', 'logo', 'mugshot',
                'official_answers', 'official_blueprints',
                'official_codehosting', 'owner', 'private',
                'programminglang', 'project', 'redeemSubscriptionVoucher',
                'releaseroot', 'screenshotsurl', 'sourceforgeproject',
                'summary', 'title', 'uses_launchpad', 'wikiurl')),
            'launchpad.Moderate': set((
                'active', 'autoupdate', 'license_approved', 'name',
                'project_reviewed', 'registrant', 'reviewer_whiteboard')),
            'launchpad.TranslationsAdmin': set((
                'translation_focus', 'translationgroup',
                'translationpermission', 'translations_usage')),
            'launchpad.AnyAllowedPerson': set((
                'date_next_suggest_packaging', )),
            }
        product = self.factory.makeProduct()
        checker = getChecker(product)
        self.check_permissions(
            expected_set_permissions, checker.set_permissions, 'set')

    def test_access_launchpad_View_public_product(self):
        # Everybody, including anonymous users, has access to
        # properties of public products that require the permission
        # launchpad.View
        product = self.factory.makeProduct()
        names = self.expected_get_permissions['launchpad.View']
        with person_logged_in(None):
            for attribute_name in names:
                getattr(product, attribute_name)
        ordinary_user = self.factory.makePerson()
        with person_logged_in(ordinary_user):
            for attribute_name in names:
                getattr(product, attribute_name)
        with person_logged_in(product.owner):
            for attribute_name in names:
                getattr(product, attribute_name)

    def test_access_launchpad_View_proprietary_product(self):
        # Only people with grants for a private product can access
        # attributes protected by the permission launchpad.View.
        product = self.createProduct(
            information_type=InformationType.PROPRIETARY,
            license=License.OTHER_PROPRIETARY)
        owner = removeSecurityProxy(product).owner
        names = self.expected_get_permissions['launchpad.View']
        with person_logged_in(None):
            for attribute_name in names:
                self.assertRaises(
                    Unauthorized, getattr, product, attribute_name)
        ordinary_user = self.factory.makePerson()
        with person_logged_in(ordinary_user):
            for attribute_name in names:
                self.assertRaises(
                    Unauthorized, getattr, product, attribute_name)
        with person_logged_in(owner):
            for attribute_name in names:
                getattr(product, attribute_name)
        # A user with a policy grant for the product can access attributes
        # of a private product.
        with person_logged_in(owner):
            getUtility(IService, 'sharing').sharePillarInformation(
                product, ordinary_user, owner,
                {InformationType.PROPRIETARY: SharingPermission.ALL})
        with person_logged_in(ordinary_user):
            for attribute_name in names:
                getattr(product, attribute_name)

    def test_admin_launchpad_View_proprietary_product(self):
        # Admins and commercial admins can view proprietary products.
        product = self.factory.makeProduct(
            information_type=InformationType.PROPRIETARY)
        names = self.expected_get_permissions['launchpad.View']
        with person_logged_in(self.factory.makeAdministrator()):
            for attribute_name in names:
                getattr(product, attribute_name)
        with person_logged_in(self.factory.makeCommercialAdmin()):
            for attribute_name in names:
                getattr(product, attribute_name)

    def test_access_launchpad_AnyAllowedPerson_public_product(self):
        # Only logged in persons have access to properties of public products
        # that require the permission launchpad.AnyAllowedPerson.
        product = self.factory.makeProduct()
        names = self.expected_get_permissions['launchpad.AnyAllowedPerson']
        with person_logged_in(None):
            for attribute_name in names:
                self.assertRaises(
                    Unauthorized, getattr, product, attribute_name)
        ordinary_user = self.factory.makePerson()
        with person_logged_in(ordinary_user):
            for attribute_name in names:
                getattr(product, attribute_name)
        with person_logged_in(product.owner):
            for attribute_name in names:
                getattr(product, attribute_name)

    def test_access_launchpad_AnyAllowedPerson_proprietary_product(self):
        # Only people with grants for a private product can access
        # attributes protected by the permission launchpad.AnyAllowedPerson.
        product = self.createProduct(
            information_type=InformationType.PROPRIETARY,
            license=License.OTHER_PROPRIETARY)
        owner = removeSecurityProxy(product).owner
        names = self.expected_get_permissions['launchpad.AnyAllowedPerson']
        with person_logged_in(None):
            for attribute_name in names:
                self.assertRaises(
                    Unauthorized, getattr, product, attribute_name)
        ordinary_user = self.factory.makePerson()
        with person_logged_in(ordinary_user):
            for attribute_name in names:
                self.assertRaises(
                    Unauthorized, getattr, product, attribute_name)
        with person_logged_in(owner):
            for attribute_name in names:
                getattr(product, attribute_name)
        # A user with a policy grant for the product can access attributes
        # of a private product.
        with person_logged_in(owner):
            getUtility(IService, 'sharing').sharePillarInformation(
                product, ordinary_user, owner,
                {InformationType.PROPRIETARY: SharingPermission.ALL})
        with person_logged_in(ordinary_user):
            for attribute_name in names:
                getattr(product, attribute_name)

    def test_set_launchpad_AnyAllowedPerson_public_product(self):
        # Only logged in users can set attributes protected by the
        # permission launchpad.AnyAllowedPerson.
        product = self.factory.makeProduct()
        with person_logged_in(None):
            self.assertRaises(
                Unauthorized, setattr, product, 'date_next_suggest_packaging',
                'foo')
        ordinary_user = self.factory.makePerson()
        with person_logged_in(ordinary_user):
            setattr(product, 'date_next_suggest_packaging', 'foo')
        with person_logged_in(product.owner):
            setattr(product, 'date_next_suggest_packaging', 'foo')

    def test_set_launchpad_AnyAllowedPerson_proprietary_product(self):
        # Only people with grants for a private product can set
        # attributes protected by the permission launchpad.AnyAllowedPerson.
        product = self.createProduct(
            information_type=InformationType.PROPRIETARY,
            license=License.OTHER_PROPRIETARY)
        owner = removeSecurityProxy(product).owner
        with person_logged_in(None):
            self.assertRaises(
                Unauthorized, setattr, product, 'date_next_suggest_packaging',
                'foo')
        ordinary_user = self.factory.makePerson()
        with person_logged_in(ordinary_user):
            self.assertRaises(
                Unauthorized, setattr, product, 'date_next_suggest_packaging',
                'foo')
        with person_logged_in(owner):
            setattr(product, 'date_next_suggest_packaging', 'foo')
        # A user with a policy grant for the product can access attributes
        # of a private product.
        with person_logged_in(owner):
            getUtility(IService, 'sharing').sharePillarInformation(
                product, ordinary_user, owner,
                {InformationType.PROPRIETARY: SharingPermission.ALL})
        with person_logged_in(ordinary_user):
            setattr(product, 'date_next_suggest_packaging', 'foo')

    def test_userCanView_caches_known_users(self):
        # userCanView() maintains a cache of users known to have the
        # permission to access a product.
        product = self.createProduct(
            information_type=InformationType.PROPRIETARY,
            license=License.OTHER_PROPRIETARY)
        owner = removeSecurityProxy(product).owner
        user = self.factory.makePerson()
        with person_logged_in(owner):
            getUtility(IService, 'sharing').sharePillarInformation(
                product, user, owner,
                {InformationType.PROPRIETARY: SharingPermission.ALL})
        with person_logged_in(user):
            with StormStatementRecorder() as recorder:
                # The first access to a property of the product from
                # a user requires a DB query.
                product.homepageurl
                queries_for_first_user_access = len(recorder.queries)
                # The second access does not require another query.
                product.description
                self.assertEqual(
                queries_for_first_user_access, len(recorder.queries))


class TestProductBugInformationTypes(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def makeProductWithPolicy(self, bug_sharing_policy, private_bugs=False):
        product = self.factory.makeProduct(private_bugs=private_bugs)
        self.factory.makeCommercialSubscription(product=product)
        with person_logged_in(product.owner):
            product.setBugSharingPolicy(bug_sharing_policy)
        return product

    def test_no_policy(self):
        # New projects can only use the non-proprietary information
        # types.
        product = self.factory.makeProduct()
        self.assertContentEqual(
            FREE_INFORMATION_TYPES, product.getAllowedBugInformationTypes())
        self.assertEqual(
            InformationType.PUBLIC, product.getDefaultBugInformationType())

    def test_legacy_private_bugs(self):
        # The deprecated private_bugs attribute overrides the default
        # information type to USERDATA.
        product = self.factory.makeLegacyProduct(private_bugs=True)
        self.assertContentEqual(
            FREE_INFORMATION_TYPES, product.getAllowedBugInformationTypes())
        self.assertEqual(
            InformationType.USERDATA, product.getDefaultBugInformationType())

    def test_sharing_policy_overrides_private_bugs(self):
        # bug_sharing_policy overrides private_bugs.
        product = self.makeProductWithPolicy(
            BugSharingPolicy.PUBLIC, private_bugs=True)
        self.assertContentEqual(
            FREE_INFORMATION_TYPES, product.getAllowedBugInformationTypes())
        self.assertEqual(
            InformationType.PUBLIC, product.getDefaultBugInformationType())

    def test_sharing_policy_public_or_proprietary(self):
        # bug_sharing_policy can enable Proprietary.
        product = self.makeProductWithPolicy(
            BugSharingPolicy.PUBLIC_OR_PROPRIETARY)
        self.assertContentEqual(
            FREE_INFORMATION_TYPES + (InformationType.PROPRIETARY,),
            product.getAllowedBugInformationTypes())
        self.assertEqual(
            InformationType.PUBLIC,
            product.getDefaultBugInformationType())

    def test_sharing_policy_proprietary_or_public(self):
        # bug_sharing_policy can enable and default to Proprietary.
        product = self.makeProductWithPolicy(
            BugSharingPolicy.PROPRIETARY_OR_PUBLIC)
        self.assertContentEqual(
            FREE_INFORMATION_TYPES + (InformationType.PROPRIETARY,),
            product.getAllowedBugInformationTypes())
        self.assertEqual(
            InformationType.PROPRIETARY,
            product.getDefaultBugInformationType())

    def test_sharing_policy_proprietary(self):
        # bug_sharing_policy can enable only Proprietary.
        product = self.makeProductWithPolicy(BugSharingPolicy.PROPRIETARY)
        self.assertContentEqual(
            [InformationType.PROPRIETARY],
            product.getAllowedBugInformationTypes())
        self.assertEqual(
            InformationType.PROPRIETARY,
            product.getDefaultBugInformationType())


class TestProductSpecificationPolicyAndInformationTypes(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def makeProductWithPolicy(self, specification_sharing_policy):
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product=product)
        with person_logged_in(product.owner):
            product.setSpecificationSharingPolicy(
                specification_sharing_policy)
        return product

    def test_no_policy(self):
        # Projects that have not specified a policy can use the PUBLIC
        # information type.
        product = self.factory.makeProduct()
        self.assertContentEqual(
            [InformationType.PUBLIC],
            product.getAllowedSpecificationInformationTypes())
        self.assertEqual(
            InformationType.PUBLIC,
            product.getDefaultSpecificationInformationType())

    def test_sharing_policy_public(self):
        # Projects with a purely public policy should use PUBLIC
        # information type.
        product = self.makeProductWithPolicy(
            SpecificationSharingPolicy.PUBLIC)
        self.assertContentEqual(
            [InformationType.PUBLIC],
            product.getAllowedSpecificationInformationTypes())
        self.assertEqual(
            InformationType.PUBLIC,
            product.getDefaultSpecificationInformationType())

    def test_sharing_policy_public_or_proprietary(self):
        # specification_sharing_policy can enable Proprietary.
        product = self.makeProductWithPolicy(
            SpecificationSharingPolicy.PUBLIC_OR_PROPRIETARY)
        self.assertContentEqual(
            [InformationType.PUBLIC, InformationType.PROPRIETARY],
            product.getAllowedSpecificationInformationTypes())
        self.assertEqual(
            InformationType.PUBLIC,
            product.getDefaultSpecificationInformationType())

    def test_sharing_policy_proprietary_or_public(self):
        # specification_sharing_policy can enable and default to Proprietary.
        product = self.makeProductWithPolicy(
            SpecificationSharingPolicy.PROPRIETARY_OR_PUBLIC)
        self.assertContentEqual(
            [InformationType.PUBLIC, InformationType.PROPRIETARY],
            product.getAllowedSpecificationInformationTypes())
        self.assertEqual(
            InformationType.PROPRIETARY,
            product.getDefaultSpecificationInformationType())

    def test_sharing_policy_proprietary(self):
        # specification_sharing_policy can enable only Proprietary.
        product = self.makeProductWithPolicy(
            SpecificationSharingPolicy.PROPRIETARY)
        self.assertContentEqual(
            [InformationType.PROPRIETARY],
            product.getAllowedSpecificationInformationTypes())
        self.assertEqual(
            InformationType.PROPRIETARY,
            product.getDefaultSpecificationInformationType())

    def test_sharing_policy_embargoed_or_proprietary(self):
        # specification_sharing_policy can be embargoed and then proprietary.
        product = self.makeProductWithPolicy(
            SpecificationSharingPolicy.EMBARGOED_OR_PROPRIETARY)
        self.assertContentEqual(
            [InformationType.PROPRIETARY, InformationType.EMBARGOED],
            product.getAllowedSpecificationInformationTypes())
        self.assertEqual(
            InformationType.EMBARGOED,
            product.getDefaultSpecificationInformationType())


class ProductPermissionTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_owner_can_edit(self):
        product = self.factory.makeProduct()
        with person_logged_in(product.owner):
            self.assertTrue(check_permission('launchpad.Edit', product))

    def test_commercial_admin_cannot_edit_non_commercial(self):
        product = self.factory.makeProduct()
        with celebrity_logged_in('commercial_admin'):
            self.assertFalse(check_permission('launchpad.Edit', product))

    def test_commercial_admin_can_edit_commercial(self):
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product)
        with celebrity_logged_in('commercial_admin'):
            self.assertTrue(check_permission('launchpad.Edit', product))

    def test_owner_can_driver(self):
        product = self.factory.makeProduct()
        with person_logged_in(product.owner):
            self.assertTrue(check_permission('launchpad.Driver', product))

    def test_driver_can_driver(self):
        product = self.factory.makeProduct()
        driver = self.factory.makePerson()
        with person_logged_in(product.owner):
            product.driver = driver
        with person_logged_in(driver):
            self.assertTrue(check_permission('launchpad.Driver', product))

    def test_commercial_admin_cannot_drive_non_commercial(self):
        product = self.factory.makeProduct()
        with celebrity_logged_in('commercial_admin'):
            self.assertFalse(check_permission('launchpad.Driver', product))

    def test_commercial_admin_can_drive_commercial(self):
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product)
        with celebrity_logged_in('commercial_admin'):
            self.assertTrue(check_permission('launchpad.Driver', product))


class TestProductFiles(TestCase):
    """Tests for downloadable product files."""

    layer = LaunchpadFunctionalLayer

    def test_adddownloadfile_nonascii_filename(self):
        """Test uploading a file with a non-ascii char in the filename."""
        firefox_owner = setupBrowser(auth='Basic mark@example.com:test')
        filename = u'foo\xa5.txt'.encode('utf-8')
        firefox_owner.open(
            'http://launchpad.dev/firefox/1.0/1.0.0/+adddownloadfile')
        foo_file = StringIO('Foo installer package...')
        foo_signature = StringIO('Dummy GPG signature for the Foo installer')
        firefox_owner.getControl(name='field.filecontent').add_file(
            foo_file, 'text/plain', filename)
        firefox_owner.getControl(name='field.signature').add_file(
            foo_signature, 'text/plain', '%s.asc' % filename)
        firefox_owner.getControl('Description').value = "Foo installer"
        firefox_owner.getControl(name="field.contenttype").displayValue = \
           ["Installer file"]
        firefox_owner.getControl("Upload").click()
        self.assertEqual(
            get_feedback_messages(firefox_owner.contents),
            [u"Your file 'foo\xa5.txt' has been uploaded."])
        firefox_owner.open('http://launchpad.dev/firefox/+download')
        content = find_main_content(firefox_owner.contents)
        rows = content.findAll('tr')

        a_list = rows[-1].findAll('a')
        # 1st row
        a_element = a_list[0]
        self.assertEqual(
            a_element['href'],
            'http://launchpad.dev/firefox/1.0/1.0.0/+download/foo%C2%A5.txt')
        self.assertEqual(a_element.contents[0].strip(), u'foo\xa5.txt')
        # 2nd row
        a_element = a_list[1]
        self.assertEqual(
            a_element['href'],
            'http://launchpad.dev/firefox/1.0/1.0.0/+download/'
            'foo%C2%A5.txt/+md5')
        self.assertEqual(a_element.contents[0].strip(), u'md5')
        # 3rd row
        a_element = a_list[2]
        self.assertEqual(
            a_element['href'],
            'http://launchpad.dev/firefox/1.0/1.0.0/+download/'
            'foo%C2%A5.txt.asc')
        self.assertEqual(a_element.contents[0].strip(), u'sig')


class ProductAttributeCacheTestCase(TestCaseWithFactory):
    """Cached attributes must be cleared at the end of a transaction."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(ProductAttributeCacheTestCase, self).setUp()
        self.product = Product.selectOneBy(name='tomcat')

    def testLicensesCache(self):
        """License cache should be cleared automatically."""
        self.assertEqual(self.product.licenses,
                         (License.ACADEMIC, License.AFFERO))
        ProductLicense(product=self.product, license=License.PYTHON)
        # Cache doesn't see new value.
        self.assertEqual(self.product.licenses,
                         (License.ACADEMIC, License.AFFERO))
        self.product.licenses = (License.PERL, License.PHP)
        self.assertEqual(self.product.licenses,
                         (License.PERL, License.PHP))
        # Cache is cleared and it sees database changes that occur
        # before the cache is populated.
        transaction.abort()
        ProductLicense(product=self.product, license=License.MIT)
        self.assertEqual(self.product.licenses,
                         (License.ACADEMIC, License.AFFERO, License.MIT))

    def testCommercialSubscriptionCache(self):
        """commercial_subscription cache should not traverse transactions."""
        self.assertEqual(self.product.commercial_subscription, None)
        self.factory.makeCommercialSubscription(self.product)
        self.assertEqual(self.product.commercial_subscription, None)
        self.product.redeemSubscriptionVoucher(
            'hello', self.product.owner, self.product.owner, 1)
        self.assertEqual(
            'hello', self.product.commercial_subscription.sales_system_id)
        transaction.abort()
        # Cache is cleared.
        self.assertIs(None, self.product.commercial_subscription)

        # Cache is cleared again.
        transaction.abort()
        self.factory.makeCommercialSubscription(self.product)
        # Cache is cleared and it sees database changes that occur
        # before the cache is populated.
        self.assertEqual(
            'new', self.product.commercial_subscription.sales_system_id)


class ProductLicensingTestCase(TestCaseWithFactory):
    """Test the rules of licences and commercial subscriptions."""

    layer = DatabaseFunctionalLayer
    event_listener = None

    def setup_event_listener(self):
        self.events = []
        if self.event_listener is None:
            self.event_listener = TestEventListener(
                IProduct, IObjectModifiedEvent, self.on_event)
        else:
            self.event_listener._active = True
        self.addCleanup(self.event_listener.unregister)

    def on_event(self, thing, event):
        self.events.append(event)

    def test_getLicenses(self):
        # License are assigned a list, but return a tuple.
        product = self.factory.makeProduct(
            licenses=[License.GNU_GPL_V2, License.MIT])
        self.assertEqual((License.GNU_GPL_V2, License.MIT), product.licenses)

    def test_setLicense_handles_no_change(self):
        # The project_reviewed property is not reset, if the new licences
        # are identical to the current licences.
        product = self.factory.makeProduct(licenses=[License.MIT])
        with celebrity_logged_in('registry_experts'):
            product.project_reviewed = True
        self.setup_event_listener()
        with person_logged_in(product.owner):
            product.licenses = [License.MIT]
        with celebrity_logged_in('registry_experts'):
            self.assertIs(True, product.project_reviewed)
        self.assertEqual([], self.events)

    def test_setLicense(self):
        # The project_reviewed property is not reset, if the new licences
        # are identical to the current licences.
        product = self.factory.makeProduct()
        self.setup_event_listener()
        with person_logged_in(product.owner):
            product.licenses = [License.MIT]
        self.assertEqual((License.MIT, ), product.licenses)
        self.assertEqual(1, len(self.events))
        self.assertEqual(product, self.events[0].object)

    def test_setLicense_also_sets_reviewed(self):
        # The project_reviewed attribute it set to False if the licenses
        # change.
        product = self.factory.makeProduct(licenses=[License.MIT])
        with celebrity_logged_in('registry_experts'):
            product.project_reviewed = True
        with person_logged_in(product.owner):
            product.licenses = [License.GNU_GPL_V2]
        with celebrity_logged_in('registry_experts'):
            self.assertIs(False, product.project_reviewed)

    def test_license_info_also_sets_reviewed(self):
        # The project_reviewed attribute it set to False if license_info
        # changes.
        product = self.factory.makeProduct(
            licenses=[License.OTHER_OPEN_SOURCE])
        with celebrity_logged_in('registry_experts'):
            product.project_reviewed = True
        with person_logged_in(product.owner):
            product.license_info = 'zlib'
        with celebrity_logged_in('registry_experts'):
            self.assertIs(False, product.project_reviewed)

    def test_setLicense_without_empty_licenses_error(self):
        # A project must have at least one licence.
        product = self.factory.makeProduct(licenses=[License.MIT])
        with person_logged_in(product.owner):
            self.assertRaises(
                ValueError, setattr, product, 'licenses', [])

    def test_setLicense_without_non_licenses_error(self):
        # A project must have at least one licence.
        product = self.factory.makeProduct(licenses=[License.MIT])
        with person_logged_in(product.owner):
            self.assertRaises(
                ValueError, setattr, product, 'licenses', ['bogus'])

    def test_setLicense_non_proprietary(self):
        # Non-proprietary projects are not given a complimentary
        # commercial subscription.
        product = self.factory.makeProduct(licenses=[License.MIT])
        self.assertIsNone(product.commercial_subscription)

    def test_setLicense_proprietary_with_commercial_subscription(self):
        # Proprietary projects with existing commercial subscriptions are not
        # given a complimentary commercial subscription.
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product)
        with celebrity_logged_in('admin'):
            product.commercial_subscription.sales_system_id = 'testing'
            date_expires = product.commercial_subscription.date_expires
        with person_logged_in(product.owner):
            product.licenses = [License.OTHER_PROPRIETARY]
        with celebrity_logged_in('admin'):
            self.assertEqual(
                'testing', product.commercial_subscription.sales_system_id)
            self.assertEqual(
                date_expires, product.commercial_subscription.date_expires)

    def test_setLicense_proprietary_without_commercial_subscription(self):
        # Proprietary projects without a commercial subscriptions are
        # given a complimentary 30 day commercial subscription.
        product = self.factory.makeProduct()
        with person_logged_in(product.owner):
            product.licenses = [License.OTHER_PROPRIETARY]
        with celebrity_logged_in('admin'):
            cs = product.commercial_subscription
            self.assertIsNotNone(cs)
            self.assertIn('complimentary-30-day', cs.sales_system_id)
            now = datetime.datetime.now(pytz.UTC)
            self.assertTrue(now >= cs.date_starts)
            future_30_days = now + datetime.timedelta(days=30)
            self.assertTrue(future_30_days >= cs.date_expires)
            self.assertIn(
                "Complimentary 30 day subscription. -- Launchpad",
                cs.whiteboard)
            lp_janitor = getUtility(ILaunchpadCelebrities).janitor
            self.assertEqual(lp_janitor, cs.registrant)
            self.assertEqual(lp_janitor, cs.purchaser)

    def test_new_proprietary_has_commercial_subscription(self):
        # New proprietary projects are given a complimentary 30 day
        # commercial subscription.
        owner = self.factory.makePerson()
        with person_logged_in(owner):
            product = getUtility(IProductSet).createProduct(
                owner, 'fnord', 'Fnord', 'Fnord', 'test 1', 'test 2',
                licenses=[License.OTHER_PROPRIETARY])
        with celebrity_logged_in('admin'):
            cs = product.commercial_subscription
            self.assertIsNotNone(cs)
            self.assertIn('complimentary-30-day', cs.sales_system_id)
            now = datetime.datetime.now(pytz.UTC)
            self.assertTrue(now >= cs.date_starts)
            future_30_days = now + datetime.timedelta(days=30)
            self.assertTrue(future_30_days >= cs.date_expires)
            self.assertIn(
                "Complimentary 30 day subscription. -- Launchpad",
                cs.whiteboard)
            lp_janitor = getUtility(ILaunchpadCelebrities).janitor
            self.assertEqual(lp_janitor, cs.registrant)
            self.assertEqual(lp_janitor, cs.purchaser)


class BaseSharingPolicyTests:
    """Common tests for product sharing policies."""

    layer = DatabaseFunctionalLayer

    def setSharingPolicy(self, policy, user):
        raise NotImplementedError

    def getSharingPolicy(self):
        raise NotImplementedError

    def setUp(self):
        super(BaseSharingPolicyTests, self).setUp()
        self.product = self.factory.makeProduct()
        self.commercial_admin = self.factory.makeCommercialAdmin()

    def test_owner_can_set_policy(self):
        # Project maintainers can set sharing policies.
        self.setSharingPolicy(self.public_policy, self.product.owner)
        self.assertEqual(self.public_policy, self.getSharingPolicy())

    def test_commercial_admin_can_set_policy(self):
        # Commercial admins can set sharing policies for commercial projects.
        self.factory.makeCommercialSubscription(product=self.product)
        self.setSharingPolicy(self.public_policy, self.commercial_admin)
        self.assertEqual(self.public_policy, self.getSharingPolicy())

    def test_random_cannot_set_policy(self):
        # An unrelated user can't set sharing policies.
        person = self.factory.makePerson()
        self.assertRaises(
            Unauthorized, self.setSharingPolicy, self.public_policy, person)

    def test_anonymous_cannot_set_policy(self):
        # An anonymous user can't set sharing policies.
        self.assertRaises(
            Unauthorized, self.setSharingPolicy, self.public_policy, None)

    def test_proprietary_forbidden_without_commercial_sub(self):
        # No policy that allows Proprietary can be configured without a
        # commercial subscription.
        self.setSharingPolicy(self.public_policy, self.product.owner)
        self.assertEqual(self.public_policy, self.getSharingPolicy())
        for policy in self.commercial_policies:
            self.assertRaises(
                CommercialSubscribersOnly,
                self.setSharingPolicy, policy, self.product.owner)

    def test_proprietary_allowed_with_commercial_sub(self):
        # All policies are valid when there's a current commercial
        # subscription.
        self.factory.makeCommercialSubscription(product=self.product)
        for policy in self.enum.items:
            self.setSharingPolicy(policy, self.commercial_admin)
            self.assertEqual(policy, self.getSharingPolicy())

    def test_setting_proprietary_creates_access_policy(self):
        # Setting a policy that allows Proprietary creates a
        # corresponding access policy and shares it with the the
        # maintainer.
        self.factory.makeCommercialSubscription(product=self.product)
        self.assertEqual(
            [InformationType.PRIVATESECURITY, InformationType.USERDATA],
            [policy.type for policy in
             getUtility(IAccessPolicySource).findByPillar([self.product])])
        self.setSharingPolicy(
            self.commercial_policies[0], self.commercial_admin)
        self.assertEqual(
            [InformationType.PRIVATESECURITY, InformationType.USERDATA,
             InformationType.PROPRIETARY],
            [policy.type for policy in
             getUtility(IAccessPolicySource).findByPillar([self.product])])
        self.assertTrue(
            getUtility(IService, 'sharing').checkPillarAccess(
                self.product, InformationType.PROPRIETARY, self.product.owner))

    def test_unused_policies_are_pruned(self):
        # When a sharing policy is changed, the allowed information types may
        # become more restricted. If this case, any existing access polices
        # for the now defunct information type(s) should be removed so long as
        # there are no corresponding policy artifacts.

        # We create a product with and ensure there's an APA.
        ap_source = getUtility(IAccessPolicySource)
        product = self.factory.makeProduct()
        [ap] = ap_source.find([(product, InformationType.PRIVATESECURITY)])
        self.factory.makeAccessPolicyArtifact(policy=ap)

        def getAccessPolicyTypes(pillar):
            return [
                ap.type
                for ap in ap_source.findByPillar([pillar])]

        # Now change the sharing policies to PROPRIETARY
        self.factory.makeCommercialSubscription(product=product)
        with person_logged_in(product.owner):
            product.setBugSharingPolicy(BugSharingPolicy.PROPRIETARY)
            # Just bug sharing policy has been changed so all previous policy
            # types are still valid.
            self.assertContentEqual(
                [InformationType.PRIVATESECURITY, InformationType.USERDATA,
                 InformationType.PROPRIETARY],
                getAccessPolicyTypes(product))

            product.setBranchSharingPolicy(BranchSharingPolicy.PROPRIETARY)
            # Proprietary is permitted by the sharing policy, and there's a
            # Private Security artifact. But Private isn't in use or allowed
            # by a sharing policy, so it's now gone.
            self.assertContentEqual(
                [InformationType.PRIVATESECURITY, InformationType.PROPRIETARY],
                getAccessPolicyTypes(product))


class ProductBugSharingPolicyTestCase(BaseSharingPolicyTests,
                                      TestCaseWithFactory):
    """Test Product.bug_sharing_policy."""

    layer = DatabaseFunctionalLayer

    enum = BugSharingPolicy
    public_policy = BugSharingPolicy.PUBLIC
    commercial_policies = (
        BugSharingPolicy.PUBLIC_OR_PROPRIETARY,
        BugSharingPolicy.PROPRIETARY_OR_PUBLIC,
        BugSharingPolicy.PROPRIETARY,
        )

    def setSharingPolicy(self, policy, user):
        with person_logged_in(user):
            result = self.product.setBugSharingPolicy(policy)
        return result

    def getSharingPolicy(self):
        return self.product.bug_sharing_policy


class ProductBranchSharingPolicyTestCase(BaseSharingPolicyTests,
                                         TestCaseWithFactory):
    """Test Product.branch_sharing_policy."""

    layer = DatabaseFunctionalLayer

    enum = BranchSharingPolicy
    public_policy = BranchSharingPolicy.PUBLIC
    commercial_policies = (
        BranchSharingPolicy.PUBLIC_OR_PROPRIETARY,
        BranchSharingPolicy.PROPRIETARY_OR_PUBLIC,
        BranchSharingPolicy.PROPRIETARY,
        BranchSharingPolicy.EMBARGOED_OR_PROPRIETARY,
        )

    def setSharingPolicy(self, policy, user):
        with person_logged_in(user):
            result = self.product.setBranchSharingPolicy(policy)
        return result

    def getSharingPolicy(self):
        return self.product.branch_sharing_policy

    def test_setting_embargoed_creates_access_policy(self):
        # Setting a policy that allows Embargoed creates a
        # corresponding access policy and shares it with the the
        # maintainer.
        self.factory.makeCommercialSubscription(product=self.product)
        self.assertEqual(
            [InformationType.PRIVATESECURITY, InformationType.USERDATA],
            [policy.type for policy in
             getUtility(IAccessPolicySource).findByPillar([self.product])])
        self.setSharingPolicy(
            BranchSharingPolicy.EMBARGOED_OR_PROPRIETARY,
            self.commercial_admin)
        self.assertEqual(
            [InformationType.PRIVATESECURITY, InformationType.USERDATA,
             InformationType.PROPRIETARY, InformationType.EMBARGOED],
            [policy.type for policy in
             getUtility(IAccessPolicySource).findByPillar([self.product])])
        self.assertTrue(
            getUtility(IService, 'sharing').checkPillarAccess(
                self.product, InformationType.PROPRIETARY, self.product.owner))
        self.assertTrue(
            getUtility(IService, 'sharing').checkPillarAccess(
                self.product, InformationType.EMBARGOED, self.product.owner))


class ProductSnapshotTestCase(TestCaseWithFactory):
    """Test product snapshots.

    Some attributes of a product should not be included in snapshots,
    typically because they are either too costly to fetch unless there's
    a real need, or because they get too big and trigger a shortlist
    overflow error.

    To stop an attribute from being snapshotted, wrap its declaration in
    the interface in `doNotSnapshot`.
    """

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(ProductSnapshotTestCase, self).setUp()
        self.product = self.factory.makeProduct(name="shamwow")

    def test_excluded_from_snapshot(self):
        omitted = [
            'series',
            'recipes',
            'releases',
            ]
        self.assertThat(self.product, DoesNotSnapshot(omitted, IProduct))


class TestProductTranslations(TestCaseWithFactory):
    """A TestCase for accessing product translations-related attributes."""

    layer = DatabaseFunctionalLayer

    def test_rosetta_expert(self):
        # Ensure rosetta-experts can set Product attributes
        # related to translations.
        product = self.factory.makeProduct()
        new_series = self.factory.makeProductSeries(product=product)
        group = self.factory.makeTranslationGroup()
        with celebrity_logged_in('rosetta_experts'):
            product.translations_usage = ServiceUsage.LAUNCHPAD
            product.translation_focus = new_series
            product.translationgroup = group
            product.translationpermission = TranslationPermission.CLOSED


class TestWebService(WebServiceTestCase):

    def test_translations_usage(self):
        """The translations_usage field should be writable."""
        product = self.factory.makeProduct()
        transaction.commit()
        ws_product = self.wsObject(product, product.owner)
        ws_product.translations_usage = ServiceUsage.EXTERNAL.title
        ws_product.lp_save()

    def test_translationpermission(self):
        """The translationpermission field should be writable."""
        product = self.factory.makeProduct()
        transaction.commit()
        ws_product = self.wsObject(product, product.owner)
        ws_product.translationpermission = TranslationPermission.CLOSED.title
        ws_product.lp_save()

    def test_translationgroup(self):
        """The translationgroup field should be writable."""
        product = self.factory.makeProduct()
        group = self.factory.makeTranslationGroup()
        transaction.commit()
        ws_product = self.wsObject(product, product.owner)
        ws_group = self.wsObject(group)
        ws_product.translationgroup = ws_group
        ws_product.lp_save()

    def test_oops_references_matching_product(self):
        # The product layer provides the context restriction, so we need to
        # check we can access context filtered references - e.g. on question.
        oopsid = "OOPS-abcdef1234"
        question = self.factory.makeQuestion(title="Crash with %s" % oopsid)
        product = question.product
        transaction.commit()
        ws_product = self.wsObject(product, product.owner)
        now = datetime.datetime.now(tz=pytz.utc)
        day = datetime.timedelta(days=1)
        self.failUnlessEqual(
            [oopsid],
            ws_product.findReferencedOOPS(start_date=now - day, end_date=now))
        self.failUnlessEqual(
            [],
            ws_product.findReferencedOOPS(
                start_date=now + day, end_date=now + day))

    def test_oops_references_different_product(self):
        # The product layer provides the context restriction, so we need to
        # check the filter is tight enough - other contexts should not work.
        oopsid = "OOPS-abcdef1234"
        self.factory.makeQuestion(title="Crash with %s" % oopsid)
        product = self.factory.makeProduct()
        transaction.commit()
        ws_product = self.wsObject(product, product.owner)
        now = datetime.datetime.now(tz=pytz.utc)
        day = datetime.timedelta(days=1)
        self.failUnlessEqual(
            [],
            ws_product.findReferencedOOPS(start_date=now - day, end_date=now))


class TestProductSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def makeAllInformationTypes(self):
        proprietary = self.factory.makeProduct(
            information_type=InformationType.PROPRIETARY)
        embargoed = self.factory.makeProduct(
            information_type=InformationType.EMBARGOED)
        public = self.factory.makeProduct(
            information_type=InformationType.PUBLIC)
        return proprietary, embargoed, public

    @staticmethod
    def filterFind(user):
        clause = ProductSet.getProductPrivacyFilter(user)
        return IStore(Product).find(Product, clause)

    def test_get_all_active_omits_proprietary(self):
        # Ignore proprietary products for anonymous users
        proprietary = self.factory.makeProduct(
            information_type=InformationType.PROPRIETARY)
        embargoed = self.factory.makeProduct(
            information_type=InformationType.EMBARGOED)
        result = ProductSet.get_all_active(None)
        self.assertNotIn(proprietary, result)
        self.assertNotIn(embargoed, result)

    def test_getProductPrivacyFilterAnonymous(self):
        # Ignore proprietary products for anonymous users
        proprietary, embargoed, public = self.makeAllInformationTypes()
        result = self.filterFind(None)
        self.assertIn(public, result)
        self.assertNotIn(embargoed, result)
        self.assertNotIn(proprietary, result)

    def test_getProductPrivacyFilter_excludes_random_users(self):
        # Exclude proprietary products for anonymous users
        random = self.factory.makePerson()
        proprietary, embargoed, public = self.makeAllInformationTypes()
        result = self.filterFind(random)
        self.assertIn(public, result)
        self.assertNotIn(embargoed, result)
        self.assertNotIn(proprietary, result)

    def grant(self, pillar, information_type, grantee):
        policy_source = getUtility(IAccessPolicySource)
        (policy,) = policy_source.find(
            [(pillar, information_type)])
        self.factory.makeAccessPolicyGrant(policy, grantee)

    def test_getProductPrivacyFilter_respects_grants(self):
        # Include proprietary products for users with right grants.
        grantee = self.factory.makePerson()
        proprietary, embargoed, public = self.makeAllInformationTypes()
        self.grant(embargoed, InformationType.EMBARGOED, grantee)
        self.grant(proprietary, InformationType.PROPRIETARY, grantee)
        result = self.filterFind(grantee)
        self.assertIn(public, result)
        self.assertIn(embargoed, result)
        self.assertIn(proprietary, result)

    def test_getProductPrivacyFilter_ignores_wrong_product(self):
        # Exclude proprietary products if grant is on wrong product.
        grantee = self.factory.makePerson()
        proprietary, embargoed, public = self.makeAllInformationTypes()
        self.factory.makeAccessPolicyGrant(grantee=grantee)
        result = self.filterFind(grantee)
        self.assertIn(public, result)
        self.assertNotIn(embargoed, result)
        self.assertNotIn(proprietary, result)

    def test_getProductPrivacyFilter_ignores_wrong_info_type(self):
        # Exclude proprietary products if grant is on wrong information type.
        grantee = self.factory.makePerson()
        proprietary, embargoed, public = self.makeAllInformationTypes()
        self.grant(embargoed, InformationType.PROPRIETARY, grantee)
        self.factory.makeAccessPolicy(proprietary, InformationType.EMBARGOED)
        self.grant(proprietary, InformationType.EMBARGOED, grantee)
        result = self.filterFind(grantee)
        self.assertIn(public, result)
        self.assertNotIn(embargoed, result)
        self.assertNotIn(proprietary, result)

    def test_getProductPrivacyFilter_respects_team_grants(self):
        # Include proprietary products for users in teams with right grants.
        grantee = self.factory.makeTeam()
        proprietary, embargoed, public = self.makeAllInformationTypes()
        self.grant(embargoed, InformationType.EMBARGOED, grantee)
        self.grant(proprietary, InformationType.PROPRIETARY, grantee)
        result = self.filterFind(grantee.teamowner)
        self.assertIn(public, result)
        self.assertIn(embargoed, result)
        self.assertIn(proprietary, result)

    def test_getProductPrivacyFilter_includes_admins(self):
        # Launchpad admins can see everything.
        proprietary, embargoed, public = self.makeAllInformationTypes()
        result = self.filterFind(self.factory.makeAdministrator())
        self.assertIn(public, result)
        self.assertIn(embargoed, result)
        self.assertIn(proprietary, result)

    def test_getProductPrivacyFilter_includes_commercial_admins(self):
        # Commercial admins can see everything.
        proprietary, embargoed, public = self.makeAllInformationTypes()
        result = self.filterFind(self.factory.makeCommercialAdmin())
        self.assertIn(public, result)
        self.assertIn(embargoed, result)
        self.assertIn(proprietary, result)
