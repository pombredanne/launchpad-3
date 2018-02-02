# Copyright 2016-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test ArchiveSigningKey."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import os

from testtools.deferredruntest import AsynchronousDeferredRunTest
from twisted.internet import defer
from zope.component import getUtility

from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.interfaces.archivesigningkey import (
    IArchiveSigningKey,
    )
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.services.osutils import write_file
from lp.soyuz.enums import ArchivePurpose
from lp.testing import TestCaseWithFactory
from lp.testing.gpgkeys import gpgkeysdir
from lp.testing.keyserver import InProcessKeyServerFixture
from lp.testing.layers import ZopelessDatabaseLayer


class TestArchiveSigningKey(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer
    run_tests_with = AsynchronousDeferredRunTest.make_factory(timeout=10)

    @defer.inlineCallbacks
    def setUp(self):
        super(TestArchiveSigningKey, self).setUp()
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

    def test_signfile_absolute_within_archive(self):
        filename = os.path.join(self.archive_root, "signme")
        write_file(filename, "sign this")

        signer = IArchiveSigningKey(self.archive)
        signer.signFile(filename)

        signature = filename + '.gpg'
        self.assertTrue(os.path.exists(signature))

    def test_signfile_absolute_outside_archive(self):
        filename = os.path.join(self.temp_dir, "signme")
        write_file(filename, "sign this")

        signer = IArchiveSigningKey(self.archive)
        self.assertRaises(AssertionError, lambda: signer.signFile(filename))

    def test_signfile_relative_within_archive(self):
        filename_relative = "signme"
        filename = os.path.join(self.archive_root, filename_relative)
        write_file(filename, "sign this")

        signer = IArchiveSigningKey(self.archive)
        signer.signFile(filename_relative)

        signature = filename + '.gpg'
        self.assertTrue(os.path.exists(signature))

    def test_signfile_relative_outside_archive(self):
        filename_relative = "../signme"
        filename = os.path.join(self.temp_dir, filename_relative)
        write_file(filename, "sign this")

        signer = IArchiveSigningKey(self.archive)
        self.assertRaises(
            AssertionError, lambda: signer.signFile(filename_relative))
