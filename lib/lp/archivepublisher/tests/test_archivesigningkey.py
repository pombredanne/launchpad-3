# Copyright 2016-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test ArchiveSigningKey."""

__metaclass__ = type

import os
from textwrap import dedent

from testtools.deferredruntest import AsynchronousDeferredRunTest
from testtools.matchers import FileContains
from twisted.internet import defer
from zope.component import getUtility

from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.interfaces.archivesigningkey import (
    IArchiveSigningKey,
    ISignableArchive,
    )
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.archivepublisher.tests.test_run_parts import RunPartsMixin
from lp.services.osutils import write_file
from lp.soyuz.enums import ArchivePurpose
from lp.testing import TestCaseWithFactory
from lp.testing.gpgkeys import gpgkeysdir
from lp.testing.keyserver import InProcessKeyServerFixture
from lp.testing.layers import ZopelessDatabaseLayer


class TestSignableArchiveWithSigningKey(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer
    run_tests_with = AsynchronousDeferredRunTest.make_factory(timeout=10)

    @defer.inlineCallbacks
    def setUp(self):
        super(TestSignableArchiveWithSigningKey, self).setUp()
        self.temp_dir = self.makeTemporaryDirectory()
        self.distro = self.factory.makeDistribution()
        db_pubconf = getUtility(IPublisherConfigSet).getByDistribution(
            self.distro)
        db_pubconf.root_dir = unicode(self.temp_dir)
        self.archive = self.factory.makeArchive(
            distribution=self.distro, purpose=ArchivePurpose.PRIMARY)
        self.archive_root = getPubConfig(self.archive).archiveroot
        self.suite = "distroseries"

        with InProcessKeyServerFixture() as keyserver:
            yield keyserver.start()
            key_path = os.path.join(gpgkeysdir, 'ppa-sample@canonical.com.sec')
            yield IArchiveSigningKey(self.archive).setSigningKey(
                key_path, async_keyserver=True)

    def test_signFile_absolute_within_archive(self):
        filename = os.path.join(self.archive_root, "signme")
        write_file(filename, "sign this")

        signer = ISignableArchive(self.archive)
        self.assertTrue(signer.can_sign)
        signer.signFile(self.suite, filename)

        signature = filename + '.gpg'
        self.assertTrue(os.path.exists(signature))

    def test_signFile_absolute_outside_archive(self):
        filename = os.path.join(self.temp_dir, "signme")
        write_file(filename, "sign this")

        signer = ISignableArchive(self.archive)
        self.assertTrue(signer.can_sign)
        self.assertRaises(
            AssertionError, lambda: signer.signFile(self.suite, filename))

    def test_signFile_relative_within_archive(self):
        filename_relative = "signme"
        filename = os.path.join(self.archive_root, filename_relative)
        write_file(filename, "sign this")

        signer = ISignableArchive(self.archive)
        self.assertTrue(signer.can_sign)
        signer.signFile(self.suite, filename_relative)

        signature = filename + '.gpg'
        self.assertTrue(os.path.exists(signature))

    def test_signFile_relative_outside_archive(self):
        filename_relative = "../signme"
        filename = os.path.join(self.temp_dir, filename_relative)
        write_file(filename, "sign this")

        signer = ISignableArchive(self.archive)
        self.assertTrue(signer.can_sign)
        self.assertRaises(
            AssertionError,
            lambda: signer.signFile(self.suite, filename_relative))


class TestSignableArchiveWithRunParts(RunPartsMixin, TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestSignableArchiveWithRunParts, self).setUp()
        self.temp_dir = self.makeTemporaryDirectory()
        self.distro = self.factory.makeDistribution()
        db_pubconf = getUtility(IPublisherConfigSet).getByDistribution(
            self.distro)
        db_pubconf.root_dir = unicode(self.temp_dir)
        self.archive = self.factory.makeArchive(
            distribution=self.distro, purpose=ArchivePurpose.PRIMARY)
        self.archive_root = getPubConfig(self.archive).archiveroot
        self.suite = "distroseries"
        self.enableRunParts(distribution_name=self.distro.name)
        with open(os.path.join(
                self.parts_directory, self.distro.name, "sign.d",
                "10-sign"), "w") as sign_script:
            sign_script.write(dedent("""\
                #! /bin/sh
                echo "$MODE signature of $INPUT_PATH ($DISTRIBUTION/$SUITE)" \\
                    >"$OUTPUT_PATH"
                """))
            os.fchmod(sign_script.fileno(), 0o755)

    def test_signRepository_runs_parts(self):
        suite_dir = os.path.join(self.archive_root, "dists", self.suite)
        release_path = os.path.join(suite_dir, "Release")
        write_file(release_path, "Release contents")

        signer = ISignableArchive(self.archive)
        self.assertTrue(signer.can_sign)
        signer.signRepository(self.suite)

        self.assertThat(
            os.path.join(suite_dir, "Release.gpg"),
            FileContains(
                "detached signature of %s (%s/%s)\n" %
                (release_path, self.distro.name, self.suite)))
        self.assertThat(
            os.path.join(suite_dir, "InRelease"),
            FileContains(
                "clear signature of %s (%s/%s)\n" %
                (release_path, self.distro.name, self.suite)))

    def test_signFile_runs_parts(self):
        filename = os.path.join(self.archive_root, "signme")
        write_file(filename, "sign this")

        signer = ISignableArchive(self.archive)
        self.assertTrue(signer.can_sign)
        signer.signFile(self.suite, filename)

        self.assertThat(
            "%s.gpg" % filename,
            FileContains(
                "detached signature of %s (%s/%s)\n" %
                (filename, self.distro.name, self.suite)))
