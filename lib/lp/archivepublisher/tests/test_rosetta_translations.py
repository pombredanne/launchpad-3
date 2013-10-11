# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test rosetta-translations custom uploads.

See also lp.soyuz.tests.test_distroseriesqueue_rosetta_translations for
high-level tests of rosetta-translations upload and queue manipulation.
"""

import transaction
from lazr.jobrunner.jobrunner import SuspendJobException
from zope.security.proxy import removeSecurityProxy
from zope.component import getUtility

from lp.archivepublisher.rosetta_translations import (
    process_rosetta_translations,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.job.interfaces.job import JobStatus
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.soyuz.adapters.overrides import SourceOverride
from lp.soyuz.enums import (
    ArchivePermissionType,
    PackageUploadCustomFormat,
    PackageUploadStatus,
    SourcePackageFormat,
    )
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
from lp.soyuz.interfaces.queue import IPackageUploadSet
from lp.soyuz.model.packagecopyjob import IPackageCopyJobSource
from lp.soyuz.model.packagetranslationsuploadjob import (
    PackageTranslationsUploadJob,
    )
from lp.testing import TestCaseWithFactory, person_logged_in
from lp.testing.dbuser import dbuser
from lp.testing.layers import LaunchpadZopelessLayer
from lp.archiveuploader.uploadpolicy import (
    findPolicyByName
    )
from lp.soyuz.model.archivepermission import ArchivePermission
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelectionSet,
    )


class TestRosettaTranslations(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def makeTranslationsLFA(self, tar_content=None, filename=None):
        """Create an LibraryFileAlias containing dummy translation data."""
        if tar_content is None:
            tar_content = {
                'source/po/foo.pot': 'Foo template',
                'source/po/eo.po': 'Foo translation',
                }
        tarfile_content = LaunchpadWriteTarFile.files_to_string(
            tar_content)
        return self.factory.makeLibraryFileAlias(content=tarfile_content,
                                                 filename=filename)

    def makeAndPublishSourcePackage(self, sourcepackagename, distroseries,
            archive=None):
        sourcepackage = self.factory.makeSourcePackage(
            sourcepackagename=sourcepackagename,
            distroseries=distroseries)
        if archive is None:
            archive = distroseries.main_archive
        spph = self.factory.makeSourcePackagePublishingHistory(
            distroseries=distroseries,
            archive=archive,
            sourcepackagename=sourcepackagename,
            pocket=PackagePublishingPocket.RELEASE)
        return spph

    def makeJobElements(self):
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = "foo"
        sourcepackage_version = "3.8.2-1ubuntu1"
        filename = "%s_%s_i386_translations.tar.gz" % (sourcepackagename,
            sourcepackage_version)

        spph = self.makeAndPublishSourcePackage(
            sourcepackagename=sourcepackagename, distroseries=distroseries)
        packageupload = removeSecurityProxy(self.factory.makePackageUpload(
            distroseries=distroseries,
            archive=distroseries.main_archive))
        packageupload.addSource(spph.sourcepackagerelease)

        libraryfilealias = self.makeTranslationsLFA(filename=filename)
        return spph, packageupload, libraryfilealias

    def makeJobElementsFromCopyJob(self):
        orig_distroseries = self.factory.makeDistroSeries()
        sourcepackagename = "foo"
        sourcepackage_version = "3.8.2-1ubuntu1"

        filename = "%s_%s_i386_translations.tar.gz" % (sourcepackagename,
            sourcepackage_version)

        distroseries = self.factory.makeDistroSeries()
        getUtility(ISourcePackageFormatSelectionSet).add(distroseries,
            SourcePackageFormat.FORMAT_1_0)

        libraryfilealias = self.makeTranslationsLFA(filename=filename)

        spph_target = self.factory.makeSourcePackagePublishingHistory(
            distroseries=distroseries,
            archive=distroseries.main_archive,
            sourcepackagename=sourcepackagename,
            pocket=PackagePublishingPocket.RELEASE)

        target_archive = distroseries.main_archive

        admin = self.factory.makePerson(name="john")
        with person_logged_in(target_archive.owner):
            component = spph_target.component.name
            target_archive.newComponentUploader(admin, component)

        # It doesn't really return an upload when the package has an
        # ancestry.
        upload = self.factory.makeCopyJobPackageUpload(distroseries,
            sourcepackagename, source_archive=orig_distroseries.main_archive,
            target_pocket=PackagePublishingPocket.RELEASE,
            requester=admin)

        upload = distroseries.getPackageUploads(
            archive=distroseries.main_archive,
            pocket=PackagePublishingPocket.RELEASE, name=sourcepackagename,
            exact_match=True))

        return spph_target, upload, libraryfilealias

    def test_basic_from_copy(self):
        spph, pu, lfa = self.makeJobElementsFromCopyJob()
        transaction.commit()
        self.assertTrue(pu.contains_copy)
        process_rosetta_translations(pu, lfa)

    def test_basic_from_upload(self):
        spph, pu, lfa = self.makeJobElements()
        self.assertFalse(pu.contains_copy)
        transaction.commit()
        process_rosetta_translations(pu, lfa)

    def test_correct_job_is_created_from_upload(self):
        latest_spph, packageupload, libraryfilealias = self.makeJobElements()
        transaction.commit()
        process_rosetta_translations(packageupload, libraryfilealias)

        jobs = list(PackageTranslationsUploadJob.iterReady())
        self.assertEqual(1, len(jobs))

        self.assertEqual(latest_spph.sourcepackagerelease,
                         jobs[0].sourcepackagerelease)
        self.assertEqual(libraryfilealias, jobs[0].libraryfilealias)

    def test_correct_job_is_created_from_copy(self):
        spph, pu, lfa = self.makeJobElementsFromCopyJob()
        transaction.commit()
        self.assertEqual(pu.status, PackageUploadStatus.NEW)
        pu.setAccepted()

        job = getUtility(IPackageCopyJobSource).wrap(pu.package_copy_job)
        self.assertEqual(job.status, JobStatus.SUSPENDED)
        job.run()

        process_rosetta_translations(packageupload, libraryfilealias)

        jobs = list(PackageTranslationsUploadJob.iterReady())
        self.assertEqual(1, len(jobs))

        self.assertEqual(latest_spph.sourcepackagerelease,
                         jobs[0].sourcepackagerelease)
        self.assertEqual(libraryfilealias, jobs[0].libraryfilealias)
