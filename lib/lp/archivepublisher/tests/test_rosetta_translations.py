# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test rosetta-translations custom uploads.

See also lp.soyuz.tests.test_distroseriesqueue_rosetta_translations for
high-level tests of rosetta-translations upload and queue manipulation.
"""

import transaction
from zope.security.proxy import removeSecurityProxy
from zope.component import getUtility

from lp.archivepublisher.rosetta_translations import (
    process_rosetta_translations,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.soyuz.enums import (
    ArchivePurpose,
    PackageUploadCustomFormat,
    PackageUploadStatus,
    SourcePackageFormat,
    )
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelectionSet,
    )
from lp.soyuz.model.packagetranslationsuploadjob import (
    PackageTranslationsUploadJob,
    )
from lp.testing import TestCaseWithFactory, person_logged_in
from lp.testing.layers import LaunchpadZopelessLayer


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
        self.factory.makeSourcePackage(
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
        return spph.sourcepackagerelease, packageupload, libraryfilealias

    def makeJobElementsFromCopyJob(self):
        sourcepackage_version = "3.8.2-1ubuntu1"

        das = self.factory.makeDistroArchSeries()
        distroseries = das.distroseries
        distroseries.nominatedarchindep = das
        getUtility(ISourcePackageFormatSelectionSet).add(distroseries,
            SourcePackageFormat.FORMAT_1_0)

        bpb = self.factory.makeBinaryPackageBuild(
            distroarchseries=distroseries.nominatedarchindep,
            archive=self.factory.makeArchive(purpose=ArchivePurpose.PPA),
            pocket=PackagePublishingPocket.RELEASE)
        bpr = self.factory.makeBinaryPackageRelease(build=bpb)
        self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr, distroarchseries=bpb.distro_arch_series,
            archive=bpb.archive, pocket=bpb.pocket)
        bin_pu = self.factory.makePackageUpload(
            status=PackageUploadStatus.DONE, archive=bpb.archive,
            distroseries=distroseries)
        bin_pu.addBuild(bpb)

        filename = "%s_%s_i386_translations.tar.gz" % (
            bpb.source_package_release.sourcepackagename.name,
            sourcepackage_version)

        libraryfilealias = self.makeTranslationsLFA(filename=filename)
        bin_pu.addCustom(
            libraryfilealias, PackageUploadCustomFormat.ROSETTA_TRANSLATIONS)

        # Create ancestry in the target to avoid hitting New.
        spph_target = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=bpb.source_package_release.sourcepackagename,
            version='0', archive=distroseries.main_archive,
            distroseries=distroseries, pocket=PackagePublishingPocket.RELEASE)

        target_archive = distroseries.main_archive

        admin = self.factory.makePerson(name="john")
        with person_logged_in(target_archive.owner):
            component = spph_target.component.name
            target_archive.newComponentUploader(admin, component)
            pass

        spr = bpb.source_package_release
        job = self.factory.makePlainPackageCopyJob(
            package_name=spr.sourcepackagename.name,
            package_version=spr.version, source_archive=bpb.archive,
            target_archive=distroseries.main_archive,
            target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            requester=admin, include_binaries=True)

        job.run()

        from storm.expr import Desc
        from lp.soyuz.model.queue import PackageUpload
        from lp.services.database.interfaces import IStore
        upload = IStore(PackageUpload).find(PackageUpload).order_by(
            Desc(PackageUpload.id)).first()

        return spr, upload, libraryfilealias

    def test_basic_from_copy(self):
        spr, pu, lfa = self.makeJobElementsFromCopyJob()
        transaction.commit()
        process_rosetta_translations(pu, lfa)

    def test_basic_from_upload(self):
        spr, pu, lfa = self.makeJobElements()
        transaction.commit()
        process_rosetta_translations(pu, lfa)

    def test_correct_job_is_created_from_upload(self):
        spr, packageupload, libraryfilealias = self.makeJobElements()
        transaction.commit()
        process_rosetta_translations(packageupload, libraryfilealias)

        jobs = list(PackageTranslationsUploadJob.iterReady())
        self.assertEqual(1, len(jobs))

        self.assertEqual(spr, jobs[0].sourcepackagerelease)
        self.assertEqual(libraryfilealias, jobs[0].libraryfilealias)

    def test_correct_job_is_created_from_copy(self):
        spr, packageupload, libraryfilealias = (
            self.makeJobElementsFromCopyJob())
        transaction.commit()
        process_rosetta_translations(packageupload, libraryfilealias)

        jobs = list(PackageTranslationsUploadJob.iterReady())
        self.assertEqual(1, len(jobs))

        self.assertEqual(spr, jobs[0].sourcepackagerelease)
        self.assertEqual(libraryfilealias, jobs[0].libraryfilealias)
