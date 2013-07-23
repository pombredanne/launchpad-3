# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os.path

from testtools.content import text_content
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.soyuz.enums import (
    PackageDiffStatus,
    )
from lp.soyuz.interfaces.translationsuploadjob import (
    ITranslationsUploadJob,
    ITranslationsUploadJobSource,
    )
from lp.soyuz.model.translationsuploadjob import TranslationsUploadJob
from lp.services.config import config
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import JobStatus
from lp.testing import (
    admin_logged_in,
    run_script,
    TestCaseWithFactory,
    verifyObject,
    )
from lp.services.job.tests import block_on_job
from lp.testing.fakemethod import FakeMethod
from lp.testing.layers import (
    CeleryJobLayer,
    LaunchpadZopelessLayer,
    )
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    )


class LocalTestHelper(TestCaseWithFactory):

    def makeJob(self, spr_creator=None, archive=None,
                sourcepackagerelease=None, libraryfilealias=None):
        if spr_creator is None:
            creator = self.factory.makePerson()
        else:
            creator = self.factory.makePerson(name=spr_creator)
        if archive is None:
            archive = self.factory.makeArchive()
        if sourcepackagerelease is None:
            sourcepackagerelease = self.factory.makeSourcePackageRelease(
                archive=archive, creator=creator)
        if libraryfilealias is None:
            libraryfilealias = self.makeTranslationsLFA()
        return (sourcepackagerelease,
                getUtility(ITranslationsUploadJobSource).create(
                    sourcepackagerelease, libraryfilealias))

    def makeTranslationsLFA(self):
        """Create an LibraryFileAlias containing dummy translation data."""
        test_tar_content = {
            'source/po/foo.pot': 'Foo template',
            'source/po/eo.po': 'Foo translation',
            }
        tarfile_content = LaunchpadWriteTarFile.files_to_string(
            test_tar_content)
        return self.factory.makeLibraryFileAlias(content=tarfile_content)


class TestTranslationsUploadJob(LocalTestHelper):

    layer = LaunchpadZopelessLayer

    def test_job_implements_ITranslationsUploadJob(self):
        _, job = self.makeJob()
        self.assertTrue(verifyObject(ITranslationsUploadJob, job))

    def test_job_source_implements_ITranslationsUploadJobSource(self):
        job_source = getUtility(ITranslationsUploadJobSource)
        self.assertTrue(verifyObject(ITranslationsUploadJobSource, job_source))

    def test_iterReady(self):
        _, job1 = self.makeJob()
        removeSecurityProxy(job1).job._status = JobStatus.COMPLETED
        _, job2 = self.makeJob()
        jobs = list(TranslationsUploadJob.iterReady())
        self.assertEqual(1, len(jobs))

    def test_importer_is_creator(self):
        spr, job = self.makeJob(spr_creator="foobar")
        transaction.commit()
        job.run()
        translation_import_queue = getUtility(ITranslationImportQueue)
        entries_in_queue = translation_import_queue.getAllEntries(
            target=spr.sourcepackage)
        self.assertEqual(entries_in_queue[0].importer.name, "foobar")

    def test_run(self):
        archive = self.factory.makeArchive()
        foo_pkg = self.factory.makeSourcePackageRelease(archive=archive)
        method = FakeMethod()
        removeSecurityProxy(foo_pkg).attachTranslationFiles = method
        spr, job = self.makeJob(archive=archive, sourcepackagerelease=foo_pkg)
        transaction.commit()
        job.run()
        self.assertEqual(method.call_count, 1)

    def test_smoke(self):
        spr, job = self.makeJob()
        transaction.commit()
        out, err, exit_code = run_script(
            "LP_DEBUG_SQL=1 cronscripts/process-job-source.py -vv %s" % (
                ITranslationsUploadJobSource.getName()))

        self.addDetail("stdout", text_content(out))
        self.addDetail("stderr", text_content(err))

        self.assertEqual(0, exit_code)
        translation_import_queue = getUtility(ITranslationImportQueue)
        entries_in_queue = translation_import_queue.getAllEntries(
                target=spr.sourcepackage).count()
        self.assertEqual(2, entries_in_queue)


class TestViaCelery(LocalTestHelper):
    """TranslationsUploadJob runs under Celery."""

    layer = CeleryJobLayer

    def test_run(self):
        self.useFixture(FeatureFixture({
            'jobs.celery.enabled_classes': 'TranslationsUploadJob',
        }))

        spr, job = self.makeJob()
        with block_on_job(self):
            transaction.commit()
        translation_import_queue = getUtility(ITranslationImportQueue)
        entries_in_queue = translation_import_queue.getAllEntries(
                target=spr.sourcepackage).count()
        self.assertEqual(2, entries_in_queue)
