# Copyright 2015-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test snap package build views."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import re

from fixtures import FakeLogger
from mechanize import LinkNotFoundError
from pymacaroons import Macaroon
import soupmatchers
from storm.locals import Store
from testtools.matchers import (
    Not,
    StartsWith,
    )
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
            registrant=owner, owner=owner, name="snap")
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

    def test_revision_id(self):
        build = self.factory.makeSnapBuild()
        build.updateStatus(
            BuildStatus.FULLYBUILT, slave_status={"revision_id": "dummy"})
        build_view = create_initialized_view(build, "+index")
        self.assertThat(build_view(), soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "revision ID", "li", attrs={"id": "revision-id"},
                text=re.compile(r"^\s*Revision: dummy\s*$"))))

    def test_store_upload_status_in_progress(self):
        build = self.factory.makeSnapBuild(status=BuildStatus.FULLYBUILT)
        getUtility(ISnapStoreUploadJobSource).create(build)
        build_view = create_initialized_view(build, "+index")
        self.assertThat(build_view(), soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "store upload status", "li",
                attrs={"id": "store-upload-status"},
                text=re.compile(r"^\s*Store upload in progress\s*$"))))

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
                    text=re.compile(
                        r"^\s*Manage this package in the store\s*$")))))

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
                text=re.compile(
                    r"^\s*Store upload failed:\s+Scan failed.\s*$"))))

    def test_store_upload_status_failed_with_extended_error_message(self):
        build = self.factory.makeSnapBuild(status=BuildStatus.FULLYBUILT)
        job = getUtility(ISnapStoreUploadJobSource).create(build)
        naked_job = removeSecurityProxy(job)
        naked_job.job._status = JobStatus.FAILED
        naked_job.error_message = "This should not be shown."
        naked_job.error_messages = [
            {"message": "Scan failed.", "link": "link1"},
            {"message": "Classic not allowed.", "link": "link2"}]
        build_view = create_initialized_view(build, "+index")
        built_view = build_view()
        self.assertThat(built_view, Not(soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "store upload status", "li",
                attrs={"id": "store-upload-status"},
                text=re.compile('.*This should not be shown.*')))))
        self.assertThat(built_view, soupmatchers.HTMLContains(
            soupmatchers.Within(
                soupmatchers.Tag(
                    "store upload status", "li",
                    attrs={"id": "store-upload-status"}),
                soupmatchers.Within(
                    soupmatchers.Tag(
                        "store upload error messages", "ul",
                        attrs={"id": "store-upload-error-messages"}),
                    soupmatchers.Within(
                        soupmatchers.Tag(
                            "store upload error message", "li"),
                        soupmatchers.Tag(
                            "store upload error link", "a",
                            text="What does this mean?"))))))

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
                    text=re.compile(
                        r"^\s*Releasing package to channels failed:\s+"
                        r"Failed to publish\s*$")),
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
        self.assertThat(browser.contents, soupmatchers.HTMLContains(
            soupmatchers.Tag(
                "notification", "div", attrs={"class": "warning message"},
                text="Cannot rescore this build because it is not queued.")))

    def setUpStoreUpload(self):
        self.pushConfig(
            "snappy", store_url="http://sca.example/",
            store_upload_url="http://updown.example/")
        with admin_logged_in():
            snappyseries = self.factory.makeSnappySeries(
                usable_distro_series=[self.build.snap.distro_series])
        with person_logged_in(self.requester):
            self.build.snap.store_series = snappyseries
            self.build.snap.store_name = self.factory.getUniqueUnicode()
            self.build.snap.store_secrets = {"root": Macaroon().serialize()}

    def test_store_upload(self):
        # A build not previously uploaded to the store can be uploaded
        # manually.
        self.setUpStoreUpload()
        self.build.updateStatus(BuildStatus.FULLYBUILT)
        self.factory.makeSnapFile(
            snapbuild=self.build,
            libraryfile=self.factory.makeLibraryFileAlias(db_only=True))
        browser = self.getViewBrowser(self.build, user=self.requester)
        browser.getControl("Upload this package to the store").click()
        self.assertEqual(self.build_url, browser.url)
        login(ANONYMOUS)
        [job] = getUtility(ISnapStoreUploadJobSource).iterReady()
        self.assertEqual(JobStatus.WAITING, job.job.status)
        self.assertEqual(self.build, job.snapbuild)
        self.assertEqual(
            "An upload has been scheduled and will run as soon as possible.",
            extract_text(find_tags_by_class(browser.contents, "message")[0]))

    def test_store_upload_retry(self):
        # A build with a previously-failed store upload can have the upload
        # retried.
        self.setUpStoreUpload()
        self.build.updateStatus(BuildStatus.FULLYBUILT)
        self.factory.makeSnapFile(
            snapbuild=self.build,
            libraryfile=self.factory.makeLibraryFileAlias(db_only=True))
        old_job = getUtility(ISnapStoreUploadJobSource).create(self.build)
        removeSecurityProxy(old_job).job._status = JobStatus.FAILED
        browser = self.getViewBrowser(self.build, user=self.requester)
        browser.getControl("Retry").click()
        self.assertEqual(self.build_url, browser.url)
        login(ANONYMOUS)
        [job] = getUtility(ISnapStoreUploadJobSource).iterReady()
        self.assertEqual(JobStatus.WAITING, job.job.status)
        self.assertEqual(self.build, job.snapbuild)
        self.assertEqual(
            "An upload has been scheduled and will run as soon as possible.",
            extract_text(find_tags_by_class(browser.contents, "message")[0]))

    def test_store_upload_error_notifies(self):
        # If a build cannot be scheduled for uploading to the store, we
        # issue a notification.
        self.setUpStoreUpload()
        self.build.updateStatus(BuildStatus.FULLYBUILT)
        browser = self.getViewBrowser(self.build, user=self.requester)
        browser.getControl("Upload this package to the store").click()
        self.assertEqual(self.build_url, browser.url)
        login(ANONYMOUS)
        self.assertEqual(
            [], list(getUtility(ISnapStoreUploadJobSource).iterReady()))
        self.assertEqual(
            "Cannot upload this package because it has no files.",
            extract_text(find_tags_by_class(browser.contents, "message")[0]))

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
