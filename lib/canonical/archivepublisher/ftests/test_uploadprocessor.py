# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for uploadprocessor.py."""

__metaclass__ = type

import os
from shutil import rmtree
from tempfile import mkdtemp
import transaction
import unittest

from canonical.archivepublisher.tests.test_uploadprocessor import (
    MockOptions, MockLogger)
from canonical.archivepublisher.uploadpolicy import AbstractUploadPolicy
from canonical.archivepublisher.uploadprocessor import UploadProcessor

from canonical.config import config

from canonical.launchpad.ftests import login, ANONYMOUS, logout
from canonical.launchpad.mail import stub

from canonical.testing import LaunchpadFunctionalLayer


class BrokenUploadPolicy(AbstractUploadPolicy):
    """A broken upload policy, to test error handling."""
    
    def __init__(self):
        AbstractUploadPolicy.__init__(self)
        self.name = "broken"
        self.unsigned_changes_ok = True
        self.unsigned_dsc_ok = True

    def setDistroReleaseAndPocket(self, dr_name):
        """Raise an exception upload processing is not expecting."""
        raise Exception("Exception raised by BrokenUploadPolicy for testing.")


class TestUploadProcessor(unittest.TestCase):
    """Functional tests for uploadprocessor.py."""
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)
        self.queue_folder = mkdtemp()
        os.makedirs(os.path.join(self.queue_folder, "incoming"))
        
    def tearDown(self):
        logout()
        rmtree(self.queue_folder)
        
    def testRejectionEmailForUnhandledException(self):
        """Test there's a rejection email when nascentupload breaks.

        If a developer makes an upload which finds a bug in nascentupload,
        and an unhandled exception occurs, we should try to send a
        rejection email. We'll test that this works, in a case where we
        will have the right information to send the email before the
        error occurs.

        If we haven't extracted enough information to send a rejection
        email when things break, trying to send one will raise a new
        exception, and the upload will fail silently as before. We don't
        test this case.

        See bug 35965.
        """
        test_files_dir = os.path.join(config.root,
            "lib/canonical/archivepublisher/tests/data/suite")

        # Register our broken upload policy
        AbstractUploadPolicy._registerPolicy(BrokenUploadPolicy)

        # Set up the uploadprocessor with appropriate options and logger
        options = MockOptions()
        options.base_fsroot = self.queue_folder
        options.leafname = None
        options.distro = "ubuntu"
        options.nomails = False
        options.context = 'broken'
        log = MockLogger()
        uploadprocessor = UploadProcessor(options, transaction, log)

        # Place a suitable upload in the queue. This one is one of
        # Daniel's.
        os.system("cp -a %s %s" %
            (os.path.join(test_files_dir, "baz_1.0-1"),
             os.path.join(self.queue_folder, "incoming")))

        # Try to process it
        uploadprocessor.processUploadQueue()

        # Check the mailer stub has a rejection email for Daniel
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        daniel = "Daniel Silverstone <daniel.silverstone@canonical.com>"
        self.assertEqual(to_addrs, [daniel])
        self.assertTrue("Unhandled exception processing upload: Exception "
                        "raised by BrokenUploadPolicy for testing." in raw_msg)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

        
