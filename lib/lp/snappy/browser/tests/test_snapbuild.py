# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test snap package build views."""

__metaclass__ = type

from fixtures import FakeLogger
from mechanize import LinkNotFoundError
import soupmatchers
from storm.locals import Store
from testtools.matchers import StartsWith
import transaction
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import BuildStatus
from lp.services.job.interfaces.job import JobStatus
from lp.services.webapp import canonical_url
from lp.snappy.interfaces.snapbuildjob import ISnapStoreUploadJobSource
from lp.testing import (
    admin_logged_in,
    ANONYMOUS,
    BrowserTestCase,
    login,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.pages import (
    extract_text,
    find_main_content,
    find_tags_by_class,
    )
from lp.testing.views import create_initialized_view


class TestCanonicalUrlForSnapBuild(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_canonical_url(self):
        owner = self.factory.makePerson(name="person")
        snap = self.factory.makeSnap(
            registrant=owner, owner=owner, name=u"snap")
        build = self.factory.makeSnapBuild(requester=owner, snap=snap)
        self.assertThat(
            canonical_url(build),
            StartsWith("http://launchpad.dev/~person/+snap/snap/+build/"))


class TestSnapBuildView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_files(self):
        # SnapBuildView.files returns all the associated files.
        build = self.factory.makeSnapBuild(status=BuildStatus.FULLYBUILT)
        snapfile = self.factory.makeSnapFile(snapbuild=build)
        build_view = create_initialized_view(build, "+index")
        self.assertEqual(
            [snapfile.libraryfile.filename],
            [lfa.filename for lfa in build_view.files])
        # Deleted files won't be included.
        self.assertFalse(snapfile.libraryfile.deleted)
        removeSecurityProxy(snapfile.libraryfile).content = None
        self.assertTrue(snapfile.libraryfile.deleted)
        build_view = create_initialized_view(build, "+index")
        self.assertEqual([], build_view.files)

    def test_store_upload_status_in_progress(self):
        build = self.factory.makeSnapBuild(status=BuildStatus.FULLYBUILT)
        getUtility(ISnapStoreUploadJobSource).create(build)
        build_view = create_initialized_view(build, "+index")
        self.assertThat(build_view(), soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "store upload status", "li",
                attrs={"id": "store-upload-status"},
                text="Store upload in progress")))

    def test_store_upload_status_completed(self):
        build = self.factory.makeSnapBuild(status=BuildStatus.FULLYBUILT)
        job = getUtility(ISnapStoreUploadJobSource).create(build)
        naked_job = removeSecurityProxy(job)
        naked_job.job._status = JobStatus.COMPLETED
        naked_job.store_url = "http://sca.example/dev/click-apps/1/rev/1/"
        build_view = create_initialized_view(build, "+index")
        self.assertThat(build_view(), soupmatchers.HTMLContains(
            soupmatchers.Within(
                soupmatchers.Tag(
                    "store upload status", "li",
                    attrs={"id": "store-upload-status"}),
                soupmatchers.Tag(
                    "store link", "a", attrs={"href": job.store_url},
                    text="Manage this package in the store"))))

    def test_store_upload_status_failed(self):
        build = self.factory.makeSnapBuild(status=BuildStatus.FULLYBUILT)
        job = getUtility(ISnapStoreUploadJobSource).create(build)
        naked_job = removeSecurityProxy(job)
        naked_job.job._status = JobStatus.FAILED
        naked_job.error_message = "Scan failed."
        build_view = create_initialized_view(build, "+index")
        self.assertThat(build_view(), soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "store upload status", "li",
                attrs={"id": "store-upload-status"},
                text="Store upload failed: Scan failed.")))

    def test_store_upload_status_release_failed(self):
        build = self.factory.makeSnapBuild(status=BuildStatus.FULLYBUILT)
        job = getUtility(ISnapStoreUploadJobSource).create(build)
        naked_job = removeSecurityProxy(job)
        naked_job.job._status = JobStatus.FAILED
        naked_job.store_url = "http://sca.example/dev/click-apps/1/rev/1/"
        naked_job.error_message = "Failed to publish"
        build_view = create_initialized_view(build, "+index")
        self.assertThat(build_view(), soupmatchers.HTMLContains(
            soupmatchers.Within(
                soupmatchers.Tag(
                    "store upload status", "li",
                    attrs={"id": "store-upload-status"},
                    text=(
                        "Releasing package to channels failed: "
                        "Failed to publish")),
                soupmatchers.Tag(
                    "store link", "a", attrs={"href": job.store_url}))))


