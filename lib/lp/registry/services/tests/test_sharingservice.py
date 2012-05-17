# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


from lazr.restful.interfaces import IWebBrowserOriginatingRequest
from lazr.restful.utils import get_current_web_service_request
from testtools.matchers import Equals
import transaction
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.traversing.browser.absoluteurl import absoluteURL

from lp.app.interfaces.services import IService
from lp.bugs.interfaces.bug import IBug
from lp.code.enums import (
    BranchSubscriptionDiffSize,
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel,
    )
from lp.code.interfaces.branch import IBranch
from lp.registry.enums import (
    InformationType,
    SharingPermission,
    )
from lp.registry.interfaces.accesspolicy import (
    IAccessArtifactGrantSource,
    IAccessPolicyGrantFlatSource,
    IAccessPolicyGrantSource,
    IAccessPolicySource,
    )
from lp.registry.services.sharingservice import SharingService
from lp.services.features.testing import FeatureFixture
from lp.services.job.tests import block_on_job
from lp.services.webapp.interaction import ANONYMOUS
from lp.services.webapp.interfaces import ILaunchpadRoot
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    login,
    login_person,
    StormStatementRecorder,
    TestCaseWithFactory,
    WebServiceTestCase,
    ws_object,
    )
from lp.testing.layers import (
    AppServerLayer,
    CeleryJobLayer,
    )
from lp.testing.matchers import HasQueryCount
from lp.testing.pages import LaunchpadWebServiceCaller


WRITE_FLAG = {
    'disclosure.enhanced_sharing.writable': 'true',
    'disclosure.enhanced_sharing_details.enabled': 'true',
    'jobs.celery.enabled_classes': 'RemoveSubscriptionsJob'}
DETAILS_FLAG = {'disclosure.enhanced_sharing_details.enabled': 'true'}


