# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import simplejson

from zope.component import getUtility

from lp.app.enums import InformationVisibilityPolicy
from lp.registry.services.accesspolicyservice import AccessPolicyService
from lp.services.webapp.interfaces import ILaunchpadRoot
from lp.services.webapp.publisher import canonical_url
from lp.testing import WebServiceTestCase
from lp.testing.pages import LaunchpadWebServiceCaller


class TestWebService(WebServiceTestCase):
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
            '%sservices/accesspolicy' % canonical_url(root_app),
            canonical_url(service))

    def _named_get(self, api_method, **kwargs):
        return self.webservice.named_get(
            '/services/accesspolicy',
            api_method, api_version='devel', **kwargs).jsonBody()

    def test_getAccessPolicies(self):
        # Test the getAccessPolicies method.
        json_policies = self._named_get('getAccessPolicies')
        policies = simplejson.loads(json_policies)
        expected_polices = []
        for x, policy in enumerate(InformationVisibilityPolicy):
            item = dict(
                index=x,
                value=policy.token,
                title=policy.title,
                description=policy.value.description
            )
            expected_polices.append(item)
        self.assertContentEqual(expected_polices, policies)
