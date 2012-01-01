# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test webservice methods related to the publisher."""

from lp.services.webapp.interfaces import OAuthPermission
from lp.testing import (
    api_url,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.pages import webservice_for_person


class BinaryPackagePublishingHistoryWebserviceTests(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_binaryFileUrls(self):
        bpr = self.factory.makeBinaryPackageRelease()
        self.factory.makeBinaryPackageFile(binarypackagerelease=bpr)
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr)
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        with person_logged_in(person):
            bpph_url = api_url(bpph)
        response = webservice.named_get(
            bpph_url, 'binaryFileUrls', api_version='devel')
        self.assertEqual(200, response.status)
        urls = response.jsonBody()
        self.assertEqual(1, len(urls))
