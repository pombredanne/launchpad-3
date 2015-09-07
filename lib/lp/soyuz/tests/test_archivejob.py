# Copyright 2010-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from lp.services.job.runner import JobRunner
from lp.services.mail.sendmail import format_address_for_person
from lp.soyuz.enums import (
    ArchiveJobType,
    PackageUploadStatus,
    )
from lp.soyuz.model.archivejob import (
    ArchiveJob,
    ArchiveJobDerived,
    PackageUploadNotificationJob,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import dbuser
from lp.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.testing.mail_helpers import pop_notifications


class TestArchiveJob(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_instantiate(self):
        # ArchiveJob.__init__() instantiates a ArchiveJob instance.
        archive = self.factory.makeArchive()

        metadata = ('some', 'arbitrary', 'metadata')
        archive_job = ArchiveJob(
            archive, ArchiveJobType.PACKAGE_UPLOAD_NOTIFICATION, metadata)

        self.assertEqual(archive, archive_job.archive)
        self.assertEqual(
            ArchiveJobType.PACKAGE_UPLOAD_NOTIFICATION, archive_job.job_type)

        # When we actually access the ArchiveJob's metadata it gets
        # deserialized from JSON, so the representation returned by
        # archive_job.metadata will be different from what we originally
        # passed in.
        metadata_expected = (u'some', u'arbitrary', u'metadata')
        self.assertEqual(metadata_expected, archive_job.metadata)


class TestArchiveJobDerived(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_create_explodes(self):
        # ArchiveJobDerived.create() will blow up because it needs to be
        # subclassed to work properly.
        archive = self.factory.makeArchive()
        self.assertRaises(
            AttributeError, ArchiveJobDerived.create, archive)


class TestPackageUploadNotificationJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_getOopsVars(self):
        upload = self.factory.makePackageUpload(
            status=PackageUploadStatus.ACCEPTED)
        job = PackageUploadNotificationJob.create(
            upload, summary_text='Fake summary')
        expected = [
            ('job_id', job.context.job.id),
            ('archive_id', upload.archive.id),
            ('archive_job_id', job.context.id),
            ('archive_job_type', 'Package upload notification'),
            ('packageupload_id', upload.id),
            ('packageupload_status', 'Accepted'),
            ('summary_text', 'Fake summary'),
            ]
        self.assertEqual(expected, job.getOopsVars())

    def test_metadata(self):
        upload = self.factory.makePackageUpload(
            status=PackageUploadStatus.ACCEPTED)
        job = PackageUploadNotificationJob.create(
            upload, summary_text='Fake summary')
        expected = {
            'packageupload_id': upload.id,
            'packageupload_status': 'Accepted',
            'summary_text': 'Fake summary',
            }
        self.assertEqual(expected, job.metadata)
        self.assertEqual(upload, job.packageupload)
        self.assertEqual(
            PackageUploadStatus.ACCEPTED, job.packageupload_status)
        self.assertEqual('Fake summary', job.summary_text)

    def test_run(self):
        # Running a job produces a notification.  Detailed tests of which
        # notifications go to whom live in the PackageUpload and
        # PackageUploadMailer tests.
        upload = self.factory.makeSourcePackageUpload()
        self.factory.makeComponentSelection(
            upload.distroseries, upload.sourcepackagerelease.component)
        upload.setAccepted()
        job = PackageUploadNotificationJob.create(
            upload, summary_text='Fake summary')
        with dbuser(job.config.dbuser):
            JobRunner([job]).runAll()
        [email] = pop_notifications()
        self.assertEqual(
            format_address_for_person(upload.sourcepackagerelease.creator),
            email['To'])
        self.assertIn('(Accepted)', email['Subject'])
        self.assertIn('Fake summary', email.get_payload()[0].get_payload())
