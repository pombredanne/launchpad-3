# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Twisted Poppy FTP."""

__metaclass__ = type

import os

from testtools.deferredruntest import (
    AsynchronousDeferredRunTest,
    )
import transaction
from twisted.protocols import ftp
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.ftests.keys_for_tests import gpgkeysdir
from canonical.launchpad.interfaces.gpghandler import IGPGHandler
from canonical.testing.layers import ZopelessDatabaseLayer

from lp.poppy.twistedftp import PoppyFileWriter
from lp.registry.interfaces.gpg import (
    GPGKeyAlgorithm,
    IGPGKeySet)
from lp.services.database.isolation import check_no_transaction
from lp.testing import TestCaseWithFactory
from lp.testing.keyserver import KeyServerTac


class TestPoppyFileWriter(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer
    run_tests_with = AsynchronousDeferredRunTest.make_factory(timeout=20)

    def setUp(self):
        TestCaseWithFactory.setUp(self)

        # Start the test keyserver.  Starting up and tearing this down
        # for each test is expensive, but we don't have a way of having
        # cross-test persistent fixtures yet.  See bug 724349.
        self.tac = KeyServerTac()
        self.tac.setUp()
        self.addCleanup(self.tac.tearDown)

        # Load a key.
        gpg_handler = getUtility(IGPGHandler)
        key_path = os.path.join(gpgkeysdir, 'ftpmaster@canonical.com.pub')
        key_data = open(key_path).read()
        key = gpg_handler.importPublicKey(key_data)
        assert key is not None

        # Make a new user and add the above key to it.
        user = self.factory.makePerson()
        key_set = getUtility(IGPGKeySet)
        user_key = key_set.new(
            ownerID=user.id, keyid=key.keyid, fingerprint=key.fingerprint,
            algorithm=GPGKeyAlgorithm.items[key.algorithm],
            keysize=key.keysize, can_encrypt=key.can_encrypt,
            active=True)
        # validateGPG runs in its own transaction.
        transaction.commit()

        # Locate the directory with test files.
        self.test_files_dir = os.path.join(
            config.root, "lib/lp/soyuz/scripts/tests/upload_test_files/")

    def test_changes_file_with_valid_GPG(self):
        valid_changes_file = os.path.join(
            self.test_files_dir, "etherwake_1.08-1_source.changes")

        def callback(result):
            self.assertIs(None, result)

        with open(valid_changes_file) as opened_file:
            file_writer = PoppyFileWriter(opened_file)
            d = file_writer.close()
            d.addBoth(callback)
            return d

    def test_changes_file_with_invalid_GPG(self):
        invalid_changes_file = os.path.join(
            self.test_files_dir, "broken_source.changes")

        def error_callback(failure):
            self.assertTrue(failure.check, ftp.PermissionDeniedError)
            self.assertIn(
                "Changes file must be signed with a valid GPG signature",
                failure.getErrorMessage())

        def success_callback(result):
            self.fail("Success when there should have been failure.")

        with open(invalid_changes_file) as opened_file:
            file_writer = PoppyFileWriter(opened_file)
            d = file_writer.close()
            d.addCallbacks(success_callback, error_callback)
            return d

    def test_aborts_transaction(self):
        valid_changes_file = os.path.join(
            self.test_files_dir, "etherwake_1.08-1_source.changes")

        def callback(result):
            check_no_transaction()

        with open(valid_changes_file) as opened_file:
            file_writer = PoppyFileWriter(opened_file)
            d = file_writer.close()
            d.addBoth(callback)
            return d
