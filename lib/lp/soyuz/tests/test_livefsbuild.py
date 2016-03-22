# Copyright 2014-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test live filesystem build features."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
from urllib2 import (
    HTTPError,
    urlopen,
    )

import pytz
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.buildmaster.interfaces.packagebuild import IPackageBuild
from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.registry.enums import PersonVisibility
from lp.services.config import config
from lp.services.features.testing import FeatureFixture
from lp.services.librarian.browser import ProxiedLibraryFileAlias
from lp.services.webapp.interfaces import OAuthPermission
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.interfaces.livefs import (
    LIVEFS_FEATURE_FLAG,
    LiveFSFeatureDisabled,
    )
from lp.soyuz.interfaces.livefsbuild import (
    ILiveFSBuild,
    ILiveFSBuildSet,
    )
from lp.testing import (
    ANONYMOUS,
    api_url,
    login,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.testing.mail_helpers import pop_notifications
from lp.testing.pages import webservice_for_person


class TestLiveFSBuildFeatureFlag(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_feature_flag_disabled(self):
        # Without a feature flag, we will not create new LiveFSBuilds.
        class MockLiveFS:
            require_virtualized = False

        self.assertRaises(
            LiveFSFeatureDisabled, getUtility(ILiveFSBuildSet).new,
            None, MockLiveFS(), self.factory.makeArchive(),
            self.factory.makeDistroArchSeries(), None, None, None)


expected_body = """\
 * Live Filesystem: livefs-1
 * Version: 20140425-103800
 * Archive: distro
 * Distroseries: distro unstable
 * Architecture: i386
 * Pocket: RELEASE
 * State: Failed to build
 * Duration: 10 minutes
 * Build Log: %s
 * Upload Log: %s
 * Builder: http://launchpad.dev/builders/bob
"""


class TestLiveFSBuild(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestLiveFSBuild, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))
        self.build = self.factory.makeLiveFSBuild()

    def test_implements_interfaces(self):
        # LiveFSBuild implements IPackageBuild and ILiveFSBuild.
        self.assertProvides(self.build, IPackageBuild)
        self.assertProvides(self.build, ILiveFSBuild)

    def test_queueBuild(self):
        # LiveFSBuild can create the queue entry for itself.
        bq = self.build.queueBuild()
        self.assertProvides(bq, IBuildQueue)
        self.assertEqual(
            self.build.build_farm_job, removeSecurityProxy(bq)._build_farm_job)
        self.assertEqual(self.build, bq.specific_build)
        self.assertEqual(self.build.virtualized, bq.virtualized)
        self.assertIsNotNone(bq.processor)
        self.assertEqual(bq, self.build.buildqueue_record)

    def test_current_component_primary(self):
        # LiveFSBuilds for primary archives always build in universe for the
        # time being.
        self.assertEqual(ArchivePurpose.PRIMARY, self.build.archive.purpose)
        self.assertEqual("universe", self.build.current_component.name)

    def test_current_component_ppa(self):
        # PPAs only have indices for main, so LiveFSBuilds for PPAs always
        # build in main.
        build = self.factory.makeLiveFSBuild(
            archive=self.factory.makeArchive())
        self.assertEqual("main", build.current_component.name)

    def test_is_private(self):
        # A LiveFSBuild is private iff its LiveFS and archive are.
        self.assertFalse(self.build.is_private)
        private_team = self.factory.makeTeam(
            visibility=PersonVisibility.PRIVATE)
        with person_logged_in(private_team.teamowner):
            build = self.factory.makeLiveFSBuild(
                requester=private_team.teamowner, owner=private_team)
            self.assertTrue(build.is_private)
        private_archive = self.factory.makeArchive(private=True)
        with person_logged_in(private_archive.owner):
            build = self.factory.makeLiveFSBuild(archive=private_archive)
            self.assertTrue(build.is_private)

    def test_can_be_cancelled(self):
        # For all states that can be cancelled, can_be_cancelled returns True.
        ok_cases = [
            BuildStatus.BUILDING,
            BuildStatus.NEEDSBUILD,
            ]
        for status in BuildStatus:
            if status in ok_cases:
                self.assertTrue(self.build.can_be_cancelled)
            else:
                self.assertFalse(self.build.can_be_cancelled)

    def test_cancel_not_in_progress(self):
        # The cancel() method for a pending build leaves it in the CANCELLED
        # state.
        self.build.queueBuild()
        self.build.cancel()
        self.assertEqual(BuildStatus.CANCELLED, self.build.status)
        self.assertIsNone(self.build.buildqueue_record)

    def test_cancel_in_progress(self):
        # The cancel() method for a building build leaves it in the
        # CANCELLING state.
        bq = self.build.queueBuild()
        bq.markAsBuilding(self.factory.makeBuilder())
        self.build.cancel()
        self.assertEqual(BuildStatus.CANCELLING, self.build.status)
        self.assertEqual(bq, self.build.buildqueue_record)

    def test_estimateDuration(self):
        # Without previous builds, the default time estimate is 30m.
        self.assertEqual(1800, self.build.estimateDuration().seconds)

    def test_estimateDuration_with_history(self):
        # Previous successful builds of the same live filesystem are used
        # for estimates.
        self.factory.makeLiveFSBuild(
            requester=self.build.requester, livefs=self.build.livefs,
            distroarchseries=self.build.distro_arch_series,
            status=BuildStatus.FULLYBUILT, duration=timedelta(seconds=335))
        for i in range(3):
            self.factory.makeLiveFSBuild(
                requester=self.build.requester, livefs=self.build.livefs,
                distroarchseries=self.build.distro_arch_series,
                status=BuildStatus.FAILEDTOBUILD,
                duration=timedelta(seconds=20))
        self.assertEqual(335, self.build.estimateDuration().seconds)

    def test_build_cookie(self):
        build = self.factory.makeLiveFSBuild()
        self.assertEqual('LIVEFSBUILD-%d' % build.id, build.build_cookie)

    def test_getFileByName_logs(self):
        # getFileByName returns the logs when requested by name.
        self.build.setLog(
            self.factory.makeLibraryFileAlias(filename="buildlog.txt.gz"))
        self.assertEqual(
            self.build.log, self.build.getFileByName("buildlog.txt.gz"))
        self.assertRaises(NotFoundError, self.build.getFileByName, "foo")
        self.build.storeUploadLog("uploaded")
        self.assertEqual(
            self.build.upload_log,
            self.build.getFileByName(self.build.upload_log.filename))

    def test_getFileByName_uploaded_files(self):
        # getFileByName returns uploaded files when requested by name.
        filenames = ("ubuntu.squashfs", "ubuntu.manifest")
        lfas = []
        for filename in filenames:
            lfa = self.factory.makeLibraryFileAlias(filename=filename)
            lfas.append(lfa)
            self.build.addFile(lfa)
        self.assertContentEqual(
            lfas, [row[1] for row in self.build.getFiles()])
        for filename, lfa in zip(filenames, lfas):
            self.assertEqual(lfa, self.build.getFileByName(filename))
        self.assertRaises(NotFoundError, self.build.getFileByName, "missing")

    def test_verifySuccessfulUpload(self):
        self.assertFalse(self.build.verifySuccessfulUpload())
        self.factory.makeLiveFSFile(livefsbuild=self.build)
        self.assertTrue(self.build.verifySuccessfulUpload())

    def test_notify_fullybuilt(self):
        # notify does not send mail when a LiveFSBuild completes normally.
        person = self.factory.makePerson(name="person")
        build = self.factory.makeLiveFSBuild(
            requester=person, status=BuildStatus.FULLYBUILT)
        build.notify()
        self.assertEqual(0, len(pop_notifications()))

    def test_notify_packagefail(self):
        # notify sends mail when a LiveFSBuild fails.
        person = self.factory.makePerson(name="person")
        distribution = self.factory.makeDistribution(name="distro")
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution, name="unstable")
        processor = getUtility(IProcessorSet).getByName("386")
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag="i386",
            processor=processor)
        build = self.factory.makeLiveFSBuild(
            name=u"livefs-1", requester=person, owner=person,
            distroarchseries=distroarchseries,
            date_created=datetime(2014, 4, 25, 10, 38, 0, tzinfo=pytz.UTC),
            status=BuildStatus.FAILEDTOBUILD,
            builder=self.factory.makeBuilder(name="bob"),
            duration=timedelta(minutes=10))
        build.setLog(self.factory.makeLibraryFileAlias())
        build.notify()
        [notification] = pop_notifications()
        self.assertEqual(
            config.canonical.noreply_from_address, notification["From"])
        self.assertEqual(
            "Person <%s>" % person.preferredemail.email, notification["To"])
        subject = notification["Subject"].replace("\n ", " ")
        self.assertEqual(
            "[LiveFS build #%d] i386 build of livefs-1 livefs in distro "
            "unstable" % build.id, subject)
        self.assertEqual(
            "Requester", notification["X-Launchpad-Message-Rationale"])
        self.assertEqual(person.name, notification["X-Launchpad-Message-For"])
        self.assertEqual(
            "livefs-build-status",
            notification["X-Launchpad-Notification-Type"])
        self.assertEqual(
            "FAILEDTOBUILD", notification["X-Launchpad-Build-State"])
        body, footer = notification.get_payload(decode=True).split("\n-- \n")
        self.assertEqual(expected_body % (build.log_url, ""), body)
        self.assertEqual(
            "http://launchpad.dev/~person/+livefs/distro/unstable/livefs-1/"
            "+build/%d\n"
            "You are the requester of the build.\n" % build.id, footer)

    def addFakeBuildLog(self, build):
        build.setLog(self.factory.makeLibraryFileAlias("mybuildlog.txt"))

    def test_log_url(self):
        # The log URL for a live filesystem build will use the archive context.
        self.addFakeBuildLog(self.build)
        self.assertEqual(
            "http://launchpad.dev/~%s/+livefs/%s/%s/%s/+build/%d/+files/"
            "mybuildlog.txt" % (
                self.build.livefs.owner.name, self.build.distribution.name,
                self.build.distro_series.name, self.build.livefs.name,
                self.build.id),
            self.build.log_url)


