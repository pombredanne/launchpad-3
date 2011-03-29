# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestProductAlias(TestCaseWithFactory):
    """Aliases should behave well with the webservice."""

    layer = DatabaseFunctionalLayer

    def test_alias_redirects_in_webservice(self):
        # When a redirect occurs for a product, it should remain in the
        # webservice.
        product = self.factory.makeProduct(name='lemur')
        removeSecurityProxy(product).setAliases(['monkey'])
        webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')
        response = webservice.get('/monkey')
        self.assertEqual(
            'http://api.launchpad.dev/beta/lemur',
            response.getheader('location'))
