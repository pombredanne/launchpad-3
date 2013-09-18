# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test upload and queue manipulation of Rosetta Translations' tarballs.

See also lp.archivepublisher.tests.test_rosetta_translations for detailed
tests of rosetta-translations handling.
"""

import transaction
from zope.component import getUtility

from lp.archiveuploader.nascentupload import NascentUpload
from lp.archiveuploader.tests import (
    datadir,
    getPolicy,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.log.logger import DevNullLogger
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.model.packagetranslationsuploadjob import (
    PackageTranslationsUploadJob,
    )
from lp.soyuz.tests.test_publishing import TestNativePublishingBase
from lp.testing.gpgkeys import import_public_test_keys
from lp.testing.layers import LaunchpadZopelessLayer

from lp.translations.enums import RosettaImportStatus
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    )


class TestDistroSeriesQueueRosettaTranslationsTarball(
        TestNativePublishingBase):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestDistroSeriesQueueRosettaTranslationsTarball, self).setUp()
        import_public_test_keys()
        self.logger = DevNullLogger()
        self.absolutely_anything_policy = getPolicy(
            name="absolutely-anything", distro="ubuntu",
            distroseries=None)
        self.package_name = "pmount"
        self.version = "0.9.20-2ubuntu0.2"

    def uploadTestData(self, name=None, version=None):
        if name is None:
            name = self.package_name
        if version is None:
            version = self.version
        package = self.factory.getOrMakeSourcePackageName(name=name)
        changes_file = "%s_%s_i386.changes" % (name, version)

        self.spr = self.factory.makeSourcePackageRelease(
            sourcepackagename=package, version=version,
            component=self.factory.makeComponent("universe"))
        self.translations_file = "%s_%s_i386_translations.tar.gz" % (name,
                                                                     version)
        upload = NascentUpload.from_changesfile_path(
            datadir("rosetta-translations/%s" % changes_file),
            self.absolutely_anything_policy, self.logger)
        series = upload.policy.distro.getSeries(
            name_or_version="breezy-autotest")
        # Publish the source
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=series, archive=series.main_archive,
            pocket=PackagePublishingPocket.RELEASE,
            status=PackagePublishingStatus.PUBLISHED,
            sourcepackagerelease=self.spr)

        upload.process()
        self.assertFalse(upload.is_rejected)
        self.assertTrue(upload.do_accept())
        self.assertFalse(upload.rejection_message)
        # Accepting the queue entry because there's no ancestry, so not
        # auto-accepted
        upload.queue_root.setAccepted()
        return upload

    def test_accepts_correct_upload(self):
        upload = self.uploadTestData()
        self.assertEqual(1, len(upload.queue_root.customfiles))

    def test_publish(self):
        upload = self.uploadTestData()
        transaction.commit()
        upload.queue_root.realiseUpload(self.logger)

        # Test if the job was created correctly
        jobs = list(PackageTranslationsUploadJob.iterReady())
        self.assertEqual(1, len(jobs))

        job = jobs[0]
        # Assert the job corresponds to the one we uploaded
        self.assertEqual(job.sourcepackagerelease, self.spr)
        self.assertEqual(job.libraryfilealias.filename, self.translations_file)

        # Test if all files inside the pmount translations tar.gz were added to
        # the TranslationImportQueue
        job.run()
        translation_import_queue = getUtility(ITranslationImportQueue)
        entries_in_queue = translation_import_queue.getAllEntries(
            target=self.spr.sourcepackage)
        self.assertEqual(39, len(list(entries_in_queue)))
        # and are all waiting for review
        entries_in_queue = translation_import_queue.getAllEntries(
            target=self.spr.sourcepackage,
            import_status=RosettaImportStatus.NEEDS_REVIEW)
        self.assertEqual(39, len(list(entries_in_queue)))


