# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for canonical.launchpad.daemons.tachandler"""

__metaclass__ = type

import os.path
import tempfile

from fixtures import TempDir
import testtools

from canonical.launchpad.daemons.readyservice import LOG_MAGIC
from canonical.launchpad.daemons.tachandler import (
    TacException,
    TacTestSetup,
    )


class TacTestSetupTestCase(testtools.TestCase):
    """Some tests for the error handling of TacTestSetup."""

    def test_missingTac(self):
        """TacTestSetup raises TacException if the tacfile doesn't exist"""
        class MissingTac(TacTestSetup):
            root = '/'
            tacfile = '/file/does/not/exist'
            pidfile = tacfile
            logfile = tacfile
            def setUpRoot(self):
                pass

        self.assertRaises(TacException, MissingTac().setUp)

    def test_couldNotListenTac(self):
        """If the tac fails due to not being able to listen on the needed port,
        TacTestSetup will fail.
        """
        class CouldNotListenTac(TacTestSetup):
            root = os.path.dirname(__file__)
            tacfile = os.path.join(root, 'cannotlisten.tac')
            pidfile = os.path.join(tempfile.gettempdir(), 'cannotlisten.pid')
            logfile = os.path.join(tempfile.gettempdir(), 'cannotlisten.log')
            def setUpRoot(self):
                pass

        self.assertRaises(TacException, CouldNotListenTac().setUp)

    def test_truncateLog(self):
        """truncateLog truncates the log. What did you expect?"""
        tempdir = self.useFixture(TempDir()).path

        class DoNothingTac(TacTestSetup):
            logfile = os.path.join(tempdir, 'nothing.log')

        # Put something in the log file.
        fixture = DoNothingTac()
        with open(fixture.logfile, "wb") as logfile:
            logfile.write("Hello\n")

        # Truncating the log does not remove the log file.
        fixture.truncateLog()
        self.assertTrue(os.path.exists(fixture.logfile))
        with open(fixture.logfile, "rb") as logfile:
            self.assertEqual("", logfile.read())

        # Put something in the log again, along with LOG_MAGIC.
        with open(fixture.logfile, "wb") as logfile:
            logfile.write("One\n")
            logfile.write("Two\n")
            logfile.write("Three, %s\n" % LOG_MAGIC)
            logfile.write("Four\n")

        # Truncating the log leaves everything up to and including the line
        # containing LOG_MAGIC.
        fixture.truncateLog()
        with open(fixture.logfile, "rb") as logfile:
            self.assertEqual(
                "One\nTwo\nThree, %s\n" % LOG_MAGIC,
                logfile.read())