class TestSnapBuildOperations(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnapBuildOperations, self).setUp()
        self.useFixture(FakeLogger())
        self.build = self.factory.makeSnapBuild()
        self.build_url = canonical_url(self.build)
        self.requester = self.build.requester
        self.buildd_admin = self.factory.makePerson(
            member_of=[getUtility(ILaunchpadCelebrities).buildd_admin])

    def test_cancel_build(self):
        # The requester of a build can cancel it.
        self.build.queueBuild()
        transaction.commit()
        browser = self.getViewBrowser(self.build, user=self.requester)
        browser.getLink("Cancel build").click()
        self.assertEqual(self.build_url, browser.getLink("Cancel").url)
        browser.getControl("Cancel build").click()
        self.assertEqual(self.build_url, browser.url)
        login(ANONYMOUS)
        self.assertEqual(BuildStatus.CANCELLED, self.build.status)

    def test_cancel_build_random_user(self):
        # An unrelated non-admin user cannot cancel a build.
        self.build.queueBuild()
        transaction.commit()
        user = self.factory.makePerson()
        browser = self.getViewBrowser(self.build, user=user)
        self.assertRaises(LinkNotFoundError, browser.getLink, "Cancel build")
        self.assertRaises(
            Unauthorized, self.getUserBrowser, self.build_url + "/+cancel",
            user=user)

    def test_cancel_build_wrong_state(self):
        # If the build isn't queued, you can't cancel it.
        browser = self.getViewBrowser(self.build, user=self.requester)
        self.assertRaises(LinkNotFoundError, browser.getLink, "Cancel build")

    def test_rescore_build(self):
        # A buildd admin can rescore a build.
        self.build.queueBuild()
        transaction.commit()
        browser = self.getViewBrowser(self.build, user=self.buildd_admin)
        browser.getLink("Rescore build").click()
        self.assertEqual(self.build_url, browser.getLink("Cancel").url)
        browser.getControl("Priority").value = "1024"
        browser.getControl("Rescore build").click()
        self.assertEqual(self.build_url, browser.url)
        login(ANONYMOUS)
        self.assertEqual(1024, self.build.buildqueue_record.lastscore)

    def test_rescore_build_invalid_score(self):
        # Build scores can only take numbers.
        self.build.queueBuild()
        transaction.commit()
        browser = self.getViewBrowser(self.build, user=self.buildd_admin)
        browser.getLink("Rescore build").click()
        self.assertEqual(self.build_url, browser.getLink("Cancel").url)
        browser.getControl("Priority").value = "tentwentyfour"
        browser.getControl("Rescore build").click()
        self.assertEqual(
            "Invalid integer data",
            extract_text(find_tags_by_class(browser.contents, "message")[1]))

    def test_rescore_build_not_admin(self):
        # A non-admin user cannot cancel a build.
        self.build.queueBuild()
        transaction.commit()
        user = self.factory.makePerson()
        browser = self.getViewBrowser(self.build, user=user)
        self.assertRaises(LinkNotFoundError, browser.getLink, "Rescore build")
        self.assertRaises(
            Unauthorized, self.getUserBrowser, self.build_url + "/+rescore",
            user=user)

    def test_rescore_build_wrong_state(self):
        # If the build isn't NEEDSBUILD, you can't rescore it.
        self.build.queueBuild()
        with person_logged_in(self.requester):
            self.build.cancel()
        browser = self.getViewBrowser(self.build, user=self.buildd_admin)
        self.assertRaises(LinkNotFoundError, browser.getLink, "Rescore build")

    def test_rescore_build_wrong_state_stale_link(self):
        # An attempt to rescore a non-queued build from a stale link shows a
        # sensible error message.
        self.build.queueBuild()
        with person_logged_in(self.requester):
            self.build.cancel()
        browser = self.getViewBrowser(
            self.build, "+rescore", user=self.buildd_admin)
        self.assertEqual(self.build_url, browser.url)
        self.assertIn(
            "Cannot rescore this build because it is not queued.",
            browser.contents)

    def test_builder_history(self):
        Store.of(self.build).flush()
        self.build.updateStatus(
            BuildStatus.FULLYBUILT, builder=self.factory.makeBuilder())
        title = self.build.title
        browser = self.getViewBrowser(self.build.builder, "+history")
        self.assertTextMatchesExpressionIgnoreWhitespace(
            "Build history.*%s" % title,
            extract_text(find_main_content(browser.contents)))
        self.assertEqual(self.build_url, browser.getLink(title).url)

    def makeBuildingSnap(self, archive=None):
        builder = self.factory.makeBuilder()
        build = self.factory.makeSnapBuild(archive=archive)
        build.updateStatus(BuildStatus.BUILDING, builder=builder)
        build.queueBuild()
        build.buildqueue_record.builder = builder
        build.buildqueue_record.logtail = "tail of the log"
        return build

    def test_builder_index_public(self):
        build = self.makeBuildingSnap()
        builder_url = canonical_url(build.builder)
        logout()
        browser = self.getNonRedirectingBrowser(
            url=builder_url, user=ANONYMOUS)
        self.assertIn("tail of the log", browser.contents)

    def test_builder_index_private(self):
        archive = self.factory.makeArchive(private=True)
        with admin_logged_in():
            build = self.makeBuildingSnap(archive=archive)
            builder_url = canonical_url(build.builder)
        logout()

        # An unrelated user can't see the logtail of a private build.
        browser = self.getNonRedirectingBrowser(url=builder_url)
        self.assertNotIn("tail of the log", browser.contents)

        # But someone who can see the archive can.
        browser = self.getNonRedirectingBrowser(
            url=builder_url, user=archive.owner)
        self.assertIn("tail of the log", browser.contents)
