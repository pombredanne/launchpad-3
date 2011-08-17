# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for canonical.launchpad.daemons.tachandler"""

__metaclass__ = type

import os.path
import subprocess
import tempfile
import unittest

from canonical.launchpad.daemons.tachandler import (
    TacException,
    TacTestSetup,
    )
from lp.services.osutils import get_pid_from_file


class TacTestSetupTestCase(unittest.TestCase):
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

    def test_pidForNotRunningProcess(self):
        """If the tac fails due to not being able to listen on the needed port,
        TacTestSetup will fail.
        """
        class OkayTac(TacTestSetup):
            root = os.path.dirname(__file__)
            tacfile = os.path.join(root, 'okay.tac')
            pidfile = os.path.join(tempfile.gettempdir(), 'okay.pid')
            logfile = os.path.join(tempfile.gettempdir(), 'okay.log')
            def setUpRoot(self):
                pass

        # Run a short-lived process with the intention of using its pid in the
        # next step. Linux uses pids sequentially (from the information I've
        # been able to discover) so this approach is safe as long as we don't
        # delay until pids wrap... which should be a very long time unless the
        # machine is seriously busy.
        process = subprocess.Popen("true")
        process.wait()

        # Put the (now bogus) pid in the pid file.
        with open(OkayTac.pidfile, "wb") as pidfile:
            pidfile.write(str(process.pid))

        with OkayTac() as fixture:
            self.assertNotEqual(
                process.pid, get_pid_from_file(fixture.pidfile))