class TestSharingService(TestCaseWithFactory):
    """Tests for the SharingService."""

    layer = CeleryJobLayer

    def setUp(self):
        super(TestSharingService, self).setUp()
        self.service = getUtility(IService, 'sharing')

    def _makeShareeData(self, sharee, policy_permissions,
                        shared_artifact_types):
        # Unpack a sharee into its attributes and add in permissions.
        request = get_current_web_service_request()
        sharee_data = {
            'name': sharee.name,
            'meta': 'team' if sharee.is_team else 'person',
            'display_name': sharee.displayname,
            'self_link': absoluteURL(sharee, request),
            'permissions': {}}
        browser_request = IWebBrowserOriginatingRequest(request)
        sharee_data['web_link'] = absoluteURL(sharee, browser_request)
        shared_items_exist = False
        permissions = {}
        for (policy, permission) in policy_permissions:
            permissions[policy.name] = unicode(permission.name)
            if permission == SharingPermission.SOME:
                shared_items_exist = True
        sharee_data['shared_items_exist'] = shared_items_exist
        sharee_data['shared_artifact_types'] = [
            info_type.name for info_type in shared_artifact_types]
        sharee_data['permissions'] = permissions
        return sharee_data

    def test_getSharingPermissions(self):
        # test_getSharingPermissions returns permissions in the right order.
        permissions = self.service.getSharingPermissions()
        expected_permissions = [
            SharingPermission.ALL,
            SharingPermission.SOME,
            SharingPermission.NOTHING
        ]
        for x, permission in enumerate(expected_permissions):
            self.assertEqual(permissions[x]['value'], permission.name)

    def _assert_getInformationTypes(self, pillar, expected_policies):
        policy_data = self.service.getInformationTypes(pillar)
        expected_data = []
        for x, policy in enumerate(expected_policies):
            item = dict(
                index=x,
                value=policy.name,
                title=policy.title,
                description=policy.description
            )
            expected_data.append(item)
        self.assertContentEqual(expected_data, policy_data)

    def test_getInformationTypes_product(self):
        product = self.factory.makeProduct()
        self._assert_getInformationTypes(
            product,
            [InformationType.EMBARGOEDSECURITY, InformationType.USERDATA])

    def test_getInformationTypes_expired_commercial_product(self):
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product, expired=True)
        self._assert_getInformationTypes(
            product,
            [InformationType.EMBARGOEDSECURITY, InformationType.USERDATA])

    def test_getInformationTypes_commercial_product(self):
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product)
        self._assert_getInformationTypes(
            product,
            [InformationType.EMBARGOEDSECURITY,
             InformationType.USERDATA,
             InformationType.PROPRIETARY])

    def test_getInformationTypes_distro(self):
        distro = self.factory.makeDistribution()
        self._assert_getInformationTypes(
            distro,
            [InformationType.EMBARGOEDSECURITY, InformationType.USERDATA])

    def test_jsonShareeData_with_Some(self):
        # jsonShareeData returns the expected data for a grantee with
        # permissions which include SOME.
        product = self.factory.makeProduct()
        [policy1, policy2] = getUtility(IAccessPolicySource).findByPillar(
            [product])
        grantee = self.factory.makePerson()
        with FeatureFixture(DETAILS_FLAG):
            sharees = self.service.jsonShareeData(
                [(grantee, {
                    policy1: SharingPermission.ALL,
                    policy2: SharingPermission.SOME},
                  [policy1.type, policy2.type])])
        expected_data = self._makeShareeData(
            grantee,
            [(policy1.type, SharingPermission.ALL),
             (policy2.type, SharingPermission.SOME)],
             [policy1.type, policy2.type])
        self.assertContentEqual([expected_data], sharees)

    def test_jsonShareeData_with_Some_without_flag(self):
        # jsonShareeData returns the expected data for a grantee with
        # permissions which include SOME and the feature flag not set.
        product = self.factory.makeProduct()
        [policy1, policy2] = getUtility(IAccessPolicySource).findByPillar(
            [product])
        grantee = self.factory.makePerson()
        sharees = self.service.jsonShareeData(
            [(grantee, {
                policy1: SharingPermission.ALL,
                policy2: SharingPermission.SOME}, [policy2.type])])
        expected_data = self._makeShareeData(
            grantee,
            [(policy1.type, SharingPermission.ALL),
             (policy2.type, SharingPermission.SOME)], [policy2.type])
        expected_data['shared_items_exist'] = False
        self.assertContentEqual([expected_data], sharees)

    def test_jsonShareeData_without_Some(self):
        # jsonShareeData returns the expected data for a grantee with only ALL
        # permissions.
        product = self.factory.makeProduct()
        [policy1, policy2] = getUtility(IAccessPolicySource).findByPillar(
            [product])
        grantee = self.factory.makePerson()
        with FeatureFixture(DETAILS_FLAG):
            sharees = self.service.jsonShareeData(
                [(grantee, {
                    policy1: SharingPermission.ALL}, [])])
        expected_data = self._makeShareeData(
            grantee,
            [(policy1.type, SharingPermission.ALL)], [])
        self.assertContentEqual([expected_data], sharees)

    def _assert_getPillarShareeData(self, pillar):
        # getPillarShareeData returns the expected data.
        access_policy = self.factory.makeAccessPolicy(
            pillar=pillar,
            type=InformationType.PROPRIETARY)
        grantee = self.factory.makePerson()
        # Make access policy grant so that 'All' is returned.
        self.factory.makeAccessPolicyGrant(access_policy, grantee)
        # Make access artifact grants so that 'Some' is returned.
        artifact_grant = self.factory.makeAccessArtifactGrant()
        self.factory.makeAccessPolicyArtifact(
            artifact=artifact_grant.abstract_artifact, policy=access_policy)

        with FeatureFixture(DETAILS_FLAG):
            sharees = self.service.getPillarShareeData(pillar)
        expected_sharees = [
            self._makeShareeData(
                grantee,
                [(InformationType.PROPRIETARY, SharingPermission.ALL)], []),
            self._makeShareeData(
                artifact_grant.grantee,
                [(InformationType.PROPRIETARY, SharingPermission.SOME)],
                [InformationType.PROPRIETARY])]
        self.assertContentEqual(expected_sharees, sharees)

    def test_getProductShareeData(self):
        # Users with launchpad.Driver can view sharees.
        driver = self.factory.makePerson()
        product = self.factory.makeProduct(driver=driver)
        login_person(driver)
        self._assert_getPillarShareeData(product)

    def test_getDistroShareeData(self):
        # Users with launchpad.Driver can view sharees.
        driver = self.factory.makePerson()
        distro = self.factory.makeDistribution(driver=driver)
        login_person(driver)
        self._assert_getPillarShareeData(distro)

    def _assert_QueryCount(self, func):
        """ getPillarSharees[Data] only should use 3 queries.

        1. load access policies for pillar
        2. load sharees
        3. load permissions for sharee

        Steps 2 and 3 are split out to allow batching on persons.
        """
        driver = self.factory.makePerson()
        product = self.factory.makeProduct(driver=driver)
        login_person(driver)
        access_policy = self.factory.makeAccessPolicy(
            pillar=product,
            type=InformationType.PROPRIETARY)

        def makeGrants():
            grantee = self.factory.makePerson()
            # Make access policy grant so that 'All' is returned.
            self.factory.makeAccessPolicyGrant(access_policy, grantee)
            # Make access artifact grants so that 'Some' is returned.
            artifact_grant = self.factory.makeAccessArtifactGrant()
            self.factory.makeAccessPolicyArtifact(
                artifact=artifact_grant.abstract_artifact,
                policy=access_policy)

        # Make some grants and check the count.
        for x in range(5):
            makeGrants()
        with StormStatementRecorder() as recorder:
            sharees = list(func(product))
        self.assertEqual(10, len(sharees))
        self.assertThat(recorder, HasQueryCount(Equals(3)))
        # Make some more grants and check again.
        for x in range(5):
            makeGrants()
        with StormStatementRecorder() as recorder:
            sharees = list(func(product))
        self.assertEqual(20, len(sharees))
        self.assertThat(recorder, HasQueryCount(Equals(3)))

    def test_getPillarShareesQueryCount(self):
        self._assert_QueryCount(self.service.getPillarSharees)

    def test_getPillarShareeDataQueryCount(self):
        self._assert_QueryCount(self.service.getPillarShareeData)

    def _assert_getPillarShareeDataUnauthorized(self, pillar):
        # getPillarShareeData raises an Unauthorized exception if the user is
        # not permitted to do so.
        access_policy = self.factory.makeAccessPolicy(pillar=pillar)
        grantee = self.factory.makePerson()
        self.factory.makeAccessPolicyGrant(access_policy, grantee)
        self.assertRaises(
            Unauthorized, self.service.getPillarShareeData, pillar)

    def test_getPillarShareeDataAnonymous(self):
        # Anonymous users are not allowed.
        product = self.factory.makeProduct()
        login(ANONYMOUS)
        self._assert_getPillarShareeDataUnauthorized(product)

    def test_getPillarShareeDataAnyone(self):
        # Unauthorized users are not allowed.
        product = self.factory.makeProduct()
        login_person(self.factory.makePerson())
        self._assert_getPillarShareeDataUnauthorized(product)

    def _assert_getPillarSharees(self, pillar):
        # getPillarSharees returns the expected data.
        access_policy = self.factory.makeAccessPolicy(
            pillar=pillar,
            type=InformationType.PROPRIETARY)
        grantee = self.factory.makePerson()
        # Make access policy grant so that 'All' is returned.
        self.factory.makeAccessPolicyGrant(access_policy, grantee)
        # Make access artifact grants so that 'Some' is returned.
        artifact_grant = self.factory.makeAccessArtifactGrant()
        self.factory.makeAccessPolicyArtifact(
            artifact=artifact_grant.abstract_artifact, policy=access_policy)

        sharees = self.service.getPillarSharees(pillar)
        expected_sharees = [
            (grantee, {access_policy: SharingPermission.ALL}, []),
            (artifact_grant.grantee, {access_policy: SharingPermission.SOME},
             [access_policy.type])]
        self.assertContentEqual(expected_sharees, sharees)

    def test_getProductSharees(self):
        # Users with launchpad.Driver can view sharees.
        driver = self.factory.makePerson()
        product = self.factory.makeProduct(driver=driver)
        login_person(driver)
        self._assert_getPillarSharees(product)

    def test_getDistroSharees(self):
        # Users with launchpad.Driver can view sharees.
        driver = self.factory.makePerson()
        distro = self.factory.makeDistribution(driver=driver)
        login_person(driver)
        self._assert_getPillarSharees(distro)

    def _assert_getPillarShareesUnauthorized(self, pillar):
        # getPillarSharees raises an Unauthorized exception if the user is
        # not permitted to do so.
        access_policy = self.factory.makeAccessPolicy(pillar=pillar)
        grantee = self.factory.makePerson()
        self.factory.makeAccessPolicyGrant(access_policy, grantee)
        self.assertRaises(
            Unauthorized, self.service.getPillarSharees, pillar)

    def test_getPillarShareesAnonymous(self):
        # Anonymous users are not allowed.
        product = self.factory.makeProduct()
        login(ANONYMOUS)
        self._assert_getPillarShareesUnauthorized(product)

    def test_getPillarShareesAnyone(self):
        # Unauthorized users are not allowed.
        product = self.factory.makeProduct()
        login_person(self.factory.makePerson())
        self._assert_getPillarShareesUnauthorized(product)

    def _assert_sharePillarInformation(self, pillar):
        """sharePillarInformations works and returns the expected data."""
        sharee = self.factory.makePerson()
        grantor = self.factory.makePerson()

        # Make existing grants to ensure sharePillarInformation handles those
        # cases correctly.
        # First, a grant that is in the add set - it wil be retained.
        es_policy = getUtility(IAccessPolicySource).find(((
            pillar, InformationType.EMBARGOEDSECURITY),))[0]
        ud_policy = getUtility(IAccessPolicySource).find(((
            pillar, InformationType.USERDATA),))[0]
        self.factory.makeAccessPolicyGrant(
            es_policy, grantee=sharee, grantor=grantor)
        # Second, grants that are not in the all set - they will be deleted.
        p_policy = self.factory.makeAccessPolicy(
            pillar=pillar, type=InformationType.PROPRIETARY)
        self.factory.makeAccessPolicyGrant(
            p_policy, grantee=sharee, grantor=grantor)
        self.factory.makeAccessPolicyGrant(
            ud_policy, grantee=sharee, grantor=grantor)

        # We also make some artifact grants.
        # First, a grant which will be retained.
        artifact = self.factory.makeAccessArtifact()
        self.factory.makeAccessArtifactGrant(artifact, sharee)
        self.factory.makeAccessPolicyArtifact(
            artifact=artifact, policy=es_policy)
        # Second, grants which will be deleted because their policies have
        # information types in the 'some' or 'nothing' category.
        artifact = self.factory.makeAccessArtifact()
        self.factory.makeAccessArtifactGrant(artifact, sharee)
        self.factory.makeAccessPolicyArtifact(
            artifact=artifact, policy=p_policy)
        artifact = self.factory.makeAccessArtifact()
        self.factory.makeAccessArtifactGrant(artifact, sharee)
        self.factory.makeAccessPolicyArtifact(
            artifact=artifact, policy=ud_policy)

        # Now call sharePillarInformation will the grants we want.
        permissions = {
            InformationType.EMBARGOEDSECURITY: SharingPermission.ALL,
            InformationType.USERDATA: SharingPermission.SOME,
            InformationType.PROPRIETARY: SharingPermission.NOTHING}
        with FeatureFixture(WRITE_FLAG):
            sharee_data = self.service.sharePillarInformation(
                pillar, sharee, permissions, grantor)
        policies = getUtility(IAccessPolicySource).findByPillar([pillar])
        policy_grant_source = getUtility(IAccessPolicyGrantSource)
        [grant] = policy_grant_source.findByPolicy(policies)
        self.assertEqual(grantor, grant.grantor)
        self.assertEqual(sharee, grant.grantee)
        expected_permissions = [
            (InformationType.EMBARGOEDSECURITY, SharingPermission.ALL),
            (InformationType.USERDATA, SharingPermission.SOME)]
        expected_sharee_data = self._makeShareeData(
            sharee, expected_permissions,
            [InformationType.USERDATA, InformationType.EMBARGOEDSECURITY])
        self.assertEqual(expected_sharee_data, sharee_data)
        # Check that getPillarSharees returns what we expect.
        expected_sharee_grants = [
            (sharee, {
                es_policy: SharingPermission.ALL,
                ud_policy: SharingPermission.SOME},
             [InformationType.USERDATA, InformationType.EMBARGOEDSECURITY])]
        sharee_grants = list(self.service.getPillarSharees(pillar))
        self.assertContentEqual(expected_sharee_grants, sharee_grants)

    def test_updateProjectGroupSharee_not_allowed(self):
        # We cannot add sharees to ProjectGroups.
        owner = self.factory.makePerson()
        project_group = self.factory.makeProject(owner=owner)
        sharee = self.factory.makePerson()
        login_person(owner)
        self.assertRaises(
            AssertionError, self.service.sharePillarInformation,
            project_group, sharee,
            {InformationType.USERDATA: SharingPermission.ALL}, owner)

    def test_updateProductSharee(self):
        # Users with launchpad.Edit can add sharees.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)
        self._assert_sharePillarInformation(product)

    def test_updateDistroSharee(self):
        # Users with launchpad.Edit can add sharees.
        owner = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=owner)
        login_person(owner)
        self._assert_sharePillarInformation(distro)

    def test_updatePillarSharee_no_access_grants_remain(self):
        # When a pillar sharee has it's only access policy permission changed
        # to Some, test that None is returned.
        owner = self.factory.makePerson()
        pillar = self.factory.makeProduct(owner=owner)
        login_person(owner)
        sharee = self.factory.makePerson()
        grant = self.factory.makeAccessPolicyGrant(grantee=sharee)

        permissions = {
            grant.policy.type: SharingPermission.SOME}
        with FeatureFixture(WRITE_FLAG):
            sharee_data = self.service.sharePillarInformation(
                pillar, sharee, permissions, self.factory.makePerson())
        self.assertIsNone(sharee_data)

    def _assert_sharePillarInformationUnauthorized(self, pillar):
        # sharePillarInformation raises an Unauthorized exception if the user
        # is not permitted to do so.
        with FeatureFixture(WRITE_FLAG):
            sharee = self.factory.makePerson()
            user = self.factory.makePerson()
            self.assertRaises(
                Unauthorized, self.service.sharePillarInformation,
                pillar, sharee,
                {InformationType.USERDATA: SharingPermission.ALL}, user)

    def test_sharePillarInformationAnonymous(self):
        # Anonymous users are not allowed.
        with FeatureFixture(WRITE_FLAG):
            product = self.factory.makeProduct()
            login(ANONYMOUS)
            self._assert_sharePillarInformationUnauthorized(product)

    def test_sharePillarInformationAnyone(self):
        # Unauthorized users are not allowed.
        with FeatureFixture(WRITE_FLAG):
            product = self.factory.makeProduct()
            login_person(self.factory.makePerson())
            self._assert_sharePillarInformationUnauthorized(product)

    def test_sharePillarInformation_without_flag(self):
        # The feature flag needs to be enabled.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)
        sharee = self.factory.makePerson()
        user = self.factory.makePerson()
        self.assertRaises(
            Unauthorized, self.service.sharePillarInformation,
            product, sharee,
            {InformationType.USERDATA: SharingPermission.ALL}, user)

    def _assert_deletePillarSharee(self, pillar, types_to_delete=None):
        access_policies = getUtility(IAccessPolicySource).findByPillar(
            (pillar,))
        information_types = [ap.type for ap in access_policies]
        grantee = self.factory.makePerson()
        # Make some access policy grants for our sharee.
        for access_policy in access_policies:
            self.factory.makeAccessPolicyGrant(access_policy, grantee)
        # Make some artifact grants for our sharee.
        artifact = self.factory.makeAccessArtifact()
        self.factory.makeAccessArtifactGrant(artifact, grantee)
        for access_policy in access_policies:
            self.factory.makeAccessPolicyArtifact(
                artifact=artifact, policy=access_policy)
        # Make some access policy grants for another sharee.
        another = self.factory.makePerson()
        self.factory.makeAccessPolicyGrant(access_policies[0], another)
        # Delete data for a specific information type.
        with FeatureFixture(WRITE_FLAG):
            self.service.deletePillarSharee(
                pillar, pillar.owner, grantee, types_to_delete)
        # Assemble the expected data for the remaining access grants for
        # grantee.
        expected_data = []
        if types_to_delete is not None:
            expected_information_types = (
                set(information_types).difference(types_to_delete))
            expected_policies = [
                access_policy for access_policy in access_policies
                if access_policy.type in expected_information_types]
            expected_data = [
                (grantee, {policy: SharingPermission.ALL}, [])
                for policy in expected_policies]
        # Add the expected data for the other sharee.
        another_person_data = (
            another, {access_policies[0]: SharingPermission.ALL}, [])
        expected_data.append(another_person_data)
        self.assertContentEqual(
            expected_data, self.service.getPillarSharees(pillar))

    def test_deleteProductShareeAll(self):
        # Users with launchpad.Edit can delete all access for a sharee.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)
        self._assert_deletePillarSharee(product)

    def test_deleteProductShareeSelectedPolicies(self):
        # Users with launchpad.Edit can delete selected policy access for an
        # sharee.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)
        self._assert_deletePillarSharee(product, [InformationType.USERDATA])

    def test_deleteDistroShareeAll(self):
        # Users with launchpad.Edit can delete all access for a sharee.
        owner = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=owner)
        login_person(owner)
        self._assert_deletePillarSharee(distro)

    def test_deleteDistroShareeSelectedPolicies(self):
        # Users with launchpad.Edit can delete selected policy access for an
        # sharee.
        owner = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=owner)
        login_person(owner)
        self._assert_deletePillarSharee(distro, [InformationType.USERDATA])

    def _assert_deletePillarShareeUnauthorized(self, pillar):
        # deletePillarSharee raises an Unauthorized exception if the user
        # is not permitted to do so.
        with FeatureFixture(WRITE_FLAG):
            self.assertRaises(
                Unauthorized, self.service.deletePillarSharee,
                pillar, pillar.owner, [InformationType.USERDATA])

    def test_deletePillarShareeAnonymous(self):
        # Anonymous users are not allowed.
        with FeatureFixture(WRITE_FLAG):
            product = self.factory.makeProduct()
            login(ANONYMOUS)
            self._assert_deletePillarShareeUnauthorized(product)

    def test_deletePillarShareeAnyone(self):
        # Unauthorized users are not allowed.
        with FeatureFixture(WRITE_FLAG):
            product = self.factory.makeProduct()
            login_person(self.factory.makePerson())
            self._assert_deletePillarShareeUnauthorized(product)

    def test_deletePillarSharee_without_flag(self):
        # The feature flag needs to be enabled.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)
        self.assertRaises(
            Unauthorized, self.service.deletePillarSharee,
            product, product.owner, [InformationType.USERDATA])

    def _assert_deleteShareeRemoveSubscriptions(self,
                                                types_to_delete=None):
        product = self.factory.makeProduct()
        access_policies = getUtility(IAccessPolicySource).findByPillar(
            (product,))
        information_types = [ap.type for ap in access_policies]
        grantee = self.factory.makePerson()
        # Make some access policy grants for our sharee.
        for access_policy in access_policies:
            self.factory.makeAccessPolicyGrant(access_policy, grantee)

        login_person(product.owner)
        # Make some bug artifact grants for our sharee.
        # Branches will be done when information_type attribute is supported.
        bugs = []
        for access_policy in access_policies:
            bug = self.factory.makeBug(
                product=product, owner=product.owner,
                information_type=access_policy.type)
            bugs.append(bug)
            artifact = self.factory.makeAccessArtifact(concrete=bug)
            self.factory.makeAccessArtifactGrant(artifact, grantee)

        # Make some access policy grants for another sharee.
        another = self.factory.makePerson()
        self.factory.makeAccessPolicyGrant(access_policies[0], another)

        # Subscribe the grantee and other person to the artifacts.
        for person in [grantee, another]:
            for bug in bugs:
                bug.subscribe(person, product.owner)

        # Delete data for specified information types or all.
        with FeatureFixture(WRITE_FLAG):
            self.service.deletePillarSharee(
                product, product.owner, grantee, types_to_delete)
        with block_on_job(self):
            transaction.commit()

        expected_information_types = []
        if types_to_delete is not None:
            expected_information_types = (
                set(information_types).difference(types_to_delete))
        # Check that grantee is unsubscribed.
        for bug in bugs:
            if bug.information_type in expected_information_types:
                self.assertIn(grantee, bug.getDirectSubscribers())
            else:
                self.assertNotIn(grantee, bug.getDirectSubscribers())
            self.assertIn(another, bug.getDirectSubscribers())

    def test_shareeUnsubscribedWhenDeleted(self):
        # The sharee is unsubscribed from any inaccessible artifacts when their
        # access is revoked.
        self._assert_deleteShareeRemoveSubscriptions()

    def test_shareeUnsubscribedWhenDeletedSelectedPolicies(self):
        # The sharee is unsubscribed from any inaccessible artifacts when their
        # access to selected policies is revoked.
        self._assert_deleteShareeRemoveSubscriptions(
            [InformationType.USERDATA])

    def _assert_revokeAccessGrants(self, pillar, bugs, branches):
        artifacts = []
        if bugs:
            artifacts.extend(bugs)
        if branches:
            artifacts.extend(branches)
        policy = self.factory.makeAccessPolicy(pillar=pillar)
        # Grant access to a grantee and another person.
        grantee = self.factory.makePerson()
        someone = self.factory.makePerson()
        access_artifacts = []
        for artifact in artifacts:
            access_artifact = self.factory.makeAccessArtifact(
                concrete=artifact)
            access_artifacts.append(access_artifact)
            self.factory.makeAccessPolicyArtifact(
                artifact=access_artifact, policy=policy)
            for person in [grantee, someone]:
                self.factory.makeAccessArtifactGrant(
                    artifact=access_artifact, grantee=person,
                    grantor=pillar.owner)

        # Subscribe the grantee and other person to the artifacts.
        for person in [grantee, someone]:
            for bug in bugs or []:
                bug.subscribe(person, pillar.owner)
            for branch in branches or []:
                branch.subscribe(grantee,
                    BranchSubscriptionNotificationLevel.NOEMAIL, None,
                    CodeReviewNotificationLevel.NOEMAIL, pillar.owner)

        # Check that grantee has expected access grants.
        accessartifact_grant_source = getUtility(IAccessArtifactGrantSource)
        grants = accessartifact_grant_source.findByArtifact(
            access_artifacts, [grantee])
        apgfs = getUtility(IAccessPolicyGrantFlatSource)
        self.assertEqual(1, grants.count())

        with FeatureFixture(WRITE_FLAG):
            self.service.revokeAccessGrants(
                pillar, pillar.owner, grantee, bugs=bugs, branches=branches)
        with block_on_job(self):
            transaction.commit()

        # The grantee now has no access to anything.
        permission_info = apgfs.findGranteePermissionsByPolicy(
            [policy], [grantee])
        self.assertEqual(0, permission_info.count())

        # Check that the grantee's subscriptions have been removed.
        # Branches will be done once they have the information_type attribute.
        for bug in bugs:
            self.assertNotIn(grantee, bug.getDirectSubscribers())

        # Someone else still has access to the bugs and branches.
        grants = accessartifact_grant_source.findByArtifact(
            access_artifacts, [someone])
        self.assertEqual(1, grants.count())
        # Someone else still has subscriptions to the bugs and branches.
        for bug in bugs:
            self.assertIn(someone, bug.getDirectSubscribers())
        for branch in branches:
            self.assertIn(someone, branch.subscribers)

    def test_revokeAccessGrantsBugs(self):
        # Users with launchpad.Edit can delete all access for a sharee.
        owner = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=owner)
        login_person(owner)
        bug = self.factory.makeBug(
            distribution=distro, owner=owner,
            information_type=InformationType.USERDATA)
        self._assert_revokeAccessGrants(distro, [bug], None)

    def test_revokeAccessGrantsBranches(self):
        # Users with launchpad.Edit can delete all access for a sharee.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)
        branch = self.factory.makeBranch(
            product=product, owner=owner, private=True)
        self._assert_revokeAccessGrants(product, None, [branch])

    def _assert_revokeAccessGrantsUnauthorized(self):
        # revokeAccessGrants raises an Unauthorized exception if the user
        # is not permitted to do so.
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(
            product=product, information_type=InformationType.USERDATA)
        sharee = self.factory.makePerson()
        with FeatureFixture(WRITE_FLAG):
            self.assertRaises(
                Unauthorized, self.service.revokeAccessGrants,
                product, product.owner, sharee, bugs=[bug])

    def test_revokeAccessGrantsAnonymous(self):
        # Anonymous users are not allowed.
        with FeatureFixture(WRITE_FLAG):
            login(ANONYMOUS)
            self._assert_revokeAccessGrantsUnauthorized()

    def test_revokeAccessGrantsAnyone(self):
        # Unauthorized users are not allowed.
        with FeatureFixture(WRITE_FLAG):
            login_person(self.factory.makePerson())
            self._assert_revokeAccessGrantsUnauthorized()

    def test_revokeAccessGrants_without_flag(self):
        # The feature flag needs to be enabled.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        bug = self.factory.makeBug(
            product=product, information_type=InformationType.USERDATA)
        sharee = self.factory.makePerson()
        login_person(owner)
        self.assertRaises(
            Unauthorized, self.service.revokeAccessGrants,
            product, product.owner, sharee, bugs=[bug])

    def _assert_createAccessGrants(self, user, bugs, branches):
        # Creating access grants works as expected.
        grantee = self.factory.makePerson()
        with FeatureFixture(WRITE_FLAG):
            self.service.createAccessGrants(
                user, grantee, bugs=bugs, branches=branches)

        # Check that grantee has expected access grants.
        shared_bugs = []
        shared_branches = []
        all_pillars = []
        for bug in bugs or []:
            all_pillars.extend(bug.affected_pillars)
        for branch in branches or []:
            all_pillars.append(branch.target.context)
        policies = getUtility(IAccessPolicySource).findByPillar(all_pillars)

        apgfs = getUtility(IAccessPolicyGrantFlatSource)
        access_artifacts = apgfs.findArtifactsByGrantee(grantee, policies)
        for a in access_artifacts:
            if IBug.providedBy(a.concrete_artifact):
                shared_bugs.append(a.concrete_artifact)
            elif IBranch.providedBy(a.concrete_artifact):
                shared_branches.append(a.concrete_artifact)
        self.assertContentEqual(bugs or [], shared_bugs)
        self.assertContentEqual(branches or [], shared_branches)

    def test_createAccessGrantsBugs(self):
        # Access grants can be created for bugs.
        owner = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=owner)
        login_person(owner)
        bug = self.factory.makeBug(
            distribution=distro, owner=owner,
            information_type=InformationType.USERDATA)
        self._assert_createAccessGrants(owner, [bug], None)

    def test_createAccessGrantsBranches(self):
        # Access grants can be created for branches.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)
        branch = self.factory.makeBranch(
            product=product, owner=owner, private=True)
        self._assert_createAccessGrants(owner, None, [branch])

    def _assert_createAccessGrantsUnauthorized(self, user):
        # createAccessGrants raises an Unauthorized exception if the user
        # is not permitted to do so.
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(
            product=product, information_type=InformationType.USERDATA)
        sharee = self.factory.makePerson()
        with FeatureFixture(WRITE_FLAG):
            self.assertRaises(
                Unauthorized, self.service.createAccessGrants,
                user, sharee, bugs=[bug])

    def test_createAccessGrantsAnonymous(self):
        # Anonymous users are not allowed.
        with FeatureFixture(WRITE_FLAG):
            login(ANONYMOUS)
            self._assert_createAccessGrantsUnauthorized(ANONYMOUS)

    def test_createAccessGrantsAnyone(self):
        # Unauthorized users are not allowed.
        with FeatureFixture(WRITE_FLAG):
            anyone = self.factory.makePerson()
            login_person(anyone)
            self._assert_createAccessGrantsUnauthorized(anyone)

    def test_createAccessGrants_without_flag(self):
        # The feature flag needs to be enabled.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        bug = self.factory.makeBug(
            product=product, information_type=InformationType.USERDATA)
        sharee = self.factory.makePerson()
        login_person(owner)
        self.assertRaises(
            Unauthorized, self.service.createAccessGrants,
            product.owner, sharee, bugs=[bug])

    def test_getSharedArtifacts(self):
        # Test the getSharedArtifacts method.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)

        bugs = []
        bug_tasks = []
        for x in range(0, 10):
            bug = self.factory.makeBug(
                product=product, owner=owner,
                information_type=InformationType.USERDATA)
            bugs.append(bug)
            bug_tasks.append(bug.default_bugtask)
        branches = []
        for x in range(0, 10):
            branch = self.factory.makeBranch(
                product=product, owner=owner, private=True)
            branches.append(branch)

        # Grant access to grantee as well as the person who will be doing the
        # query. The person who will be doing the query is not granted access
        # to the last bug/branch so those won't be in the result.
        grantee = self.factory.makePerson()
        user = self.factory.makePerson()

        def grant_access(artifact, grantee_only):
            access_artifact = self.factory.makeAccessArtifact(
                concrete=artifact)
            self.factory.makeAccessArtifactGrant(
                artifact=access_artifact, grantee=grantee, grantor=owner)
            if not grantee_only:
                self.factory.makeAccessArtifactGrant(
                    artifact=access_artifact, grantee=user, grantor=owner)
            return access_artifact

        for i, bug in enumerate(bugs):
            grant_access(bug, i == 9)
        # For branches we also need to call makeAccessPolicyArtifact.
        [policy] = getUtility(IAccessPolicySource).find(
            [(product, InformationType.USERDATA)])
        for i, branch in enumerate(branches):
            artifact = grant_access(branch, i == 9)
            # XXX for now we need to subscribe users to the branch in order
            # for the underlying BranchCollection to allow access. This will
            # no longer be the case when BranchCollection supports the new
            # access policy framework.
            if i < 9:
                branch.subscribe(
                    user, BranchSubscriptionNotificationLevel.NOEMAIL,
                    BranchSubscriptionDiffSize.NODIFF,
                    CodeReviewNotificationLevel.NOEMAIL,
                    owner)
            self.factory.makeAccessPolicyArtifact(
                artifact=artifact, policy=policy)

        # Check the results.
        shared_bugtasks, shared_branches = self.service.getSharedArtifacts(
            product, grantee, user)
        self.assertContentEqual(bug_tasks[:9], shared_bugtasks)
        self.assertContentEqual(branches[:9], shared_branches)

    def test_getVisibleArtifacts(self):
        # Test the getVisibleArtifacts method.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        grantee = self.factory.makePerson()
        login_person(owner)

        bugs = []
        for x in range(0, 10):
            bug = self.factory.makeBug(
                product=product, owner=owner,
                information_type=InformationType.USERDATA)
            bugs.append(bug)
        branches = []
        for x in range(0, 10):
            branch = self.factory.makeBranch(
                product=product, owner=owner, private=True)
            branches.append(branch)

        def grant_access(artifact):
            access_artifact = self.factory.makeAccessArtifact(
                concrete=artifact)
            self.factory.makeAccessArtifactGrant(
                artifact=access_artifact, grantee=grantee, grantor=owner)
            return access_artifact

        # Grant access to some of the bugs and branches.
        for bug in bugs[:5]:
            grant_access(bug)
        for branch in branches[:5]:
            grant_access(branch)
            # XXX for now we need to subscribe users to the branch in order
            # for the underlying BranchCollection to allow access. This will
            # no longer be the case when BranchCollection supports the new
            # access policy framework.
            branch.subscribe(
                grantee, BranchSubscriptionNotificationLevel.NOEMAIL,
                BranchSubscriptionDiffSize.NODIFF,
                CodeReviewNotificationLevel.NOEMAIL,
                owner)

        # Check the results.
        shared_bugs, shared_branches = self.service.getVisibleArtifacts(
            grantee, branches, bugs)
        self.assertContentEqual(bugs[:5], shared_bugs)
        self.assertContentEqual(branches[:5], shared_branches)


