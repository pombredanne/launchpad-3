#! /usr/bin/python2.4
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test `reupload_translations` and `ReuploadPackageTranslations`."""

__metaclass__ = type

from unittest import TestLoader

import re
from StringIO import StringIO
import tarfile
import transaction

from zope.security.proxy import removeSecurityProxy

from canonical.testing import LaunchpadZopelessLayer
from lp.testing import TestCaseWithFactory
from canonical.launchpad.scripts.tests import run_script

from canonical.launchpad.database.librarian import LibraryFileAliasSet
from lp.registry.model.sourcepackage import SourcePackage
from lp.translations.model.translationimportqueue import (
    TranslationImportQueue)

from lp.translations.scripts.reupload_translations import (
    ReuploadPackageTranslations)


class UploadInjector:
    def __init__(self, script, tar_alias):
        self.tar_alias = tar_alias
        self.script = script
        self.original_findPackage = script._findPackage

    def __call__(self, name):
        package = self.original_findPackage(name)
        removeSecurityProxy(package).getLatestTranslationsUploads = (
            self._fakeTranslationsUpload)
        return package

    def _fakeTranslationsUpload(self):
        return [self.tar_alias]


def upload_tarball(translation_files):
    """Create a tarball and upload it to the Librarian.

    :param translation_files: A dict mapping filenames to file contents.
    :return: A `LibraryFileAlias`.
    """
    buf = StringIO()
    tarball = tarfile.open('', 'w:gz', buf)
    for name, contents in translation_files.iteritems():
        pseudofile = StringIO(contents)
        tarinfo = tarfile.TarInfo()
        tarinfo.name = name
        tarinfo.size = len(contents)
        tarinfo.type = tarfile.REGTYPE
        tarball.addfile(tarinfo, pseudofile)

    tarball.close()
    buf.flush()
    tarsize = buf.tell()
    buf.seek(0)

    return LibraryFileAliasSet().create(
        'uploads.tar.gz', tarsize, buf, 'application/x-gtar')


def summarize_translations_queue(sourcepackage):
    """Describe queue entries for `sourcepackage` as a name/contents dict."""
    entries = TranslationImportQueue().getAllEntries(sourcepackage)
    return dict((entry.path, entry.content.read()) for entry in entries)


class TestReuploadPackageTranslations(TestCaseWithFactory):
    """Test `ReuploadPackageTranslations`."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestReuploadPackageTranslations, self).setUp()
        sourcepackagename = self.factory.makeSourcePackageName()
        distroseries = self.factory.makeDistroRelease()
        self.sourcepackage = SourcePackage(sourcepackagename, distroseries)
        self.script = ReuploadPackageTranslations('reupload', test_args=[
            '-d', distroseries.distribution.name,
            '-s', distroseries.name,
            '-p', sourcepackagename.name,
            '-qqq'])

    def test_findPackage(self):
        # _findPackage finds a SourcePackage by name.
        self.script._setDistroDetails()
        found_package = self.script._findPackage(
            self.sourcepackage.sourcepackagename.name)
        self.assertEqual(self.sourcepackage, found_package)

    def test_processPackage_nothing(self):
        # A package need not have a translations upload.  The script
        # notices this but does nothing about it.
        self.script.main()
        self.assertEqual(
            [self.sourcepackage], self.script.uploadless_packages)

    def test_processPackage(self):
        # _processPackage will fetch the package's latest translations
        # upload from the Librarian and re-import it.
        translation_files = {
            'po/messages.pot': '# pot',
            'po/nl.po': '# nl',
        }
        tar_alias = upload_tarball(translation_files)

        # Force Librarian update
        transaction.commit()

        self.script._findPackage = UploadInjector(self.script, tar_alias)
        self.script.main()
        self.assertEqual([], self.script.uploadless_packages)

        # Force Librarian update
        transaction.commit()

        queue_summary = summarize_translations_queue(self.sourcepackage)
        self.assertEqual(translation_files, queue_summary)


class TestReuploadScript(TestCaseWithFactory):
    """Test reupload-translations script."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestReuploadScript, self).setUp()
        self.distroseries = self.factory.makeDistroRelease()
        self.sourcepackagename1 = self.factory.makeSourcePackageName()
        self.sourcepackagename2 = self.factory.makeSourcePackageName()
        transaction.commit()

    def test_reupload_translations(self):
        """Test a run of the script."""
        retcode, stdout, stderr = run_script(
            'scripts/rosetta/reupload-translations.py', [
                '-d', self.distroseries.distribution.name,
                '-s', self.distroseries.name,
                '-p', self.sourcepackagename1.name,
                '-p', self.sourcepackagename2.name,
                '-vvv',
                '--dry-run',
            ])

        self.assertEqual(0, retcode)
        self.assertEqual('', stdout)

        expected_output = (
            "INFO\s*Dry run.  Not really uploading anything.\n"
            "INFO\s*Processing [^\s]+ in .*\n"
            "WARNING\s*Found no translations upload for .*\n"
            "INFO\s*Processing [^\s]+ in .*\n"
            "WARNING\s*Found no translations upload for .*\n"
            "INFO\s*Done.\n")
        self.assertTrue(re.match(expected_output, stderr))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
