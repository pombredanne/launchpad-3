# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from testtools.content import text_content
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.tests import block_on_job
from lp.services.mail.sendmail import format_address_for_person
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.soyuz.enums import PackageUploadCustomFormat
from lp.soyuz.interfaces.packagetranslationsuploadjob import (
    IPackageTranslationsUploadJob,
    IPackageTranslationsUploadJobSource,
    )
from lp.soyuz.model.packagetranslationsuploadjob import (
    PackageTranslationsUploadJob,
    )
from lp.testing import (
    person_logged_in,
    run_script,
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.dbuser import dbuser
from lp.testing.fakemethod import FakeMethod
from lp.testing.layers import (
    CeleryJobLayer,
    LaunchpadZopelessLayer,
    )
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    )


class LocalTestHelper(TestCaseWithFactory):

    def makeJob(self, archive=None, distroseries=None, tar_content=None):
        requester = self.factory.makePerson()
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.getOrMakeSourcePackageName("foobar")
        if archive is None:
            archive = distroseries.main_archive
        libraryfilealias = self.makeTranslationsLFA(tar_content)
        self.factory.makeSourcePackage(sourcepackagename=sourcepackagename,
            distroseries=distroseries, publish=True)
        spr = self.factory.makeSourcePackageRelease(
            sourcepackagename=sourcepackagename,
            distroseries=distroseries)
        upload = removeSecurityProxy(self.factory.makePackageUpload(
            distroseries=distroseries))

        upload.addSource(spr)

        upload.addCustom(
            libraryfilealias,
            custom_type=PackageUploadCustomFormat.ROSETTA_TRANSLATIONS)

        return (upload,
                getUtility(IPackageTranslationsUploadJobSource).create(
                    upload, spr, libraryfilealias, requester))

    def makeTranslationsLFA(self, tar_content=None):
        """Create an LibraryFileAlias containing dummy translation data."""
        if tar_content is None:
            tar_content = {
                'source/po/foo.pot': 'Foo template',
                'source/po/eo.po': 'Foo translation',
                }
        tarfile_content = LaunchpadWriteTarFile.files_to_string(
            tar_content)
        return self.factory.makeLibraryFileAlias(content=tarfile_content)


class TestPackageTranslationsUploadJob(LocalTestHelper):

    layer = LaunchpadZopelessLayer

    def test_job_implements_IPackageTranslationsUploadJob(self):
        _, job = self.makeJob()
        self.assertTrue(verifyObject(IPackageTranslationsUploadJob, job))

    def test_job_source_implements_IPackageTranslationsUploadJobSource(self):
        job_source = getUtility(IPackageTranslationsUploadJobSource)
        self.assertTrue(verifyObject(IPackageTranslationsUploadJobSource,
                                     job_source))

    def test_iterReady(self):
        _, job1 = self.makeJob()
        removeSecurityProxy(job1).job._status = JobStatus.COMPLETED
        _, job2 = self.makeJob()
        jobs = list(PackageTranslationsUploadJob.iterReady())
        self.assertEqual(1, len(jobs))

    def test_getErrorRecipients_requester(self):
        _, job = self.makeJob()
        email = format_address_for_person(job.requester)
        self.assertEquals([email], job.getErrorRecipients())
        removeSecurityProxy(job).requester = None
        self.assertEquals([], job.getErrorRecipients())

    def test_run(self):
        archive = self.factory.makeArchive()
        packageupload, job = self.makeJob(archive=archive)
        method = FakeMethod()
        removeSecurityProxy(job).attachTranslationFiles = method
        transaction.commit()
        job.run()
        self.assertEqual(method.call_count, 1)

    def test_smoke(self):
        tar_content = {
            'source/po/foobar.pot': 'FooBar template',
        }
        packageupload, job = self.makeJob(tar_content=tar_content)
        transaction.commit()
        out, err, exit_code = run_script(
            "LP_DEBUG_SQL=1 cronscripts/process-job-source.py -vv %s" % (
                IPackageTranslationsUploadJobSource.getName()))

        self.addDetail("stdout", text_content(out))
        self.addDetail("stderr", text_content(err))

        self.assertEqual(0, exit_code)
        translation_import_queue = getUtility(ITranslationImportQueue)
        entries_in_queue = translation_import_queue.getAllEntries(
            target=packageupload.sourcepackagerelease.sourcepackage)

        self.assertEqual(1, entries_in_queue.count())
        # Check if the file in tar_content is queued:
        self.assertTrue("po/foobar.pot", entries_in_queue[0].path)


class TestViaCelery(LocalTestHelper):
    """PackageTranslationsUploadJob runs under Celery."""

    layer = CeleryJobLayer

    def test_run(self):
        self.useFixture(FeatureFixture({
            'jobs.celery.enabled_classes': 'PackageTranslationsUploadJob',
        }))

        packageupload, job = self.makeJob()
        with block_on_job(self):
            transaction.commit()
        translation_import_queue = getUtility(ITranslationImportQueue)
        entries_in_queue = translation_import_queue.getAllEntries(
            target=packageupload.sourcepackagerelease.sourcepackage).count()
        self.assertEqual(2, entries_in_queue)


class TestAttachTranslationFiles(LocalTestHelper):
    """Tests for attachTranslationFiles."""

    layer = LaunchpadZopelessLayer

    def test_attachTranslationFiles__no_translation_sharing(self):
        # If translation sharing is disabled, attachTranslationFiles() creates
        # a job in the translation import queue.

        packageupload, job = self.makeJob()
        spr = packageupload.sourcepackagerelease

        self.assertFalse(spr.sourcepackage.has_sharing_translation_templates)
        transaction.commit()
        with dbuser('upload_package_translations_job'):
            job.attachTranslationFiles(True)
        translation_import_queue = getUtility(ITranslationImportQueue)
        entries_in_queue = translation_import_queue.getAllEntries(
            target=spr.sourcepackage).count()
        self.assertEqual(2, entries_in_queue)

    def test_attachTranslationFiles__translation_sharing(self):
        # If translation sharing is enabled, attachTranslationFiles() only
        # attaches templates.
        packageupload, job = self.makeJob()
        sourcepackage = packageupload.sourcepackagerelease.sourcepackage
        productseries = self.factory.makeProductSeries()

        self.factory.makePOTemplate(productseries=productseries)
        with person_logged_in(sourcepackage.distroseries.owner):
            sourcepackage.setPackaging(
                productseries, sourcepackage.distroseries.owner)
        self.assertTrue(sourcepackage.has_sharing_translation_templates)
        transaction.commit()
        with dbuser('upload_package_translations_job'):
            job.attachTranslationFiles(True)
        translation_import_queue = getUtility(ITranslationImportQueue)
        entries = translation_import_queue.getAllEntries(target=sourcepackage)
        self.assertEqual(1, entries.count())
        self.assertTrue(entries[0].path.endswith('.pot'))
