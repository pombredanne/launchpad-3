# Copyright 2013-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test upload and queue manipulation of Rosetta Translations' tarballs.

See also lp.archivepublisher.tests.test_rosetta_translations for detailed
tests of rosetta-translations handling.
"""

from __future__ import absolute_import, print_function, unicode_literals

from os.path import relpath
from tarfile import TarFile

from storm.expr import Desc
import transaction
from zope.component import getUtility

from lp.archiveuploader.nascentupload import NascentUpload
from lp.archiveuploader.tests import (
    datadir,
    getPolicy,
    )
from lp.archiveuploader.uploadpolicy import ArchiveUploadType
from lp.registry.interfaces.person import IPersonSet
from lp.services.database.interfaces import IStore
from lp.services.log.logger import DevNullLogger
from lp.soyuz.enums import (
    PackagePublishingStatus,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
from lp.soyuz.interfaces.packagecopyjob import IPlainPackageCopyJobSource
from lp.soyuz.model.packagetranslationsuploadjob import (
    PackageTranslationsUploadJob,
    )
from lp.soyuz.model.queue import PackageUpload
from lp.soyuz.tests.test_publishing import TestNativePublishingBase
from lp.testing.dbuser import dbuser
from lp.testing.gpgkeys import import_public_test_keys
from lp.testing.layers import LaunchpadZopelessLayer
from lp.translations.enums import RosettaImportStatus
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    )
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
            distroseries="breezy-autotest")
        self.package_name = "pmount"
        self.version = "0.9.20-2ubuntu0.2"
        self.source_changes_file = "%s_%s_source.changes" % (self.package_name,
                                                             self.version)
        self.bin_changes_file = "%s_%s_i386.changes" % (self.package_name,
                                                        self.version)
        self.translations_file = "%s_%s_i386_translations.tar.gz" % (
            self.package_name, self.version)
        self.translation_import_queue = getUtility(ITranslationImportQueue)

    def uploadTestData(self, name=None, version=None):
        if name is None:
            name = self.package_name
        if version is None:
            version = self.version

        spph = self.getPubSource(sourcename=name, version=version,
                                 distroseries=self.breezy_autotest,
                                 status=PackagePublishingStatus.PUBLISHED)
        self.spr = spph.sourcepackagerelease
        upload = NascentUpload.from_changesfile_path(
            datadir("rosetta-translations/%s" % self.bin_changes_file),
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
        sp = self.breezy_autotest.getSourcePackage(self.spr.sourcepackagename)
        if import_status is not None:
            entries = self.translation_import_queue.getAllEntries(
                target=sp, import_status=import_status)
        else:
            entries = self.translation_import_queue.getAllEntries(target=sp)
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
        self.assertEqual(job.sourcepackagename, self.spr.sourcepackagename)
        self.assertEqual(job.libraryfilealias.filename, self.translations_file)

        # Test if the pmount translations tarball files were added to the
        # translation import queue
        with dbuser("upload_package_translations_job"):
            job.run()
        self.assertContentEqual(self._getImportableFilesFromTarball(),
                                self._getQueuePaths())

        self.factory.makePOTemplate(
            distroseries=self.breezy_autotest,
            sourcepackagename=self.spr.sourcepackagename,
            path="po/pmount.pot",
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

    def uploadToPPA(self):
        # Setup PPA owner and archive
        self.name16 = getUtility(IPersonSet).getByName('name16')
        name16_archive = self.factory.makeArchive(
            distribution=self.breezy_autotest.distribution, owner=self.name16,
            name="ppa")

        policy = self.absolutely_anything_policy
        policy.archive = name16_archive

        upload = NascentUpload.from_changesfile_path(
            datadir("rosetta-translations/%s" % self.source_changes_file),
            policy, self.logger)
        upload.process()

        self.assertFalse(upload.is_rejected)
        self.assertTrue(upload.do_accept())

        self.assertEqual(upload.queue_root.status, PackageUploadStatus.DONE)
        spph = self.name16.archive.getPublishedSources(name="pmount").one()
        self.assertIsNotNone(spph)
        transaction.commit()

        policy.accepted_type = ArchiveUploadType.BINARY_ONLY

        bin_upload = NascentUpload.from_changesfile_path(
            datadir("rosetta-translations/%s" % self.bin_changes_file), policy,
            self.logger)
        bin_upload.process()

        self.assertFalse(bin_upload.is_rejected)
        self.assertTrue(bin_upload.do_accept())
        self.assertEqual(bin_upload.queue_root.status,
                         PackageUploadStatus.ACCEPTED)

        bin_upload.queue_root.realiseUpload()
        self.assertEqual(bin_upload.queue_root.status,
                         PackageUploadStatus.DONE)
        self.assertEqual(bin_upload.queue_root.builds[0].build.status.name,
                         "FULLYBUILT")
        transaction.commit()

        return upload, spph, bin_upload

    def test_copyFromPPAToArchiveWithTranslations(self):
        # Upload the package to a PPA and process it.
        src_upload, spph, bin_upload = self.uploadToPPA()
        target_archive = self.breezy_autotest.main_archive

        # Copy the source package with binaries from PPA to the main archive.
        # Give QueueAdmin permissions for the user so the upload will be
        # accepted right away.
        person = target_archive.owner
        for component in self.breezy_autotest.components:
            getUtility(IArchivePermissionSet).newQueueAdmin(target_archive,
                                                            person, component)

        self.assertTrue(
            target_archive.canAdministerQueue(
                person, self.breezy_autotest.components, spph.pocket,
                self.breezy_autotest))

        target_archive.copyPackage(
            source_name=self.package_name, version=self.version,
            from_archive=self.name16.archive,
            to_pocket='RELEASE', to_series=self.breezy_autotest.name,
            person=person, include_binaries=True, unembargo=True,
            auto_approve=True)

        # Get copy job and run it, should be enough to publish it
        copy_job_source = getUtility(IPlainPackageCopyJobSource)
        copy_job = copy_job_source.getActiveJobs(target_archive).one()
        with dbuser('copy_packages'):
            copy_job.run()

        published_source = target_archive.getPublishedSources(name='pmount')[0]
        self.assertIsNotNone(published_source)
        self.assertEqual(
            published_source.sourcepackagerelease.upload_archive.displayname,
            'PPA for Foo Bar')
        self.assertEqual(
            published_source.archive.displayname,
            'Primary Archive for Ubuntu Test')

        # Move package to main, as only main and restricted packages have
        # their translations processed.
        published_source = published_source.changeOverride(
            new_component="main")

        self.spr = published_source.sourcepackagerelease
        self.assertIsNotNone(published_source.getPublishedBinaries())

        # Process the upload for it to create the PTUJ
        upload = IStore(PackageUpload).find(PackageUpload).order_by(
            Desc(PackageUpload.id)).first()
        upload.realiseUpload(self.logger)

        # Assert the job is created correctly
        ptu_jobs = list(PackageTranslationsUploadJob.iterReady())
        self.assertNotEqual(len(ptu_jobs), 0)

        # Let's attachTranslations
        ptu_job = ptu_jobs[0]
        with dbuser('upload_package_translations_job'):
            ptu_job.run()

        # Test if the pmount translations tarball files were added to the
        # translation import queue
        self.assertContentEqual(
            self._getImportableFilesFromTarball(), self._getQueuePaths())

        self.factory.makePOTemplate(
            distroseries=self.breezy_autotest,
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
