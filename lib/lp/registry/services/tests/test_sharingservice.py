# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

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


class TestSharingService(TestCaseWithFactory):
    """Tests for the SharingService."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSharingService, self).setUp()
        self.service = getUtility(IService, 'sharing')

    def _makeShareeData(self, sharee, policy_types):
        # Unpack an sharee into its attributes and add in permissions.
        request = get_current_web_service_request()
        resource = EntryResource(sharee, request)
        sharee_data = resource.toDataForJSON()
        permissions = {}
        for policy in policy_types:
            permissions[policy.name] = SharingPermission.ALL.name
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
        self.factory.makeAccessPolicyGrant(access_policy, grantee)
        [sharee] = self.service.getPillarSharees(pillar)
        person_data = self._makeShareeData(
            grantee, [InformationType.PROPRIETARY])
        self.assertEqual(person_data, sharee)

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

    def _test_updatePillarSharee(self, pillar):
        """updatePillarSharees works and returns the expected data."""
        sharee = self.factory.makePerson()
        grantor = self.factory.makePerson()

        # Make existing grants to ensure updatePillarSharee handles those
        # cases correctly.
        # First, a grant that is in the add set - it wil be retained.
        policy = self.factory.makeAccessPolicy(
            pillar=pillar, type=InformationType.EMBARGOEDSECURITY)
        self.factory.makeAccessPolicyGrant(
            policy, grantee=sharee, grantor=grantor)
        # Second, a grant that is not in the add set - it will be deleted.
        policy = self.factory.makeAccessPolicy(
            pillar=pillar, type=InformationType.PROPRIETARY)
        self.factory.makeAccessPolicyGrant(
            policy, grantee=sharee, grantor=grantor)

        # Now call updatePillarSharee will the grants we want.
        information_types = [
            InformationType.EMBARGOEDSECURITY,
            InformationType.USERDATA]
        sharee_data = self.service.updatePillarSharee(
            pillar, sharee, information_types, grantor)
        policies = getUtility(IAccessPolicySource).findByPillar([pillar])
        policy_grant_source = getUtility(IAccessPolicyGrantSource)
        grants = policy_grant_source.findByPolicy(policies)
        self.assertEqual(grants.count(), len(information_types))
        for grant in grants:
            self.assertEqual(grantor, grant.grantor)
            self.assertEqual(sharee, grant.grantee)
            self.assertIn(grant.policy.type, information_types)
        expected_sharee_data = self._makeShareeData(
            sharee, information_types)
        self.assertEqual(expected_sharee_data, sharee_data)

    def test_updateProjectGroupSharee_not_allowed(self):
        # We cannot add sharees to ProjectGroups.
        owner = self.factory.makePerson()
        project_group = self.factory.makeProject(owner=owner)
        sharee = self.factory.makePerson()
        login_person(owner)
        self.assertRaises(
            AssertionError, self.service.updatePillarSharee,
            project_group, sharee, [InformationType.USERDATA], owner)

    def test_updateProductSharee(self):
        # Users with launchpad.Edit can add sharees.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)
        self._test_updatePillarSharee(product)

    def test_updateDistroSharee(self):
        # Users with launchpad.Edit can add sharees.
        owner = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=owner)
        login_person(owner)
        self._test_updatePillarSharee(distro)

    def _test_updatePillarShareeUnauthorized(self, pillar):
        # updatePillarSharee raises an Unauthorized exception if the user is
        # not permitted to do so.
        sharee = self.factory.makePerson()
        user = self.factory.makePerson()
        self.assertRaises(
            Unauthorized, self.service.updatePillarSharee,
            pillar, sharee, [InformationType.USERDATA], user)

    def test_updatePillarShareeAnonymous(self):
        # Anonymous users are not allowed.
        product = self.factory.makeProduct()
        login(ANONYMOUS)
        self._test_updatePillarShareeUnauthorized(product)

    def test_updatePillarShareeAnyone(self):
        # Unauthorized users are not allowed.
        product = self.factory.makeProduct()
        login_person(self.factory.makePerson())
        self._test_updatePillarShareeUnauthorized(product)

    def _test_deletePillarSharee(self, pillar, types_to_delete=None):
        # Make grants for some information types.
        information_types = [
            InformationType.EMBARGOEDSECURITY,
            InformationType.USERDATA]
        access_policies = []
        for info_type in information_types:
            access_policy = self.factory.makeAccessPolicy(
                pillar=pillar, type=info_type)
            access_policies.append(access_policy)
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
        self.service.deletePillarSharee(pillar, grantee, types_to_delete)
        # Assemble the expected data for the remaining access grants for
        # grantee.
        expected_data = []
        if types_to_delete is not None:
            expected_information_types = (
                set(information_types).difference(types_to_delete))
            remaining_grantee_person_data = self._makeShareeData(
                grantee, expected_information_types)
            expected_data.append(remaining_grantee_person_data)
        # Add the data for the other sharee.
        another_person_data = self._makeShareeData(
            another, information_types[:1])
        expected_data.append(another_person_data)
        self.assertContentEqual(
            expected_data, self.service.getPillarSharees(pillar))

    def test_deleteProductShareeAll(self):
        # Users with launchpad.Edit can delete all access for an sharee.
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
        # Users with launchpad.Edit can delete all access for an sharee.
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


class ApiTestMixin:
    """Common tests for launchpadlib and webservice."""

    def setUp(self):
        super(ApiTestMixin, self).setUp()
        self.driver = self.factory.makePerson()
        self.pillar = self.factory.makeProduct(driver=self.driver)
        access_policy = self.factory.makeAccessPolicy(pillar=self.pillar)
        self.grantee = self.factory.makePerson(name='grantee')
        self.factory.makeAccessPolicyGrant(
            policy=access_policy, grantee=self.grantee)
        transaction.commit()

    def test_getPillarSharees(self):
        # Test the getPillarSharees method.
        [json_data] = self._getPillarSharees()
        self.assertEqual('grantee', json_data['name'])
        self.assertIn('permissions', json_data)


class TestWebService(ApiTestMixin, WebServiceTestCase):
    """Test the web service interface for the Access Policy Service."""

    def setUp(self):
        super(TestWebService, self).setUp()
        self.webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')

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

    def _getPillarSharees(self):
        pillar_uri = canonical_url(self.pillar, force_local_path=True)
        return self._named_get(
            'getPillarSharees', pillar=pillar_uri)


class TestLaunchpadlib(ApiTestMixin, TestCaseWithFactory):
    """Test launchpadlib access for the Access Policy Service."""

    layer = AppServerLayer

    def setUp(self):
        super(TestLaunchpadlib, self).setUp()
        self.launchpad = self.factory.makeLaunchpadService(person=self.driver)

    def _getPillarSharees(self):
        # XXX 2012-02-23 wallyworld bug 681767
        # Launchpadlib can't do relative url's
        service = self.launchpad.load(
            '%s/+services/sharing' % self.launchpad._root_uri)
        ws_pillar = ws_object(self.launchpad, self.pillar)
#        login_person(self.driver)
        return service.getPillarSharees(pillar=ws_pillar)
