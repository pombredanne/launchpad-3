# Copyright 2007 Canonical Ltd.  All rights reserved.

"""End-to-end tests for the branch puller."""

__metaclass__ = type
__all__ = []


import os
import shutil
from subprocess import PIPE, Popen
import sys
import unittest
import xmlrpclib

from bzrlib.tests import TestCase

from twisted.application import strports

from canonical.authserver.ftests.harness import AuthserverTacTestSetup
from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import cursor, sqlvalues
from canonical.launchpad.interfaces import BranchType
from canonical.testing import LaunchpadZopelessLayer


def _getPort():
    portDescription = config.authserver.port
    kind, args, kwargs = strports.parse(portDescription, None)
    assert kind == 'TCP'
    return int(args[0])


class TestBranchPuller(TestCase):
    """Acceptance tests for the branch puller.

    These tests actually run the supermirror-pull.py script. Instead of
    checking specific behaviour, these tests help ensure that all of the
    components in the branch puller system work together sanely.
    """

    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCase.setUp(self)
        self._puller_script = os.path.join(
            config.root, 'cronscripts', 'supermirror-pull.py')
        self.makeCleanDirectory(config.codehosting.branches_root)
        self.makeCleanDirectory(config.supermirror.branchesdest)
        self.emptyPullQueue()
        authserver_tac = AuthserverTacTestSetup()
        authserver_tac.setUp()
        self.addCleanup(authserver_tac.tearDown)

    def makeCleanDirectory(self, path):
        """Guarantee an empty branch upload area."""
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path)

    def emptyPullQueue(self):
        """Make sure there are no branches to pull."""
        # XXX: JonathanLange 2007-08-20, When the mirror-request branch lands,
        # all of these queries will collapse to 'UPDATE Branch SET
        # mirror_request_time = NULL'.
        LaunchpadZopelessLayer.txn.begin()
        cursor().execute("""
            UPDATE Branch
            SET mirror_request_time = NULL, last_mirror_attempt = %s
            WHERE branch_type = %s"""
            % sqlvalues(UTC_NOW, BranchType.HOSTED))
        cursor().execute("""
            UPDATE Branch
            SET mirror_request_time = NULL, last_mirror_attempt = %s
            WHERE branch_type = %s"""
            % sqlvalues(UTC_NOW, BranchType.MIRRORED))
        cursor().execute("""
            UPDATE ProductSeries
            SET datelastsynced = NULL""")
        cursor().execute("""
            UPDATE Branch
            SET last_mirror_attempt = NULL
            WHERE branch_type = %s"""
            % sqlvalues(BranchType.IMPORTED))
        LaunchpadZopelessLayer.txn.commit()

    def runSubprocess(self, command):
        """Run the given command in a subprocess.

        :param command: A command and arguments given as a list.
        :return: retcode, stdout, stderr
        """
        print command
        process = Popen(command, stdout=PIPE, stderr=PIPE)
        output, error = process.communicate()
        return process.returncode, output, error

    def runPuller(self, branch_type):
        command = [
            sys.executable, os.path.join(self._puller_script), branch_type]
        retcode, output, error = self.runSubprocess(command)
        self.assertRanSuccessfully(command, retcode, output, error)
        return output

    def assertRanSuccessfully(self, command, retcode, stdout, stderr):
        """Assert that the command ran successfully.

        'Successfully' means that it's return code was 0 and it printed nothing
        to stderr.
        """
        message = '\n'.join(
            ['Command: %r' % (command,),
             'Return code: %s' % retcode,
             'Output:',
             stdout,
             '',
             'Error:',
             stderr])
        self.assertEqual(0, retcode, message)
        self.assertEqual('', stderr, message)

    def test_fixture(self):
        """Confirm the fixture is set up correctly.

        We want the branch upload area and the supermirror destination area to
        both be empty. We also want the branch pull queue to be empty. This all
        """
        self.assertEqual([], os.listdir(config.codehosting.branches_root))
        self.assertEqual([], os.listdir(config.supermirror.branchesdest))
        server = xmlrpclib.Server('http://localhost:%s/branch/' % _getPort())
        self.assertEqual([], server.getBranchPullQueue())
        self.failUnless(
            os.path.isfile(self._puller_script),
            "%s doesn't exist" % (self._puller_script,))

    def test_mirror_empty(self):
        """Push a branch up to Launchpad and mirror it."""
        self.runPuller("upload")
        
    # Need
    # - upload a branch
    # - mirror it
    # - check that the branch is in the new location

    # Variations
    # - branch already exists in new location
    # - private branches
    # - mirrored branches?
    # - imported branches?
    # - branch doesn't exist in fs?
    # - different branch exists in new location
    # - running puller while another puller is running

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
