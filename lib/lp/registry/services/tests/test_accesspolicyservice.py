# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import simplejson
from zope.component import getUtility

from lp.registry.enums import AccessPolicyType
from lp.registry.services.accesspolicyservice import AccessPolicyService
from lp.services.webapp.interfaces import ILaunchpadRoot
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    TestCaseWithFactory,
    WebServiceTestCase,
    )
from lp.testing.layers import AppServerLayer
from lp.testing.pages import LaunchpadWebServiceCaller


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