class TestLiveFSBuildSet(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestLiveFSBuildSet, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))

    def test_getByBuildFarmJob_works(self):
        build = self.factory.makeLiveFSBuild()
        self.assertEqual(
            build,
            getUtility(ILiveFSBuildSet).getByBuildFarmJob(
                build.build_farm_job))

    def test_getByBuildFarmJob_returns_None_when_missing(self):
        bpb = self.factory.makeBinaryPackageBuild()
        self.assertIsNone(
            getUtility(ILiveFSBuildSet).getByBuildFarmJob(bpb.build_farm_job))

    def test_getByBuildFarmJobs_works(self):
        builds = [self.factory.makeLiveFSBuild() for i in range(10)]
        self.assertContentEqual(
            builds,
            getUtility(ILiveFSBuildSet).getByBuildFarmJobs(
                [build.build_farm_job for build in builds]))

    def test_getByBuildFarmJobs_works_empty(self):
        self.assertContentEqual(
            [], getUtility(ILiveFSBuildSet).getByBuildFarmJobs([]))


class TestLiveFSBuildWebservice(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestLiveFSBuildWebservice, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))
        self.person = self.factory.makePerson()
        self.webservice = webservice_for_person(
            self.person, permission=OAuthPermission.WRITE_PRIVATE)
        self.webservice.default_api_version = "devel"
        login(ANONYMOUS)

    def getURL(self, obj):
        return self.webservice.getAbsoluteUrl(api_url(obj))

    def test_properties(self):
        # The basic properties of a LiveFSBuild are sensible.
        db_build = self.factory.makeLiveFSBuild(
            requester=self.person, unique_key=u"foo",
            metadata_override={"image_format": "plain"},
            date_created=datetime(2014, 4, 25, 10, 38, 0, tzinfo=pytz.UTC))
        build_url = api_url(db_build)
        logout()
        build = self.webservice.get(build_url).jsonBody()
        with person_logged_in(self.person):
            self.assertEqual(self.getURL(self.person), build["requester_link"])
            self.assertEqual(
                self.getURL(db_build.livefs), build["livefs_link"])
            self.assertEqual(
                self.getURL(db_build.archive), build["archive_link"])
            self.assertEqual(
                self.getURL(db_build.distro_arch_series),
                build["distro_arch_series_link"])
            self.assertEqual("Release", build["pocket"])
            self.assertEqual("foo", build["unique_key"])
            self.assertEqual(
                {"image_format": "plain"}, build["metadata_override"])
            self.assertEqual("20140425-103800", build["version"])
            self.assertIsNone(build["score"])
            self.assertFalse(build["can_be_rescored"])
            self.assertFalse(build["can_be_cancelled"])

    def test_public(self):
        # A LiveFSBuild with a public LiveFS and archive is itself public.
        db_build = self.factory.makeLiveFSBuild()
        build_url = api_url(db_build)
        unpriv_webservice = webservice_for_person(
            self.factory.makePerson(), permission=OAuthPermission.WRITE_PUBLIC)
        unpriv_webservice.default_api_version = "devel"
        logout()
        self.assertEqual(200, self.webservice.get(build_url).status)
        self.assertEqual(200, unpriv_webservice.get(build_url).status)

    def test_private_livefs(self):
        # A LiveFSBuild with a private LiveFS is private.
        db_team = self.factory.makeTeam(
            owner=self.person, visibility=PersonVisibility.PRIVATE)
        with person_logged_in(self.person):
            db_build = self.factory.makeLiveFSBuild(
                requester=self.person, owner=db_team)
            build_url = api_url(db_build)
        unpriv_webservice = webservice_for_person(
            self.factory.makePerson(), permission=OAuthPermission.WRITE_PUBLIC)
        unpriv_webservice.default_api_version = "devel"
        logout()
        self.assertEqual(200, self.webservice.get(build_url).status)
        # 404 since we aren't allowed to know that the private team exists.
        self.assertEqual(404, unpriv_webservice.get(build_url).status)

    def test_private_archive(self):
        # A LiveFSBuild with a private archive is private.
        db_archive = self.factory.makeArchive(owner=self.person, private=True)
        with person_logged_in(self.person):
            db_build = self.factory.makeLiveFSBuild(archive=db_archive)
            build_url = api_url(db_build)
        unpriv_webservice = webservice_for_person(
            self.factory.makePerson(), permission=OAuthPermission.WRITE_PUBLIC)
        unpriv_webservice.default_api_version = "devel"
        logout()
        self.assertEqual(200, self.webservice.get(build_url).status)
        self.assertEqual(401, unpriv_webservice.get(build_url).status)

    def test_cancel(self):
        # The owner of a build can cancel it.
        db_build = self.factory.makeLiveFSBuild(requester=self.person)
        db_build.queueBuild()
        build_url = api_url(db_build)
        unpriv_webservice = webservice_for_person(
            self.factory.makePerson(), permission=OAuthPermission.WRITE_PUBLIC)
        unpriv_webservice.default_api_version = "devel"
        logout()
        build = self.webservice.get(build_url).jsonBody()
        self.assertTrue(build["can_be_cancelled"])
        response = unpriv_webservice.named_post(build["self_link"], "cancel")
        self.assertEqual(401, response.status)
        response = self.webservice.named_post(build["self_link"], "cancel")
        self.assertEqual(200, response.status)
        build = self.webservice.get(build_url).jsonBody()
        self.assertFalse(build["can_be_cancelled"])
        with person_logged_in(self.person):
            self.assertEqual(BuildStatus.CANCELLED, db_build.status)

    def test_rescore(self):
        # Buildd administrators can rescore builds.
        db_build = self.factory.makeLiveFSBuild(requester=self.person)
        db_build.queueBuild()
        build_url = api_url(db_build)
        buildd_admin = self.factory.makePerson(
            member_of=[getUtility(ILaunchpadCelebrities).buildd_admin])
        buildd_admin_webservice = webservice_for_person(
            buildd_admin, permission=OAuthPermission.WRITE_PUBLIC)
        buildd_admin_webservice.default_api_version = "devel"
        logout()
        build = self.webservice.get(build_url).jsonBody()
        self.assertEqual(2505, build["score"])
        self.assertTrue(build["can_be_rescored"])
        response = self.webservice.named_post(
            build["self_link"], "rescore", score=5000)
        self.assertEqual(401, response.status)
        response = buildd_admin_webservice.named_post(
            build["self_link"], "rescore", score=5000)
        self.assertEqual(200, response.status)
        build = self.webservice.get(build_url).jsonBody()
        self.assertEqual(5000, build["score"])

    def assertCanOpenRedirectedUrl(self, browser, url):
        redirection = self.assertRaises(HTTPError, browser.open, url)
        self.assertEqual(303, redirection.code)
        urlopen(redirection.hdrs["Location"]).close()

    def test_logs(self):
        # API clients can fetch the build and upload logs.
        db_build = self.factory.makeLiveFSBuild(requester=self.person)
        db_build.setLog(self.factory.makeLibraryFileAlias("buildlog.txt.gz"))
        db_build.storeUploadLog("uploaded")
        build_url = api_url(db_build)
        logout()
        build = self.webservice.get(build_url).jsonBody()
        browser = self.getNonRedirectingBrowser(user=self.person)
        self.assertIsNotNone(build["build_log_url"])
        self.assertCanOpenRedirectedUrl(browser, build["build_log_url"])
        self.assertIsNotNone(build["upload_log_url"])
        self.assertCanOpenRedirectedUrl(browser, build["upload_log_url"])

    def test_getFileUrls(self):
        # API clients can fetch files attached to builds.
        db_build = self.factory.makeLiveFSBuild(requester=self.person)
        db_files = [
            self.factory.makeLiveFSFile(livefsbuild=db_build)
            for i in range(2)]
        build_url = api_url(db_build)
        file_urls = [
            ProxiedLibraryFileAlias(file.libraryfile, db_build).http_url
            for file in db_files]
        logout()
        response = self.webservice.named_get(build_url, "getFileUrls")
        self.assertEqual(200, response.status)
        self.assertContentEqual(file_urls, response.jsonBody())
        browser = self.getNonRedirectingBrowser(user=self.person)
        for file_url in file_urls:
            self.assertCanOpenRedirectedUrl(browser, file_url)
