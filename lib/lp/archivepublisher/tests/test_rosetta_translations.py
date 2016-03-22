# Copyright 2013-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test rosetta-translations custom uploads.

See also lp.soyuz.tests.test_distroseriesqueue_rosetta_translations for
high-level tests of rosetta-translations upload and queue manipulation.
"""

from storm.expr import Desc
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.errors import NotFoundError
from lp.archivepublisher.rosetta_translations import (
    process_rosetta_translations,
    RosettaTranslationsUpload,
    )
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.database.interfaces import IStore
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
from lp.soyuz.model.queue import PackageUpload
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.dbuser import dbuser
from lp.testing.layers import LaunchpadZopelessLayer
from lp.translations.model.translationpackagingjob import (
    TranslationPackagingJob,
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

    def makeJobElements(self, sourcepackagename=None):
        distroseries = self.factory.makeDistroSeries()
        if sourcepackagename is None:
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
        archive = self.factory.makeArchive(
            distribution=distroseries.distribution,
            purpose=ArchivePurpose.PPA)
        getUtility(ISourcePackageFormatSelectionSet).add(
            distroseries, SourcePackageFormat.FORMAT_1_0)

        bpb = self.factory.makeBinaryPackageBuild(
            distroarchseries=distroseries.nominatedarchindep, archive=archive,
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

        upload = IStore(PackageUpload).find(PackageUpload).order_by(
            Desc(PackageUpload.id)).first()

        return spr, upload, libraryfilealias

    def ensureDistroSeries(self, distribution_name, distroseries_name):
        distribution = getUtility(IDistributionSet).getByName(
            distribution_name)
        if distribution is None:
            distribution = self.factory.makeDistribution(
                name=distribution_name)
        try:
            distroseries = distribution[distroseries_name]
        except NotFoundError:
            distroseries = self.factory.makeDistroSeries(
                distribution=distribution, name=distroseries_name)
        return distroseries

    def makeJobElementsForPPA(self, owner_name, distribution_name,
                              distroseries_name, archive_name):
        owner = self.factory.makePerson(name=owner_name)
        distroseries = self.ensureDistroSeries(
            distribution_name, distroseries_name)
        archive = self.factory.makeArchive(
            owner=owner, distribution=distroseries.distribution,
            name=archive_name, purpose=ArchivePurpose.PPA)
        sourcepackage_version = "3.8.2-1ubuntu1"
        filename = "foo_%s_i386_translations.tar.gz" % sourcepackage_version
        spph = self.makeAndPublishSourcePackage(
            sourcepackagename="foo", distroseries=distroseries,
            archive=archive)
        packageupload = removeSecurityProxy(self.factory.makePackageUpload(
            distroseries=distroseries, archive=archive))
        packageupload.addSource(spph.sourcepackagerelease)
        libraryfilealias = self.makeTranslationsLFA(filename=filename)
        return spph.sourcepackagerelease, packageupload, libraryfilealias

    def test_parsePath(self):
        filename = "foobar_3.8.2-1ubuntu1_i386_translations.tar.gz"
        parsed_path = RosettaTranslationsUpload.parsePath(filename)
        self.assertEqual(len(parsed_path), 4)
        self.assertEqual(parsed_path[0], "foobar")

    def test_malformed_filename_raises_parsePath_error(self):
        filename = "this_is_clearly_wrong_translations.tar.gz"
        self.assertRaises(ValueError, RosettaTranslationsUpload.parsePath,
                          filename)

    def test_setComponents(self):
        rosetta_upload = RosettaTranslationsUpload()
        self.assertIsNone(rosetta_upload.package_name)

        filename1 = "foobar_3.8.2-1ubuntu1_i386_translations.tar.gz"
        rosetta_upload.setComponents(filename1)
        self.assertEqual(rosetta_upload.package_name, "foobar")

        filename2 = "barfoo_3.8.2-1ubuntu1_i386_translations.tar.gz"
        rosetta_upload.setComponents(filename2)
        self.assertEqual(rosetta_upload.package_name, "barfoo")

        filename3 = "barfoo_malformed_3.8.2-1ubuntu1_i386_translations.tar.gz"
        self.assertRaises(ValueError, rosetta_upload.setComponents, filename3)

    def test_package_name_from_packageupload(self):
        spr, pu, lfa = self.makeJobElements(sourcepackagename="foobar")
        self.assertEqual(pu.package_name, "foobar")

        rosetta_upload = RosettaTranslationsUpload()
        self.assertIsNone(rosetta_upload.package_name)

        rosetta_upload.process(pu, lfa)
        self.assertEqual(rosetta_upload.package_name, pu.package_name)

    def test_package_name_from_lfa_filename(self):
        filename = "hello_3.8.2-1ubuntu1_i386_translations.tar.gz"
        lfa = self.makeTranslationsLFA(filename=filename)

        rosetta_upload = RosettaTranslationsUpload()
        self.assertIsNone(rosetta_upload.package_name)

        nameless_pu = self.factory.makePackageUpload()
        self.assertIsNone(nameless_pu.package_name)

        rosetta_upload.process(nameless_pu, lfa)
        self.assertEqual(rosetta_upload.package_name, "hello")

    def test_package_name_None_raises_error(self):
        rosetta_upload = RosettaTranslationsUpload()
        self.assertIsNone(rosetta_upload.package_name)

        self.assertRaises(AssertionError,
                          rosetta_upload._findSourcePublication, None)

    def test_basic_from_copy(self):
        spr, pu, lfa = self.makeJobElementsFromCopyJob()
        transaction.commit()
        with dbuser("process_accepted"):
            process_rosetta_translations(pu, lfa)

    def test_basic_from_upload(self):
        spr, pu, lfa = self.makeJobElements()
        transaction.commit()
        with dbuser("process_accepted"):
            process_rosetta_translations(pu, lfa)

    def test_correct_job_is_created_from_upload(self):
        spr, packageupload, libraryfilealias = self.makeJobElements()
        transaction.commit()
        with dbuser("process_accepted"):
            process_rosetta_translations(packageupload, libraryfilealias)

        jobs = list(PackageTranslationsUploadJob.iterReady())
        self.assertEqual(1, len(jobs))

        self.assertEqual(spr.upload_distroseries, jobs[0].distroseries)
        self.assertEqual(libraryfilealias, jobs[0].libraryfilealias)
        self.assertEqual(spr.sourcepackagename, jobs[0].sourcepackagename)

    def test_correct_job_is_created_from_copy(self):
        spr, packageupload, libraryfilealias = (
            self.makeJobElementsFromCopyJob())
        transaction.commit()
        with dbuser("process_accepted"):
            process_rosetta_translations(packageupload, libraryfilealias)

        jobs = list(PackageTranslationsUploadJob.iterReady())
        self.assertEqual(1, len(jobs))

        self.assertEqual(spr.upload_distroseries, jobs[0].distroseries)
        self.assertEqual(libraryfilealias, jobs[0].libraryfilealias)
        self.assertEqual(spr.sourcepackagename, jobs[0].sourcepackagename)

    def test_correct_job_is_created_from_redirected_ppa(self):
        spr, packageupload, libraryfilealias = self.makeJobElementsForPPA(
            owner_name="ci-train-ppa-service", distribution_name="ubuntu",
            distroseries_name="vivid", archive_name="stable-phone-overlay")
        self.ensureDistroSeries("ubuntu-rtm", "15.04")
        transaction.commit()
        with dbuser("process_accepted"):
            process_rosetta_translations(packageupload, libraryfilealias)

        jobs = list(PackageTranslationsUploadJob.iterReady())
        self.assertEqual(1, len(jobs))

        self.assertEqual("ubuntu-rtm 15.04", str(jobs[0].distroseries))
        self.assertEqual(libraryfilealias, jobs[0].libraryfilealias)
        self.assertEqual(spr.sourcepackagename, jobs[0].sourcepackagename)

    def test_unredirected_series_in_redirected_ppa_is_skipped(self):
        spr, packageupload, libraryfilealias = self.makeJobElementsForPPA(
            owner_name="ci-train-ppa-service", distribution_name="ubuntu",
            distroseries_name="wily", archive_name="stable-phone-overlay")
        self.ensureDistroSeries("ubuntu-rtm", "15.04")
        transaction.commit()
        with dbuser("process_accepted"):
            process_rosetta_translations(packageupload, libraryfilealias)

        jobs = list(PackageTranslationsUploadJob.iterReady())
        self.assertEqual(0, len(jobs))

    def test_unredirected_ppa_is_skipped(self):
        spr, packageupload, libraryfilealias = self.makeJobElementsForPPA(
            owner_name="ci-train-ppa-service", distribution_name="ubuntu",
            distroseries_name="vivid", archive_name="landing-001")
        self.ensureDistroSeries("ubuntu-rtm", "15.04")
        transaction.commit()
        with dbuser("process_accepted"):
            process_rosetta_translations(packageupload, libraryfilealias)

        jobs = list(PackageTranslationsUploadJob.iterReady())
        self.assertEqual(0, len(jobs))

    def test_skips_packaging_for_primary(self):
        # An upload to a primary archive leaves Packaging records untouched.
        spr, packageupload, libraryfilealias = self.makeJobElements()
        transaction.commit()
        sourcepackage = packageupload.distroseries.getSourcePackage(spr.name)
        self.assertIsNone(sourcepackage.packaging)
        with dbuser("process_accepted"):
            process_rosetta_translations(packageupload, libraryfilealias)
        self.assertIsNone(sourcepackage.packaging)

    def test_skips_packaging_for_redirected_ppa_no_original(self):
        # If there is no suitable Packaging record in the original
        # distroseries, then an upload to a redirected PPA leaves Packaging
        # records untouched.
        spr, packageupload, libraryfilealias = self.makeJobElementsForPPA(
            owner_name="ci-train-ppa-service", distribution_name="ubuntu",
            distroseries_name="vivid", archive_name="stable-phone-overlay")
        self.ensureDistroSeries("ubuntu-rtm", "15.04")
        transaction.commit()
        sourcepackage = packageupload.distroseries.getSourcePackage(spr.name)
        self.assertIsNone(sourcepackage.packaging)
        with dbuser("process_accepted"):
            process_rosetta_translations(packageupload, libraryfilealias)
        self.assertIsNone(sourcepackage.packaging)

    def test_skips_existing_packaging_for_redirected_ppa(self):
        # If there is already a suitable Packaging record in the redirected
        # distroseries, then an upload to a redirected PPA leaves it
        # untouched.
        person = self.factory.makePerson()
        current_upstream = self.factory.makeProductSeries()
        new_upstream = self.factory.makeProductSeries()
        spr, packageupload, libraryfilealias = self.makeJobElementsForPPA(
            owner_name="ci-train-ppa-service", distribution_name="ubuntu",
            distroseries_name="vivid", archive_name="stable-phone-overlay")
        redirected_series = self.ensureDistroSeries("ubuntu-rtm", "15.04")
        sourcepackage = redirected_series.getSourcePackage(spr.name)
        sourcepackage.setPackaging(current_upstream, person)
        original_series = self.ensureDistroSeries("ubuntu", "vivid")
        original_series.getSourcePackage(spr.name).setPackaging(
            new_upstream, person)
        transaction.commit()
        self.assertEqual(
            current_upstream, sourcepackage.packaging.productseries)
        with dbuser("process_accepted"):
            process_rosetta_translations(packageupload, libraryfilealias)
        self.assertEqual(
            current_upstream, sourcepackage.packaging.productseries)

    def test_copies_packaging_for_redirected_ppa(self):
        # If there is no suitable Packaging record in the redirected
        # distroseries but there is one in the original distroseries, then
        # an upload to a redirected PPA copies it from the original.
        person = self.factory.makePerson()
        upstream = self.factory.makeProductSeries()
        spr, packageupload, libraryfilealias = self.makeJobElementsForPPA(
            owner_name="ci-train-ppa-service", distribution_name="ubuntu",
            distroseries_name="vivid", archive_name="stable-phone-overlay")
        redirected_series = self.ensureDistroSeries("ubuntu-rtm", "15.04")
        original_series = self.ensureDistroSeries("ubuntu", "vivid")
        original_series.getSourcePackage(spr.name).setPackaging(
            upstream, person)
        transaction.commit()
        sourcepackage = redirected_series.getSourcePackage(spr.name)
        self.assertIsNone(sourcepackage.packaging)
        with dbuser("process_accepted"):
            process_rosetta_translations(packageupload, libraryfilealias)
        self.assertEqual(upstream, sourcepackage.packaging.productseries)
        # TranslationPackagingJobs are created to handle the Packaging
        # change (one TranslationMergeJob for each of ubuntu/vivid and
        # ubuntu-rtm/15.04).
        jobs = list(TranslationPackagingJob.iterReady())
        self.assertEqual(2, len(jobs))
