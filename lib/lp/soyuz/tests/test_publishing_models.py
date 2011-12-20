# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test model and set utilities used for publishing."""

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.database.constants import UTC_NOW
from canonical.launchpad.testing.pages import webservice_for_person
from canonical.launchpad.webapp.interfaces import OAuthPermission
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.testing.layers import (
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.app.errors import NotFoundError
from lp.buildmaster.enums import BuildStatus
from lp.soyuz.interfaces.publishing import (
    IPublishingSet,
    PackagePublishingStatus,
    )
from lp.soyuz.enums import BinaryPackageFileType
from lp.soyuz.tests.test_binarypackagebuild import BaseTestCaseWithThreeBuilds
from lp.testing import (
    api_url,
    person_logged_in,
    TestCaseWithFactory,
    )


class TestPublishingSet(BaseTestCaseWithThreeBuilds):
    """Tests the IPublishingSet utility implementation."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Use `SoyuzTestPublisher` to publish some sources in archives."""
        super(TestPublishingSet, self).setUp()

        # Ensure all the builds have been built.
        for build in self.builds:
            removeSecurityProxy(build).status = BuildStatus.FULLYBUILT
        self.publishing_set = getUtility(IPublishingSet)

    def _getBuildsForResults(self, results):
        # The method returns (SPPH, Build) tuples, we just want the build.
        return [result[1] for result in results]

    def test_getUnpublishedBuildsForSources_none_published(self):
        # If no binaries have been published then all builds are.
        results = self.publishing_set.getUnpublishedBuildsForSources(
            self.sources)
        unpublished_builds = self._getBuildsForResults(results)

        self.assertContentEqual(self.builds, unpublished_builds)

    def test_getUnpublishedBuildsForSources_one_published(self):
        # If we publish a binary for a build, it is no longer returned.
        bpr = self.publisher.uploadBinaryForBuild(self.builds[0], 'gedit')
        self.publisher.publishBinaryInArchive(
            bpr, self.sources[0].archive,
            status=PackagePublishingStatus.PUBLISHED)

        results = self.publishing_set.getUnpublishedBuildsForSources(
            self.sources)
        unpublished_builds = self._getBuildsForResults(results)

        self.assertContentEqual(self.builds[1:3], unpublished_builds)

    def test_getUnpublishedBuildsForSources_with_cruft(self):
        # SourcePackages that has a superseded binary are still considered
        # 'published'.

        # Publish the binaries for gedit as superseded, explicitly setting
        # the date published.
        bpr = self.publisher.uploadBinaryForBuild(self.builds[0], 'gedit')
        bpphs = self.publisher.publishBinaryInArchive(
            bpr, self.sources[0].archive,
            status=PackagePublishingStatus.SUPERSEDED)
        for bpph in bpphs:
            bpph.datepublished = UTC_NOW

        results = self.publishing_set.getUnpublishedBuildsForSources(
            self.sources)
        unpublished_builds = self._getBuildsForResults(results)

        # The original gedit build should not be included in the results as,
        # even though it is no longer published.
        self.assertContentEqual(self.builds[1:3], unpublished_builds)

    def test_getChangesFileLFA(self):
        # The getChangesFileLFA() method finds the right LFAs.
        lfas = (
            self.publishing_set.getChangesFileLFA(hist.sourcepackagerelease)
            for hist in self.sources)
        urls = [lfa.http_url for lfa in lfas]
        self.assert_(urls[0].endswith('/94/gedit_666_source.changes'))
        self.assert_(urls[1].endswith('/96/firefox_666_source.changes'))
        self.assert_(urls[2].endswith(
            '/98/getting-things-gnome_666_source.changes'))


class TestSourcePackagePublishingHistory(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_ancestry(self):
        """Ancestry can be traversed."""
        ancestor = self.factory.makeSourcePackagePublishingHistory()
        spph = self.factory.makeSourcePackagePublishingHistory(
            ancestor=ancestor)
        self.assertEquals(spph.ancestor.displayname, ancestor.displayname)

    def test_changelogUrl_missing(self):
        spr = self.factory.makeSourcePackageRelease(changelog=None)
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr)
        self.assertEqual(None, spph.changelogUrl())

    def test_changelogUrl(self):
        spr = self.factory.makeSourcePackageRelease(
            changelog=self.factory.makeChangelog('foo', ['1.0']))
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr)
        self.assertEqual(
            canonical_url(spph) + '/+files/%s' % spr.changelog.filename,
            spph.changelogUrl())

    def test_getFileByName_changelog(self):
        spr = self.factory.makeSourcePackageRelease(
            changelog=self.factory.makeLibraryFileAlias(filename='changelog'))
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr)
        self.assertEqual(spr.changelog, spph.getFileByName('changelog'))

    def test_getFileByName_changelog_absent(self):
        spr = self.factory.makeSourcePackageRelease(changelog=None)
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr)
        self.assertRaises(NotFoundError, spph.getFileByName, 'changelog')

    def test_getFileByName_unhandled_name(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        self.assertRaises(NotFoundError, spph.getFileByName, 'not-changelog')


class TestBinaryPackagePublishingHistory(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_binaryFileUrls_no_binaries(self):
        bpr = self.factory.makeBinaryPackageRelease()
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr)
        self.assertEqual(0, len(bpph.binaryFileUrls()))

    def test_binaryFileUrls_one_binary(self):
        bpr = self.factory.makeBinaryPackageRelease()
        self.factory.makeBinaryPackageFile(binarypackagerelease=bpr)
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr)
        self.assertEqual(1, len(bpph.binaryFileUrls()))

    def test_binaryFileUrls_two_binaries(self):
        bpr = self.factory.makeBinaryPackageRelease()
        self.factory.makeBinaryPackageFile(
            binarypackagerelease=bpr, filetype=BinaryPackageFileType.DEB)
        self.factory.makeBinaryPackageFile(
            binarypackagerelease=bpr, filetype=BinaryPackageFileType.DDEB)
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr)
        self.assertEqual(2, len(bpph.binaryFileUrls()))


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
