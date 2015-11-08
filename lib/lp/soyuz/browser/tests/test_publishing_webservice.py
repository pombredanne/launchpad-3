# Copyright 2011-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test webservice methods related to the publisher."""

from functools import partial

from lp.services.librarian.browser import ProxiedLibraryFileAlias
from lp.services.webapp.interfaces import OAuthPermission
from lp.testing import (
    api_url,
    login_person,
    person_logged_in,
    record_two_runs,
    TestCaseWithFactory,
    )
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.matchers import HasQueryCount
from lp.testing.pages import webservice_for_person


class SourcePackagePublishingHistoryWebserviceTests(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def make_spph_for(self, person):
        with person_logged_in(person):
            spr = self.factory.makeSourcePackageRelease()
            self.factory.makeSourcePackageReleaseFile(sourcepackagerelease=spr)
            spph = self.factory.makeSourcePackagePublishingHistory(
                sourcepackagerelease=spr)
            return spph, api_url(spph)

    def test_sourceFileUrls(self):
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        spph, url = self.make_spph_for(person)

        response = webservice.named_get(
            url, 'sourceFileUrls', api_version='devel')

        self.assertEqual(200, response.status)
        urls = response.jsonBody()
        with person_logged_in(person):
            sprf = spph.sourcepackagerelease.files[0]
            expected_urls = [
                ProxiedLibraryFileAlias(
                    sprf.libraryfile, spph.archive).http_url]
        self.assertEqual(expected_urls, urls)

    def test_sourceFileUrls_include_meta(self):
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        spph, url = self.make_spph_for(person)

        def create_file():
            self.factory.makeSourcePackageReleaseFile(
                sourcepackagerelease=spph.sourcepackagerelease)

        def get_urls():
            return webservice.named_get(
                url, 'sourceFileUrls', include_meta=True, api_version='devel')

        recorder1, recorder2 = record_two_runs(
            get_urls, create_file, 2,
            login_method=partial(login_person, person), record_request=True)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

        response = get_urls()
        self.assertEqual(200, response.status)
        info = response.jsonBody()
        with person_logged_in(person):
            expected_info = [{
                "url": ProxiedLibraryFileAlias(
                    sprf.libraryfile, spph.archive).http_url,
                "size": sprf.libraryfile.content.filesize,
                "sha256": sprf.libraryfile.content.sha256,
                } for sprf in spph.sourcepackagerelease.files]
        self.assertContentEqual(expected_info, info)


class BinaryPackagePublishingHistoryWebserviceTests(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def make_bpph_for(self, person):
        with person_logged_in(person):
            bpr = self.factory.makeBinaryPackageRelease()
            self.factory.makeBinaryPackageFile(binarypackagerelease=bpr)
            bpph = self.factory.makeBinaryPackagePublishingHistory(
                binarypackagerelease=bpr)
            return bpph, api_url(bpph)

    def test_binaryFileUrls(self):
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        bpph, url = self.make_bpph_for(person)

        response = webservice.named_get(
            url, 'binaryFileUrls', api_version='devel')

        self.assertEqual(200, response.status)
        urls = response.jsonBody()
        with person_logged_in(person):
            bpf = bpph.binarypackagerelease.files[0]
            expected_urls = [
                ProxiedLibraryFileAlias(
                    bpf.libraryfile, bpph.archive).http_url]
        self.assertEqual(expected_urls, urls)

    def test_binaryFileUrls_include_meta(self):
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        bpph, url = self.make_bpph_for(person)

        def create_file():
            self.factory.makeBinaryPackageFile(
                binarypackagerelease=bpph.binarypackagerelease)

        def get_urls():
            return webservice.named_get(
                url, 'binaryFileUrls', include_meta=True, api_version='devel')

        recorder1, recorder2 = record_two_runs(
            get_urls, create_file, 2,
            login_method=partial(login_person, person), record_request=True)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

        response = get_urls()
        self.assertEqual(200, response.status)
        info = response.jsonBody()
        with person_logged_in(person):
            expected_info = [{
                "url": ProxiedLibraryFileAlias(
                    bpf.libraryfile, bpph.archive).http_url,
                "size": bpf.libraryfile.content.filesize,
                "sha1": bpf.libraryfile.content.sha1,
                "sha256": bpf.libraryfile.content.sha256,
                } for bpf in bpph.binarypackagerelease.files]
        self.assertContentEqual(expected_info, info)
