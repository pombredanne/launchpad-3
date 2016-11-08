# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for snap build jobs."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from fixtures import FakeLogger
from zope.interface import implementer

from lp.services.config import config
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.runner import JobRunner
from lp.snappy.interfaces.snap import SNAP_TESTING_FLAGS
from lp.snappy.interfaces.snapbuildjob import (
    ISnapBuildJob,
    ISnapStoreUploadJob,
    )
from lp.snappy.interfaces.snapstoreclient import (
    BadReleaseResponse,
    BadScanStatusResponse,
    BadUploadResponse,
    ISnapStoreClient,
    UnauthorizedUploadResponse,
    UploadNotScannedYetResponse,
    )
from lp.snappy.model.snapbuildjob import (
    SnapBuildJob,
    SnapBuildJobType,
    SnapStoreUploadJob,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import dbuser
from lp.testing.fakemethod import FakeMethod
from lp.testing.fixture import ZopeUtilityFixture
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.testing.mail_helpers import pop_notifications


@implementer(ISnapStoreClient)
class FakeSnapStoreClient:

    def __init__(self):
        self.upload = FakeMethod()
        self.checkStatus = FakeMethod()
        self.release = FakeMethod()


class TestSnapBuildJob(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnapBuildJob, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

    def test_provides_interface(self):
        # `SnapBuildJob` objects provide `ISnapBuildJob`.
        snapbuild = self.factory.makeSnapBuild()
        self.assertProvides(
            SnapBuildJob(snapbuild, SnapBuildJobType.STORE_UPLOAD, {}),
            ISnapBuildJob)


class TestSnapStoreUploadJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestSnapStoreUploadJob, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))
        self.status_url = "http://sca.example/dev/api/snaps/1/builds/1/status"
        self.store_url = "http://sca.example/dev/click-apps/1/rev/1/"

    def test_provides_interface(self):
        # `SnapStoreUploadJob` objects provide `ISnapStoreUploadJob`.
        snapbuild = self.factory.makeSnapBuild()
        job = SnapStoreUploadJob.create(snapbuild)
        self.assertProvides(job, ISnapStoreUploadJob)

    def test___repr__(self):
        # `SnapStoreUploadJob` objects have an informative __repr__.
        snapbuild = self.factory.makeSnapBuild()
        job = SnapStoreUploadJob.create(snapbuild)
        self.assertEqual(
            "<SnapStoreUploadJob for %s>" % snapbuild.title, repr(job))

    def test_run(self):
        # The job uploads the build to the store and records the store URL.
        snapbuild = self.factory.makeSnapBuild(
            builder=self.factory.makeBuilder())
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.result = self.status_url
        client.checkStatus.result = (self.store_url, 1)
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            JobRunner([job]).runAll()
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([((self.status_url,), {})], client.checkStatus.calls)
        self.assertEqual([], client.release.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertEqual(self.store_url, job.store_url)
        self.assertIsNone(job.error_message)
        self.assertEqual([], pop_notifications())

    def test_run_failed(self):
        # A failed run sets the store upload status to FAILED.
        snapbuild = self.factory.makeSnapBuild(
            builder=self.factory.makeBuilder())
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.failure = ValueError("An upload failure")
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            JobRunner([job]).runAll()
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([], client.checkStatus.calls)
        self.assertEqual([], client.release.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertIsNone(job.store_url)
        self.assertEqual("An upload failure", job.error_message)
        self.assertEqual([], pop_notifications())

    def test_run_unauthorized_notifies(self):
        # A run that gets 401 from the store sends mail.
        requester = self.factory.makePerson(name="requester")
        requester_team = self.factory.makeTeam(
            owner=requester, name="requester-team", members=[requester])
        snapbuild = self.factory.makeSnapBuild(
            requester=requester_team, name="test-snap", owner=requester_team,
            builder=self.factory.makeBuilder())
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.failure = UnauthorizedUploadResponse(
            "Authorization failed.")
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            JobRunner([job]).runAll()
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([], client.checkStatus.calls)
        self.assertEqual([], client.release.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertIsNone(job.store_url)
        self.assertEqual("Authorization failed.", job.error_message)
        [notification] = pop_notifications()
        self.assertEqual(
            config.canonical.noreply_from_address, notification["From"])
        self.assertEqual(
            "Requester <%s>" % requester.preferredemail.email,
            notification["To"])
        subject = notification["Subject"].replace("\n ", " ")
        self.assertEqual("Store authorization failed for test-snap", subject)
        self.assertEqual(
            "Requester @requester-team",
            notification["X-Launchpad-Message-Rationale"])
        self.assertEqual(
            requester_team.name, notification["X-Launchpad-Message-For"])
        self.assertEqual(
            "snap-build-upload-unauthorized",
            notification["X-Launchpad-Notification-Type"])
        body, footer = notification.get_payload(decode=True).split("\n-- \n")
        self.assertIn(
            "http://launchpad.dev/~requester-team/+snap/test-snap/+authorize",
            body)
        self.assertEqual(
            "http://launchpad.dev/~requester-team/+snap/test-snap/+build/%d\n"
            "Your team Requester Team is the requester of the build.\n" %
            snapbuild.id, footer)

    def test_run_upload_failure_notifies(self):
        # A run that gets some other upload failure from the store sends
        # mail.
        requester = self.factory.makePerson(name="requester")
        requester_team = self.factory.makeTeam(
            owner=requester, name="requester-team", members=[requester])
        snapbuild = self.factory.makeSnapBuild(
            requester=requester_team, name="test-snap", owner=requester_team,
            builder=self.factory.makeBuilder())
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.failure = BadUploadResponse("Failed to upload")
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            JobRunner([job]).runAll()
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([], client.checkStatus.calls)
        self.assertEqual([], client.release.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertIsNone(job.store_url)
        self.assertEqual("Failed to upload", job.error_message)
        [notification] = pop_notifications()
        self.assertEqual(
            config.canonical.noreply_from_address, notification["From"])
        self.assertEqual(
            "Requester <%s>" % requester.preferredemail.email,
            notification["To"])
        subject = notification["Subject"].replace("\n ", " ")
        self.assertEqual("Store upload failed for test-snap", subject)
        self.assertEqual(
            "Requester @requester-team",
            notification["X-Launchpad-Message-Rationale"])
        self.assertEqual(
            requester_team.name, notification["X-Launchpad-Message-For"])
        self.assertEqual(
            "snap-build-upload-failed",
            notification["X-Launchpad-Notification-Type"])
        body, footer = notification.get_payload(decode=True).split("\n-- \n")
        self.assertIn("Failed to upload", body)
        build_url = (
            "http://launchpad.dev/~requester-team/+snap/test-snap/+build/%d" %
            snapbuild.id)
        self.assertIn(build_url, body)
        self.assertEqual(
            "%s\nYour team Requester Team is the requester of the build.\n" %
            build_url, footer)

    def test_run_scan_pending_retries(self):
        # A run that finds that the store has not yet finished scanning the
        # package schedules itself to be retried.
        self.useFixture(FakeLogger())
        snapbuild = self.factory.makeSnapBuild(
            builder=self.factory.makeBuilder())
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.result = self.status_url
        client.checkStatus.failure = UploadNotScannedYetResponse()
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            JobRunner([job]).runAll()
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([((self.status_url,), {})], client.checkStatus.calls)
        self.assertEqual([], client.release.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertIsNone(job.store_url)
        self.assertIsNone(job.error_message)
        self.assertEqual([], pop_notifications())
        self.assertEqual(JobStatus.WAITING, job.job.status)
        # Try again.  The upload part of the job is not retried, and this
        # time the scan completes.
        job.lease_expires = None
        job.scheduled_start = None
        client.upload.calls = []
        client.checkStatus.calls = []
        client.checkStatus.failure = None
        client.checkStatus.result = (self.store_url, 1)
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            JobRunner([job]).runAll()
        self.assertEqual([], client.upload.calls)
        self.assertEqual([((self.status_url,), {})], client.checkStatus.calls)
        self.assertEqual([], client.release.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertEqual(self.store_url, job.store_url)
        self.assertIsNone(job.error_message)
        self.assertEqual([], pop_notifications())
        self.assertEqual(JobStatus.COMPLETED, job.job.status)

    def test_run_scan_failure_notifies(self):
        # A run that gets a scan failure from the store sends mail.
        requester = self.factory.makePerson(name="requester")
        requester_team = self.factory.makeTeam(
            owner=requester, name="requester-team", members=[requester])
        snapbuild = self.factory.makeSnapBuild(
            requester=requester_team, name="test-snap", owner=requester_team,
            builder=self.factory.makeBuilder())
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.result = self.status_url
        client.checkStatus.failure = BadScanStatusResponse("Scan failed.")
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            JobRunner([job]).runAll()
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([((self.status_url,), {})], client.checkStatus.calls)
        self.assertEqual([], client.release.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertIsNone(job.store_url)
        self.assertEqual("Scan failed.", job.error_message)
        [notification] = pop_notifications()
        self.assertEqual(
            config.canonical.noreply_from_address, notification["From"])
        self.assertEqual(
            "Requester <%s>" % requester.preferredemail.email,
            notification["To"])
        subject = notification["Subject"].replace("\n ", " ")
        self.assertEqual("Store upload scan failed for test-snap", subject)
        self.assertEqual(
            "Requester @requester-team",
            notification["X-Launchpad-Message-Rationale"])
        self.assertEqual(
            requester_team.name, notification["X-Launchpad-Message-For"])
        self.assertEqual(
            "snap-build-upload-scan-failed",
            notification["X-Launchpad-Notification-Type"])
        body, footer = notification.get_payload(decode=True).split("\n-- \n")
        self.assertIn("Scan failed.", body)
        self.assertEqual(
            "http://launchpad.dev/~requester-team/+snap/test-snap/+build/%d\n"
            "Your team Requester Team is the requester of the build.\n" %
            snapbuild.id, footer)

    def test_run_release(self):
        # A run configured to automatically release the package to certain
        # channels does so.
        snapbuild = self.factory.makeSnapBuild(
            store_channels=["stable", "edge"])
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.result = self.status_url
        client.checkStatus.result = (self.store_url, 1)
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            JobRunner([job]).runAll()
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([((self.status_url,), {})], client.checkStatus.calls)
        self.assertEqual([((snapbuild, 1), {})], client.release.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertEqual(self.store_url, job.store_url)
        self.assertIsNone(job.error_message)
        self.assertEqual([], pop_notifications())

    def test_run_release_manual_review_notifies(self):
        # A run configured to automatically release the package to certain
        # channels but that encounters the manual review state on upload
        # sends mail.
        requester = self.factory.makePerson(name="requester")
        requester_team = self.factory.makeTeam(
            owner=requester, name="requester-team", members=[requester])
        snapbuild = self.factory.makeSnapBuild(
            requester=requester_team, name="test-snap", owner=requester_team,
            store_channels=["stable", "edge"])
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.result = self.status_url
        client.checkStatus.result = (self.store_url, None)
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            JobRunner([job]).runAll()
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([((self.status_url,), {})], client.checkStatus.calls)
        self.assertEqual([], client.release.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertEqual(self.store_url, job.store_url)
        self.assertEqual(
            "Package held for manual review on the store; "
            "cannot release it automatically.",
            job.error_message)
        [notification] = pop_notifications()
        self.assertEqual(
            config.canonical.noreply_from_address, notification["From"])
        self.assertEqual(
            "Requester <%s>" % requester.preferredemail.email,
            notification["To"])
        subject = notification["Subject"].replace("\n ", " ")
        self.assertEqual("test-snap held for manual review", subject)
        self.assertEqual(
            "Requester @requester-team",
            notification["X-Launchpad-Message-Rationale"])
        self.assertEqual(
            requester_team.name, notification["X-Launchpad-Message-For"])
        self.assertEqual(
            "snap-build-release-manual-review",
            notification["X-Launchpad-Notification-Type"])
        body, footer = notification.get_payload(decode=True).split("\n-- \n")
        self.assertIn(self.store_url, body)
        self.assertEqual(
            "http://launchpad.dev/~requester-team/+snap/test-snap/+build/%d\n"
            "Your team Requester Team is the requester of the build.\n" %
            snapbuild.id, footer)

    def test_run_release_failure_notifies(self):
        # A run configured to automatically release the package to certain
        # channels but that fails to do so sends mail.
        requester = self.factory.makePerson(name="requester")
        requester_team = self.factory.makeTeam(
            owner=requester, name="requester-team", members=[requester])
        snapbuild = self.factory.makeSnapBuild(
            requester=requester_team, name="test-snap", owner=requester_team,
            store_channels=["stable", "edge"])
        self.assertContentEqual([], snapbuild.store_upload_jobs)
        job = SnapStoreUploadJob.create(snapbuild)
        client = FakeSnapStoreClient()
        client.upload.result = self.status_url
        client.checkStatus.result = (self.store_url, 1)
        client.release.failure = BadReleaseResponse("Failed to publish")
        self.useFixture(ZopeUtilityFixture(client, ISnapStoreClient))
        with dbuser(config.ISnapStoreUploadJobSource.dbuser):
            JobRunner([job]).runAll()
        self.assertEqual([((snapbuild,), {})], client.upload.calls)
        self.assertEqual([((self.status_url,), {})], client.checkStatus.calls)
        self.assertEqual([((snapbuild, 1), {})], client.release.calls)
        self.assertContentEqual([job], snapbuild.store_upload_jobs)
        self.assertEqual(self.store_url, job.store_url)
        self.assertEqual("Failed to publish", job.error_message)
        [notification] = pop_notifications()
        self.assertEqual(
            config.canonical.noreply_from_address, notification["From"])
        self.assertEqual(
            "Requester <%s>" % requester.preferredemail.email,
            notification["To"])
        subject = notification["Subject"].replace("\n ", " ")
        self.assertEqual("Store release failed for test-snap", subject)
        self.assertEqual(
            "Requester @requester-team",
            notification["X-Launchpad-Message-Rationale"])
        self.assertEqual(
            requester_team.name, notification["X-Launchpad-Message-For"])
        self.assertEqual(
            "snap-build-release-failed",
            notification["X-Launchpad-Notification-Type"])
        body, footer = notification.get_payload(decode=True).split("\n-- \n")
        self.assertIn("Failed to publish", body)
        self.assertIn(self.store_url, body)
        self.assertEqual(
            "http://launchpad.dev/~requester-team/+snap/test-snap/+build/%d\n"
            "Your team Requester Team is the requester of the build.\n" %
            snapbuild.id, footer)