class ApiTestMixin:
    """Common tests for launchpadlib and webservice."""

    def setUp(self):
        super(ApiTestMixin, self).setUp()
        self.owner = self.factory.makePerson()
        self.pillar = self.factory.makeProduct(owner=self.owner)
        self.grantee = self.factory.makePerson(name='grantee')
        self.grantor = self.factory.makePerson()
        self.grantee_uri = canonical_url(self.grantee, force_local_path=True)
        self.grantor_uri = canonical_url(self.grantor, force_local_path=True)
        transaction.commit()

    def test_getPillarShareeData(self):
        # Test the getPillarShareeData method.
        [json_data] = self._getPillarShareeData()
        self.assertEqual('grantee', json_data['name'])
        self.assertEqual(
            {InformationType.USERDATA.name: SharingPermission.ALL.name},
            json_data['permissions'])


class TestWebService(ApiTestMixin, WebServiceTestCase):
    """Test the web service interface for the Sharing Service."""

    def setUp(self):
        super(TestWebService, self).setUp()
        self.webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')
        self._sharePillarInformation()

    def test_url(self):
        # Test that the url for the service is correct.
        service = SharingService()
        root_app = getUtility(ILaunchpadRoot)
        self.assertEqual(
            '%s+services/sharing' % canonical_url(root_app),
            canonical_url(service))

    def _named_get(self, api_method, **kwargs):
        return self.webservice.named_get(
            '/+services/sharing',
            api_method, api_version='devel', **kwargs).jsonBody()

    def _named_post(self, api_method, **kwargs):
        return self.webservice.named_post(
            '/+services/sharing',
            api_method, api_version='devel', **kwargs).jsonBody()

    def _getPillarShareeData(self):
        pillar_uri = canonical_url(self.pillar, force_local_path=True)
        return self._named_get(
            'getPillarShareeData', pillar=pillar_uri)

    def _sharePillarInformation(self):
        pillar_uri = canonical_url(self.pillar, force_local_path=True)
        with FeatureFixture(WRITE_FLAG):
            return self._named_post(
                'sharePillarInformation', pillar=pillar_uri,
                sharee=self.grantee_uri,
                permissions={
                    InformationType.USERDATA.title:
                    SharingPermission.ALL.title},
                user=self.grantor_uri)


class TestLaunchpadlib(ApiTestMixin, TestCaseWithFactory):
    """Test launchpadlib access for the Sharing Service."""

    layer = AppServerLayer

    def setUp(self):
        super(TestLaunchpadlib, self).setUp()
        self.launchpad = self.factory.makeLaunchpadService(person=self.owner)
        self.service = self.launchpad.load('+services/sharing')
        flag = FeatureFixture(WRITE_FLAG)
        flag.setUp()
        self.addCleanup(flag.cleanUp)
        transaction.commit()
        self._sharePillarInformation()

    def _getPillarShareeData(self):
        ws_pillar = ws_object(self.launchpad, self.pillar)
        return self.service.getPillarShareeData(pillar=ws_pillar)

    def _sharePillarInformation(self):
        ws_pillar = ws_object(self.launchpad, self.pillar)
        ws_grantee = ws_object(self.launchpad, self.grantee)
        return self.service.sharePillarInformation(pillar=ws_pillar,
            sharee=ws_grantee,
            permissions={
                InformationType.USERDATA.title: SharingPermission.ALL.title}
        )
