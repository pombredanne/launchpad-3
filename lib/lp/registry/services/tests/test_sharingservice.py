# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
from lp.services.features.testing import FeatureFixture

__metaclass__ = type


from lazr.restful import EntryResource
from lazr.restful.utils import get_current_web_service_request
import transaction
from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from lp.app.interfaces.services import IService
from lp.registry.enums import (
    InformationType,
    SharingPermission,
    )
from lp.registry.interfaces.accesspolicy import (
    IAccessPolicyGrantSource,
    IAccessPolicySource,
    )
from lp.registry.services.sharingservice import SharingService
from lp.services.webapp.interaction import ANONYMOUS
from lp.services.webapp.interfaces import ILaunchpadRoot
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    login,
    login_person,
    TestCaseWithFactory,
    WebServiceTestCase,
    ws_object,
    )
from lp.testing.layers import (
    AppServerLayer,
    DatabaseFunctionalLayer,
    )
from lp.testing.pages import LaunchpadWebServiceCaller


WRITE_FLAG = {'disclosure.enhanced_sharing.writable': 'true'}


class TestSharingService(TestCaseWithFactory):
    """Tests for the SharingService."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSharingService, self).setUp()
        self.service = getUtility(IService, 'sharing')

    def _makeShareeData(self, sharee, policy_permissions):
        # Unpack a sharee into its attributes and add in permissions.
        request = get_current_web_service_request()
        resource = EntryResource(sharee, request)
        sharee_data = resource.toDataForJSON()
        permissions = {}
        for (policy, permission) in policy_permissions:
            permissions[policy.name] = unicode(permission.name)
        sharee_data['permissions'] = permissions
        return sharee_data

    def _test_getInformationTypes(self, pillar, expected_policies):
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
        self._test_getInformationTypes(
            product,
            [InformationType.EMBARGOEDSECURITY, InformationType.USERDATA])

    def test_getInformationTypes_expired_commercial_product(self):
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product, expired=True)
        self._test_getInformationTypes(
            product,
            [InformationType.EMBARGOEDSECURITY, InformationType.USERDATA])

    def test_getInformationTypes_commercial_product(self):
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product)
        self._test_getInformationTypes(
            product,
            [InformationType.EMBARGOEDSECURITY,
             InformationType.USERDATA,
             InformationType.PROPRIETARY])

    def test_getInformationTypes_distro(self):
        distro = self.factory.makeDistribution()
        self._test_getInformationTypes(
            distro,
            [InformationType.EMBARGOEDSECURITY, InformationType.USERDATA])

    def _test_getPillarSharees(self, pillar):
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
            self._makeShareeData(
                grantee,
                [(InformationType.PROPRIETARY, SharingPermission.ALL)]),
            self._makeShareeData(
                artifact_grant.grantee,
                [(InformationType.PROPRIETARY, SharingPermission.SOME)])]
        self.assertContentEqual(expected_sharees, sharees)

    def test_getProductSharees(self):
        # Users with launchpad.Driver can view sharees.
        driver = self.factory.makePerson()
        product = self.factory.makeProduct(driver=driver)
        login_person(driver)
        self._test_getPillarSharees(product)

    def test_getDistroSharees(self):
        # Users with launchpad.Driver can view sharees.
        driver = self.factory.makePerson()
        distro = self.factory.makeDistribution(driver=driver)
        login_person(driver)
        self._test_getPillarSharees(distro)

    def test_getPillarSharees_filter_grantees(self):
        # getPillarSharees only returns grantees in the specified list.
        driver = self.factory.makePerson()
        pillar = self.factory.makeProduct(driver=driver)
        login_person(driver)
        access_policy = self.factory.makeAccessPolicy(
            pillar=pillar,
            type=InformationType.PROPRIETARY)
        grantee_in_result = self.factory.makePerson()
        grantee_not_in_result = self.factory.makePerson()
        self.factory.makeAccessPolicyGrant(access_policy, grantee_in_result)
        self.factory.makeAccessPolicyGrant(
            access_policy, grantee_not_in_result)

        sharees = self.service.getPillarSharees(pillar, [grantee_in_result])
        expected_sharees = [
            self._makeShareeData(
                grantee_in_result,
                [(InformationType.PROPRIETARY, SharingPermission.ALL)])]
        self.assertContentEqual(expected_sharees, sharees)

    def _test_getPillarShareesUnauthorized(self, pillar):
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
        self._test_getPillarShareesUnauthorized(product)

    def test_getPillarShareesAnyone(self):
        # Unauthorized users are not allowed.
        product = self.factory.makeProduct()
        login_person(self.factory.makePerson())
        self._test_getPillarShareesUnauthorized(product)

    def _test_sharePillarInformation(self, pillar):
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
            sharee, expected_permissions)
        self.assertEqual(expected_sharee_data, sharee_data)
        # Check that getPillarSharees returns what we expect.
        [sharee_data] = self.service.getPillarSharees(pillar)
        self.assertEqual(expected_sharee_data, sharee_data)

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
        self._test_sharePillarInformation(product)

    def test_updateDistroSharee(self):
        # Users with launchpad.Edit can add sharees.
        owner = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=owner)
        login_person(owner)
        self._test_sharePillarInformation(distro)

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

    def _test_sharePillarInformationUnauthorized(self, pillar):
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
            self._test_sharePillarInformationUnauthorized(product)

    def test_sharePillarInformationAnyone(self):
        # Unauthorized users are not allowed.
        with FeatureFixture(WRITE_FLAG):
            product = self.factory.makeProduct()
            login_person(self.factory.makePerson())
            self._test_sharePillarInformationUnauthorized(product)

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

    def _test_deletePillarSharee(self, pillar, types_to_delete=None):
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
            self.service.deletePillarSharee(pillar, grantee, types_to_delete)
        # Assemble the expected data for the remaining access grants for
        # grantee.
        expected_data = []
        if types_to_delete is not None:
            expected_information_types = (
                set(information_types).difference(types_to_delete))
            remaining_grantee_person_data = self._makeShareeData(
                grantee,
                [(info_type, SharingPermission.ALL)
                for info_type in expected_information_types])

            expected_data.append(remaining_grantee_person_data)
        # Add the data for the other sharee.
        another_person_data = self._makeShareeData(
            another, [(information_types[0], SharingPermission.ALL)])
        expected_data.append(another_person_data)
        self.assertContentEqual(
            expected_data, self.service.getPillarSharees(pillar))

    def test_deleteProductShareeAll(self):
        # Users with launchpad.Edit can delete all access for a sharee.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)
        self._test_deletePillarSharee(product)

    def test_deleteProductShareeSelectedPolicies(self):
        # Users with launchpad.Edit can delete selected policy access for an
        # sharee.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)
        self._test_deletePillarSharee(product, [InformationType.USERDATA])

    def test_deleteDistroShareeAll(self):
        # Users with launchpad.Edit can delete all access for a sharee.
        owner = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=owner)
        login_person(owner)
        self._test_deletePillarSharee(distro)

    def test_deleteDistroShareeSelectedPolicies(self):
        # Users with launchpad.Edit can delete selected policy access for an
        # sharee.
        owner = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=owner)
        login_person(owner)
        self._test_deletePillarSharee(distro, [InformationType.USERDATA])

    def _test_deletePillarShareeUnauthorized(self, pillar):
        # deletePillarSharee raises an Unauthorized exception if the user
        # is not permitted to do so.
        with FeatureFixture(WRITE_FLAG):
            self.assertRaises(
                Unauthorized, self.service.deletePillarSharee,
                pillar, [InformationType.USERDATA])

    def test_deletePillarShareeAnonymous(self):
        # Anonymous users are not allowed.
        with FeatureFixture(WRITE_FLAG):
            product = self.factory.makeProduct()
            login(ANONYMOUS)
            self._test_deletePillarShareeUnauthorized(product)

    def test_deletePillarShareeAnyone(self):
        # Unauthorized users are not allowed.
        with FeatureFixture(WRITE_FLAG):
            product = self.factory.makeProduct()
            login_person(self.factory.makePerson())
            self._test_deletePillarShareeUnauthorized(product)

    def test_deletePillarSharee_without_flag(self):
        # The feature flag needs to be enabled.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)
        self.assertRaises(
            Unauthorized, self.service.deletePillarSharee,
            product, [InformationType.USERDATA])


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

    def test_getPillarSharees(self):
        # Test the getPillarSharees method.
        [json_data] = self._getPillarSharees()
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

    def _getPillarSharees(self):
        pillar_uri = canonical_url(self.pillar, force_local_path=True)
        return self._named_get(
            'getPillarSharees', pillar=pillar_uri)

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
        # XXX 2012-02-23 wallyworld bug 681767
        # Launchpadlib can't do relative url's
        self.service = self.launchpad.load(
            '%s/+services/sharing' % self.launchpad._root_uri)
        self._sharePillarInformation()

    def _getPillarSharees(self):
        ws_pillar = ws_object(self.launchpad, self.pillar)
        return self.service.getPillarSharees(pillar=ws_pillar)

    def _sharePillarInformation(self):
        ws_pillar = ws_object(self.launchpad, self.pillar)
        ws_grantee = ws_object(self.launchpad, self.grantee)
        with FeatureFixture(WRITE_FLAG):
            return self.service.sharePillarInformation(pillar=ws_pillar,
                sharee=ws_grantee,
                permissions={
                    InformationType.USERDATA.title:
                    SharingPermission.ALL.title}
            )
