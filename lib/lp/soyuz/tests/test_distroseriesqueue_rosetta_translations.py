# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test upload and queue manipulation of Rosetta Translations' tarballs.

See also lp.archivepublisher.tests.test_rosetta_translations for detailed
tests of rosetta-translations handling.
"""

import transaction
from os.path import relpath
from tarfile import TarFile
from zope.component import getUtility

from lp.archiveuploader.nascentupload import NascentUpload
from lp.archiveuploader.tests import (
    datadir,
    getPolicy,
    )
from lp.services.log.logger import DevNullLogger
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.model.packagetranslationsuploadjob import (
    PackageTranslationsUploadJob,
    )
from lp.soyuz.tests.test_publishing import TestNativePublishingBase
from lp.testing.dbuser import dbuser
from lp.testing.gpgkeys import import_public_test_keys
from lp.testing.layers import LaunchpadZopelessLayer

from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    )
from lp.translations.enums import RosettaImportStatus
from lp.translations.scripts.import_queue_gardener import ImportQueueGardener
from lp.translations.scripts.po_import import TranslationsImport


class TestDistroSeriesQueueRosettaTranslationsTarball(
        TestNativePublishingBase):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestDistroSeriesQueueRosettaTranslationsTarball, self).setUp()
        import_public_test_keys()
        self.logger = DevNullLogger()
        self.absolutely_anything_policy = getPolicy(
            name="absolutely-anything", distro="ubuntutest",
            distroseries=None)
        self.package_name = "pmount"
        self.version = "0.9.20-2ubuntu0.2"

    def uploadTestData(self, name=None, version=None):
        if name is None:
            name = self.package_name
        if version is None:
            version = self.version
        changes_file = "%s_%s_i386.changes" % (name, version)

        spph = self.getPubSource(sourcename=name, version=version,
                                 distroseries=self.breezy_autotest,
                                 status=PackagePublishingStatus.PUBLISHED)
        self.spr = spph.sourcepackagerelease
        self.translations_file = "%s_%s_i386_translations.tar.gz" % (name,
                                                                     version)
        upload = NascentUpload.from_changesfile_path(
            datadir("rosetta-translations/%s" % changes_file),
            self.absolutely_anything_policy, self.logger)

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

    def _getImportableFilesFromTarball(self):
        tarball = TarFile.open(mode="r:gz", fileobj=open(datadir(
            "rosetta-translations/%s" % self.translations_file)))
        return [relpath(file_, "./source/") for file_ in tarball.getnames() if
                ".po" in file_]

    def _getQueuePaths(self, import_status=None):
        if import_status is not None:
            entries = self.translation_import_queue.getAllEntries(
                target=self.spr.sourcepackage, import_status=import_status)
        else:
            entries = self.translation_import_queue.getAllEntries(
                target=self.spr.sourcepackage)
        return [entry.path for entry in entries]

    def test_publish(self):
        upload = self.uploadTestData()
        transaction.commit()
        upload.queue_root.realiseUpload(self.logger)

        # Test if the job was created correctly
        jobs = list(PackageTranslationsUploadJob.iterReady())
        self.assertEqual(1, len(jobs))

        job = jobs[0]
        # Assert if the job corresponds to the file we uploaded
        self.assertEqual(job.sourcepackagerelease, self.spr)
        self.assertEqual(job.libraryfilealias.filename, self.translations_file)

        # Test if the pmount translations tarball files were added to the
        # translation import queue
        with dbuser("upload_package_translations_job"):
            job.run()
        self.translation_import_queue = getUtility(ITranslationImportQueue)
        self.assertContentEqual(self._getImportableFilesFromTarball(),
                                self._getQueuePaths())

        self.factory.makePOTemplate(distroseries=self.breezy_autotest,
            sourcepackagename=self.spr.sourcepackagename, path="po/pmount.pot",
            translation_domain=self.package_name)

        # Approve all translations in the queue
        with dbuser("translations_import_queue_gardener"):
            gardener = ImportQueueGardener(
                'translations-import-queue-gardener', logger=self.logger,
                test_args=[])
            gardener.main()

        # Import all approved translations
        with dbuser("poimport"):
            importer = TranslationsImport('poimport', logger=self.logger,
                                          test_args=[])
            importer.main()
        # Test if all translations in the queue were successfully imported
        self.assertContentEqual(
            self._getImportableFilesFromTarball(), self._getQueuePaths(
                import_status=RosettaImportStatus.IMPORTED))
