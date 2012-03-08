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
from lp.registry.services.accesspolicyservice import AccessPolicyService
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


class TestAccessPolicyService(TestCaseWithFactory):
    """Tests for the AccessPolicyService."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestAccessPolicyService, self).setUp()
        self.service = getUtility(IService, 'accesspolicy')

    def _makeObserverData(self, observer, policy_types):
        # Unpack an observer into its attributes and add in permissions.
        request = get_current_web_service_request()
        resource = EntryResource(observer, request)
        observer_data = resource.toDataForJSON()
        permissions = {}
        for policy in policy_types:
            permissions[policy.name] = SharingPermission.ALL.name
        observer_data['permissions'] = permissions
        return observer_data

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

    def _test_getPillarObservers(self, pillar):
        # getPillarObservers returns the expected data.
        access_policy = self.factory.makeAccessPolicy(
            pillar=pillar,
            type=InformationType.PROPRIETARY)
        grantee = self.factory.makePerson()
        self.factory.makeAccessPolicyGrant(access_policy, grantee)
        [observer] = self.service.getPillarObservers(pillar)
        person_data = self._makeObserverData(
            grantee, [InformationType.PROPRIETARY])
        self.assertEqual(person_data, observer)

    def test_getProductObservers(self):
        # Users with launchpad.Driver can view observers.
        driver = self.factory.makePerson()
        product = self.factory.makeProduct(driver=driver)
        login_person(driver)
        self._test_getPillarObservers(product)

    def test_getDistroObservers(self):
        # Users with launchpad.Driver can view observers.
        driver = self.factory.makePerson()
        distro = self.factory.makeDistribution(driver=driver)
        login_person(driver)
        self._test_getPillarObservers(distro)

    def _test_getPillarObserversUnauthorized(self, pillar):
        # getPillarObservers raises an Unauthorized exception if the user is
        # not permitted to do so.
        access_policy = self.factory.makeAccessPolicy(pillar=pillar)
        grantee = self.factory.makePerson()
        self.factory.makeAccessPolicyGrant(access_policy, grantee)
        self.assertRaises(
            Unauthorized, self.service.getPillarObservers, pillar)

    def test_getPillarObserversAnonymous(self):
        # Anonymous users are not allowed.
        product = self.factory.makeProduct()
        login(ANONYMOUS)
        self._test_getPillarObserversUnauthorized(product)

    def test_getPillarObserversAnyone(self):
        # Unauthorized users are not allowed.
        product = self.factory.makeProduct()
        login_person(self.factory.makePerson())
        self._test_getPillarObserversUnauthorized(product)

    def _test_updatePillarObserver(self, pillar):
        """updatePillarObservers works and returns the expected data."""
        observer = self.factory.makePerson()
        grantor = self.factory.makePerson()

        # Make existing grants to ensure updatePillarObserver handles those
        # cases correctly.
        # First, a grant that is in the add set - it wil be retained.
        policy = self.factory.makeAccessPolicy(
            pillar=pillar, type=InformationType.EMBARGOEDSECURITY)
        self.factory.makeAccessPolicyGrant(
            policy, grantee=observer, grantor=grantor)
        # Second, a grant that is not in the add set - it will be deleted.
        policy = self.factory.makeAccessPolicy(
            pillar=pillar, type=InformationType.PROPRIETARY)
        self.factory.makeAccessPolicyGrant(
            policy, grantee=observer, grantor=grantor)

        # Now call updatePillarObserver will the grants we want.
        information_types = [
            InformationType.EMBARGOEDSECURITY,
            InformationType.USERDATA]
        observer_data = self.service.updatePillarObserver(
            pillar, observer, information_types, grantor)
        policies = getUtility(IAccessPolicySource).findByPillar([pillar])
        policy_grant_source = getUtility(IAccessPolicyGrantSource)
        grants = policy_grant_source.findByPolicy(policies)
        self.assertEqual(grants.count(), len(information_types))
        for grant in grants:
            self.assertEqual(grantor, grant.grantor)
            self.assertEqual(observer, grant.grantee)
            self.assertIn(grant.policy.type, information_types)
        expected_observer_data = self._makeObserverData(
            observer, information_types)
        self.assertEqual(expected_observer_data, observer_data)

    def test_updateProjectGroupObserver_not_allowed(self):
        # We cannot add observers to ProjectGroups.
        owner = self.factory.makePerson()
        project_group = self.factory.makeProject(owner=owner)
        observer = self.factory.makePerson()
        login_person(owner)
        self.assertRaises(
            AssertionError, self.service.updatePillarObserver,
            project_group, observer, [InformationType.USERDATA], owner)

    def test_updateProductObserver(self):
        # Users with launchpad.Edit can add observers.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)
        self._test_updatePillarObserver(product)

    def test_updateDistroObserver(self):
        # Users with launchpad.Edit can add observers.
        owner = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=owner)
        login_person(owner)
        self._test_updatePillarObserver(distro)

    def _test_updatePillarObserverUnauthorized(self, pillar):
        # updatePillarObserver raises an Unauthorized exception if the user is
        # not permitted to do so.
        observer = self.factory.makePerson()
        user = self.factory.makePerson()
        self.assertRaises(
            Unauthorized, self.service.updatePillarObserver,
            pillar, observer, [InformationType.USERDATA], user)

    def test_updatePillarObserverAnonymous(self):
        # Anonymous users are not allowed.
        product = self.factory.makeProduct()
        login(ANONYMOUS)
        self._test_updatePillarObserverUnauthorized(product)

    def test_updatePillarObserverAnyone(self):
        # Unauthorized users are not allowed.
        product = self.factory.makeProduct()
        login_person(self.factory.makePerson())
        self._test_updatePillarObserverUnauthorized(product)

    def _test_deletePillarObserver(self, pillar, types_to_delete=None):
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
        # Make some access policy grants for our observer.
        for access_policy in access_policies:
            self.factory.makeAccessPolicyGrant(access_policy, grantee)
        # Make some artifact grants for our observer.
        artifact = self.factory.makeAccessArtifact()
        self.factory.makeAccessArtifactGrant(artifact, grantee)
        for access_policy in access_policies:
            self.factory.makeAccessPolicyArtifact(
                artifact=artifact, policy=access_policy)
        # Make some access policy grants for another observer.
        another = self.factory.makePerson()
        self.factory.makeAccessPolicyGrant(access_policies[0], another)
        # Delete data for a specific information type.
        self.service.deletePillarObserver(pillar, grantee, types_to_delete)
        # Assemble the expected data for the remaining access grants for
        # grantee.
        expected_data = []
        if types_to_delete is not None:
            expected_information_types = (
                set(information_types).difference(types_to_delete))
            remaining_grantee_person_data = self._makeObserverData(
                grantee, expected_information_types)
            expected_data.append(remaining_grantee_person_data)
        # Add the data for the other observer.
        another_person_data = self._makeObserverData(
            another, information_types[:1])
        expected_data.append(another_person_data)
        self.assertContentEqual(
            expected_data, self.service.getPillarObservers(pillar))

    def test_deleteProductObserverAll(self):
        # Users with launchpad.Edit can delete all access for an observer.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)
        self._test_deletePillarObserver(product)

    def test_deleteProductObserverPolicies(self):
        # Users with launchpad.Edit can delete selected policy access for an
        # observer.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)
        self._test_deletePillarObserver(product, [InformationType.USERDATA])

    def test_deleteDistroObserverAll(self):
        # Users with launchpad.Edit can delete all access for an observer.
        owner = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=owner)
        login_person(owner)
        self._test_deletePillarObserver(distro)

    def test_deleteDistroObserverPolicies(self):
        # Users with launchpad.Edit can delete selected policy access for an
        # observer.
        owner = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=owner)
        login_person(owner)
        self._test_deletePillarObserver(distro, [InformationType.USERDATA])


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

    def test_getPillarObservers(self):
        # Test the getPillarObservers method.
        [json_data] = self._getPillarObservers()
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
        service = AccessPolicyService()
        root_app = getUtility(ILaunchpadRoot)
        self.assertEqual(
            '%s+services/accesspolicy' % canonical_url(root_app),
            canonical_url(service))

    def _named_get(self, api_method, **kwargs):
        return self.webservice.named_get(
            '/+services/accesspolicy',
            api_method, api_version='devel', **kwargs).jsonBody()

    def _getPillarObservers(self):
        pillar_uri = canonical_url(self.pillar, force_local_path=True)
        return self._named_get(
            'getPillarObservers', pillar=pillar_uri)


class TestLaunchpadlib(ApiTestMixin, TestCaseWithFactory):
    """Test launchpadlib access for the Access Policy Service."""

    layer = AppServerLayer

    def setUp(self):
        super(TestLaunchpadlib, self).setUp()
        self.launchpad = self.factory.makeLaunchpadService(person=self.driver)

    def _getPillarObservers(self):
        # XXX 2012-02-23 wallyworld bug 681767
        # Launchpadlib can't do relative url's
        service = self.launchpad.load(
            '%s/+services/accesspolicy' % self.launchpad._root_uri)
        ws_pillar = ws_object(self.launchpad, self.pillar)
#        login_person(self.driver)
        return service.getPillarObservers(pillar=ws_pillar)
