# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test rosetta-translations custom uploads.

See also lp.soyuz.tests.test_distroseriesqueue_rosetta_translations for
high-level tests of rosetta-translations upload and queue manipulation.
"""

import transaction

from lp.archivepublisher.rosetta_translations import (
    process_rosetta_translations,
    )
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.soyuz.model.packagetranslationsuploadjob import (
    PackageTranslationsUploadJob,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadZopelessLayer


class TestRosettaTranslations(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

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

    def makeJobElements(self):
        sourcepackagename = self.factory.makeSourcePackageName(name="foo")
        packageupload = self.factory.makeSourcePackageUpload(
            sourcepackagename=sourcepackagename)
        libraryfilealias = self.makeTranslationsLFA()
        return packageupload, libraryfilealias

    def test_basic(self):
        packageupload, libraryfilealias = self.makeJobElements()
        transaction.commit()
        process_rosetta_translations(packageupload, libraryfilealias)

    def test_correct_job_is_created(self):
        packageupload, libraryfilealias = self.makeJobElements()
        transaction.commit()
        process_rosetta_translations(packageupload, libraryfilealias)

        jobs = list(PackageTranslationsUploadJob.iterReady())
        self.assertEqual(1, len(jobs))

        self.assertEqual(packageupload.sourcepackagerelease,
                jobs[0].sourcepackagerelease)
        self.assertEqual(libraryfilealias, jobs[0].libraryfilealias)
