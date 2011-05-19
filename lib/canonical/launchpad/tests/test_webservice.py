# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for webservice publishing."""

__metaclass__ = type


from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestWebServiceAccess(TestCaseWithFactory):
    """Tests related to web service access."""

    layer = DatabaseFunctionalLayer

    def test_webservice_unathorized_user_agent(self):
        # Creates a broken, unknown client.
        webservice = LaunchpadWebServiceCaller('unknown', 'nothing')
        # Does not matter what object we request for this test.
        response = webservice.get('/bugs/1')
        self.assertEqual(response.status, 401)
        self.assertEqual(response.getheader('x-lazr-oopsid'), None)
