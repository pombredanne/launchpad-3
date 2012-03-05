# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import transaction

from lazr.restful import EntryResource
from lazr.restful.utils import get_current_web_service_request
from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from lp.app.interfaces.services import IService
from lp.registry.enums import AccessPolicyType, SharingPermission
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
    ws_object)
from lp.testing.layers import AppServerLayer, DatabaseFunctionalLayer
from lp.testing.pages import LaunchpadWebServiceCaller


class TestAccessPolicyService(TestCaseWithFactory):
    """Tests for the AccessPolicyService."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestAccessPolicyService, self).setUp()
        self.service = getUtility(IService, 'accesspolicy')

    def _makeObserverData(self, observer):
        # Unpack an observer into its attributes and add in permissions.
        request = get_current_web_service_request()
        resource = EntryResource(observer, request)
        observer_data = resource.toDataForJSON()
        observer_data['permissions'] = {
            AccessPolicyType.PROPRIETARY.name: SharingPermission.ALL.name}
        return observer_data

    def _test_getAccessPolicies(self, pillar, expected_policies):
        policy_data = self.service.getAccessPolicies(pillar)
        expected_data = []
        for x, policy in enumerate(expected_policies):
            item = dict(
                index=x,
                value=policy.value,
                title=policy.title,
                description=policy.description
            )
            expected_data.append(item)
        self.assertContentEqual(expected_data, policy_data)

    def test_getAccessPolicies_product(self):
        product = self.factory.makeProduct()
        self._test_getAccessPolicies(
            product,
            [AccessPolicyType.EMBARGOEDSECURITY, AccessPolicyType.USERDATA])

    def test_getAccessPolicies_expired_commercial_product(self):
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product, expired=True)
        self._test_getAccessPolicies(
            product,
            [AccessPolicyType.EMBARGOEDSECURITY, AccessPolicyType.USERDATA])

    def test_getAccessPolicies_commercial_product(self):
        product = self.factory.makeProduct()
        self.factory.makeCommercialSubscription(product)
        self._test_getAccessPolicies(
            product,
            [AccessPolicyType.EMBARGOEDSECURITY,
             AccessPolicyType.USERDATA,
             AccessPolicyType.PROPRIETARY])

    def test_getAccessPolicies_distro(self):
        distro = self.factory.makeDistribution()
        self._test_getAccessPolicies(
            distro,
            [AccessPolicyType.EMBARGOEDSECURITY, AccessPolicyType.USERDATA])

    def _test_getPillarObservers(self, pillar):
        # getPillarObservers returns the expected data.
        access_policy = self.factory.makeAccessPolicy(pillar=pillar)
        grantee = self.factory.makePerson()
        self.factory.makeAccessPolicyGrant(access_policy, grantee)
        [observer] = self.service.getPillarObservers(pillar)
        person_data = self._makeObserverData(grantee)
        self.assertContentEqual(person_data, observer)

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

    def _test_addPillarObserver(self, pillar):
        """addPillarObservers works and returns the expected data."""
        observer = self.factory.makePerson()
        access_policy_type = AccessPolicyType.USERDATA
        user = self.factory.makePerson()
        observer_data = self.service.addPillarObserver(
            pillar, observer, access_policy_type, user)
        [policy] = getUtility(IAccessPolicySource).findByPillar([pillar])
        policy_grant_source = getUtility(IAccessPolicyGrantSource)
        [grant] = policy_grant_source.findByPolicy([policy])
        self.assertEqual(user, grant.grantor)
        self.assertEqual(observer, grant.grantee)
        self.assertEqual(policy, grant.policy)
        expected_observer_data = self._makeObserverData(observer)
        self.assertContentEqual(expected_observer_data, observer_data)

    def test_addProjectGroupObserver_not_allowed(self):
        # We cannot add observers to ProjectGroups.
        owner = self.factory.makePerson()
        project_group = self.factory.makeProject(owner=owner)
        login_person(owner)
        self.assertRaises(
            AssertionError, self._test_addPillarObserver, project_group)

    def test_addProductObserver(self):
        # Users with launchpad.Edit can add observers.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        login_person(owner)
        self._test_addPillarObserver(product)

    def test_addDistroObserver(self):
        # Users with launchpad.Edit can add observers.
        owner = self.factory.makePerson()
        distro = self.factory.makeDistribution(owner=owner)
        login_person(owner)
        self._test_addPillarObserver(distro)

    def _test_addPillarObserverUnauthorized(self, pillar):
        # addPillarObserver raises an Unauthorized exception if the user is
        # not permitted to do so.
        observer = self.factory.makePerson()
        access_policy_type = AccessPolicyType.USERDATA
        user = self.factory.makePerson()
        self.assertRaises(
            Unauthorized, self.service.addPillarObserver,
            pillar, observer, access_policy_type, user)

    def test_addPillarObserverAnonymous(self):
        # Anonymous users are not allowed.
        product = self.factory.makeProduct()
        login(ANONYMOUS)
        self._test_addPillarObserverUnauthorized(product)

    def test_addPillarObserverAnyone(self):
        # Unauthorized users are not allowed.
        product = self.factory.makeProduct()
        login_person(self.factory.makePerson())
        self._test_addPillarObserverUnauthorized(product)


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
