# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test ddtp-tarball custom uploads.

See also lp.soyuz.tests.test_distroseriesqueue_ddtp_tarball for high-level
tests of ddtp-tarball upload and queue manipulation.
"""

import os

from lp.archivepublisher.ddtp_tarball import process_ddtp_tarball
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.testing import TestCase


class TestDdtpTarball(TestCase):

    def setUp(self):
        super(TestDdtpTarball, self).setUp()
        self.temp_dir = self.makeTemporaryDirectory()
        self.suite = "distroseries"
        # CustomUpload.installFiles requires a umask of 022.
        old_umask = os.umask(022)
        self.addCleanup(os.umask, old_umask)

    def openArchive(self, version):
        self.path = os.path.join(
            self.temp_dir, "translations_main_%s.tar.gz" % version)
        self.buffer = open(self.path, "wb")
        self.archive = LaunchpadWriteTarFile(self.buffer)

    def process(self):
        self.archive.close()
        self.buffer.close()
        process_ddtp_tarball(self.temp_dir, self.path, self.suite)

    def getTranslationsPath(self, filename):
        return os.path.join(
            self.temp_dir, "dists", self.suite, "main", "i18n", filename)

    def test_basic(self):
        # Processing a simple correct tar file works.
        self.openArchive("20060728")
        self.archive.add_file("i18n/Translation-de", "")
        self.process()
        self.assertTrue(os.path.exists(
            self.getTranslationsPath("Translation-de")))

    def test_ignores_empty_directories(self):
        # Empty directories in the tarball are not extracted.
        self.openArchive("20060728")
        self.archive.add_file("i18n/Translation-de", "")
        self.archive.add_directory("i18n/foo")
        self.process()
        self.assertTrue(os.path.exists(
            self.getTranslationsPath("Translation-de")))
        self.assertFalse(os.path.exists(self.getTranslationsPath("foo")))

    def test_partial_update(self):
        # If a DDTP tarball only contains a subset of published translation
        # files, these are updated and the rest are left untouched.
        self.openArchive("20060728")
        self.archive.add_file("i18n/Translation-bn", "bn")
        self.archive.add_file("i18n/Translation-ca", "ca")
        self.process()
        with open(self.getTranslationsPath("Translation-bn")) as bn_file:
            self.assertEqual("bn", bn_file.read())
        with open(self.getTranslationsPath("Translation-ca")) as ca_file:
            self.assertEqual("ca", ca_file.read())
        self.openArchive("20060817")
        self.archive.add_file("i18n/Translation-bn", "new bn")
        self.process()
        with open(self.getTranslationsPath("Translation-bn")) as bn_file:
            self.assertEqual("new bn", bn_file.read())
        with open(self.getTranslationsPath("Translation-ca")) as ca_file:
            self.assertEqual("ca", ca_file.read())

    def test_breaks_hard_links(self):
        # Our archive uses dsync to replace identical files with hard links
        # in order to save some space.  tarfile.extract overwrites
        # pre-existing files rather than creating new files and moving them
        # into place, so making this work requires special care.  Test that
        # that care has been taken.
        self.openArchive("20060728")
        self.archive.add_file("i18n/Translation-ca", "")
        self.process()
        ca = self.getTranslationsPath("Translation-ca")
        bn = self.getTranslationsPath("Translation-bn")
        os.link(ca, bn)
        self.assertTrue(os.path.exists(bn))
        self.assertEqual(2, os.stat(bn).st_nlink)
        self.assertEqual(2, os.stat(ca).st_nlink)
        self.openArchive("20060817")
        self.archive.add_file("i18n/Translation-bn", "break hard link")
        self.process()
        with open(bn) as bn_file:
            self.assertEqual("break hard link", bn_file.read())
        with open(ca) as ca_file:
            self.assertEqual("", ca_file.read())
        self.assertEqual(1, os.stat(bn).st_nlink)
        self.assertEqual(1, os.stat(ca).st_nlink)
