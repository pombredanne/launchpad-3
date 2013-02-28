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
from testtools.matchers import (
    Equals,
    IsInstance,
)


class BinaryPackagePublishingHistoryWebserviceTests(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def make_bpph_url_for(self, person):
        with person_logged_in(person):
            bpr = self.factory.makeBinaryPackageRelease()
            self.factory.makeBinaryPackageFile(binarypackagerelease=bpr)
            bpph = self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr)
            return api_url(bpph)

    def test_binaryFileUrls(self):
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)

        response = webservice.named_get(
            self.make_bpph_url_for(person), 'binaryFileUrls',
            api_version='devel')

        self.assertEqual(200, response.status)
        urls = response.jsonBody()
        self.assertThat(len(urls), Equals(1))
        self.assertTrue(urls[0], IsInstance(unicode))

    def test_binaryFileUrls_include_meta(self):
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)

        response = webservice.named_get(
            self.make_bpph_url_for(person), 'binaryFileUrls',
            include_meta=True, api_version='devel')

        self.assertEqual(200, response.status)
        urls = response.jsonBody()
        self.assertThat(len(urls), Equals(1))
        self.assertThat(urls[0], IsInstance(dict))
