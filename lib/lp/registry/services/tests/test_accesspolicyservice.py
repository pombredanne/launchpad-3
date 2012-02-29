# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import simplejson
from lazr.restful import EntryResource
from lazr.restful.utils import get_current_web_service_request
from zope.component import getUtility

from lp.app.interfaces.services import IService
from lp.registry.enums import AccessPolicyType, SharingPermission
from lp.registry.interfaces.accesspolicy import (
    IAccessPolicyGrantSource,
    IAccessPolicySource,
    )
from lp.registry.services.accesspolicyservice import AccessPolicyService
from lp.services.webapp.interfaces import ILaunchpadRoot
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    TestCaseWithFactory,
    WebServiceTestCase,
    )
from lp.testing.layers import AppServerLayer, DatabaseFunctionalLayer
from lp.testing.pages import LaunchpadWebServiceCaller


class TestAccessPolicyService(TestCaseWithFactory):
    """Tests for the AccessPolicyService."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestAccessPolicyService, self).setUp()
        self.service = getUtility(IService, 'accesspolicy')

    def _makeObserverData(self, observer):
        # Unpack an observer into it's attributes and add in permissions.
        request = get_current_web_service_request()
        resource = EntryResource(observer, request)
        observer_data = resource.toDataForJSON()
        observer_data['permissions'] = {
            AccessPolicyType.PROPRIETARY.name: SharingPermission.ALL.name}
        return observer_data

    def _test_getPillarObservers(self, pillar):
        """getPillarObservers returns the expected data."""
        access_policy = self.factory.makeAccessPolicy(pillar=pillar)
        grantee = self.factory.makePerson()
        self.factory.makeAccessPolicyGrant(access_policy, grantee)
        [observer] = self.service.getPillarObservers(pillar)
        person_data = self._makeObserverData(grantee)
        self.assertContentEqual(person_data, observer)

    def test_getProductObservers(self):
        product = self.factory.makeProduct()
        self._test_getPillarObservers(product)

    def test_getDistroObservers(self):
        distro = self.factory.makeDistribution()
        self._test_getPillarObservers(distro)

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

    def test_addProductObserver(self):
        product = self.factory.makeProduct()
        self._test_addPillarObserver(product)

    def test_addDistroObserver(self):
        distro = self.factory.makeDistribution()
        self._test_addPillarObserver(distro)


class ApiTestMixin:
    """Common tests for launchpadlib and webservice."""

    def test_getAccessPolicies(self):
        # Test the getAccessPolicies method.
        json_policies = self._getAccessPolicies()
        policies = simplejson.loads(json_policies)
        expected_polices = []
        for x, policy in enumerate(AccessPolicyType):
            item = dict(
                index=x,
                value=policy.token,
                title=policy.title,
                description=policy.value.description
            )
            expected_polices.append(item)
        self.assertContentEqual(expected_polices, policies)


class TestWebService(WebServiceTestCase, ApiTestMixin):
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

    def _getAccessPolicies(self):
        return self._named_get('getAccessPolicies')


class TestLaunchpadlib(TestCaseWithFactory, ApiTestMixin):
    """Test launchpadlib access for the Access Policy Service."""

    layer = AppServerLayer

    def setUp(self):
        super(TestLaunchpadlib, self).setUp()
        self.launchpad = self.factory.makeLaunchpadService()

    def _getAccessPolicies(self):
        # XXX 2012-02-23 wallyworld bug 681767
        # Launchpadlib can't do relative url's
        service = self.launchpad.load(
            '%s/+services/accesspolicy' % self.launchpad._root_uri)
        return service.getAccessPolicies()
