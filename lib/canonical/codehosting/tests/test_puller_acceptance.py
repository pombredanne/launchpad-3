# Copyright 2007 Canonical Ltd.  All rights reserved.

"""End-to-end tests for the branch puller."""

__metaclass__ = type
__all__ = []


import os
import shutil
from subprocess import PIPE, Popen
import sys
import unittest
from urlparse import urlparse
import xmlrpclib

import transaction

from bzrlib.branch import Branch
from bzrlib.tests import HttpServer
from bzrlib.urlutils import local_path_from_url

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.authserver.tests.harness import AuthserverTacTestSetup
from canonical.codehosting.tests.helpers import BranchTestCase
from canonical.config import config
from canonical.launchpad.interfaces import BranchType, IScriptActivitySet
from canonical.codehosting import branch_id_to_path
from canonical.testing import LaunchpadScriptLayer


class TestBranchPuller(BranchTestCase):
    """Integration tests for the branch puller.

    These tests actually run the supermirror-pull.py script. Instead of
    checking specific behaviour, these tests help ensure that all of the
    components in the branch puller system work together sanely.
    """

    layer = LaunchpadScriptLayer

    def setUp(self):
        super(TestBranchPuller, self).setUp()
        self._puller_script = os.path.join(
            config.root, 'cronscripts', 'supermirror-pull.py')
        self.makeCleanDirectory(config.codehosting.branches_root)
        self.makeCleanDirectory(config.supermirror.branchesdest)
        self.emptyPullQueues()
        authserver_tac = AuthserverTacTestSetup()
        authserver_tac.setUp()
        self.addCleanup(authserver_tac.tearDown)

    def assertMirrored(self, source_path, branch):
        """Assert that 'branch' was mirrored succesfully."""
        # Make sure that we are testing the actual data.
        removeSecurityProxy(branch).sync()
        self.assertEqual(None, branch.mirror_status_message)
        self.assertEqual(branch.last_mirror_attempt, branch.last_mirrored)
        self.assertEqual(0, branch.mirror_failures)
        hosted_branch = Branch.open(source_path)
        mirrored_branch = Branch.open(self.getMirroredPath(branch))
        self.assertEqual(
            hosted_branch.last_revision(), branch.last_mirrored_id)
        self.assertEqual(
            hosted_branch.last_revision(), mirrored_branch.last_revision())

    def assertRanSuccessfully(self, command, retcode, stdout, stderr):
        """Assert that the command ran successfully.

        'Successfully' means that it's return code was 0 and it printed nothing
        to stdout or stderr.
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
        self.assertEqualDiff('', stdout)
        self.assertEqualDiff('', stderr)

    def getHostedPath(self, branch):
        """Return the path of 'branch' in the upload area."""
        return os.path.join(
            config.codehosting.branches_root, branch_id_to_path(branch.id))

    def getMirroredPath(self, branch):
        """Return the path of 'branch' in the supermirror area."""
        return os.path.join(
            config.supermirror.branchesdest, branch_id_to_path(branch.id))

    def makeCleanDirectory(self, path):
        """Guarantee an empty branch upload area."""
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path)

    def pushToBranch(self, branch, tree=None):
        """Push a trivial Bazaar branch to a given Launchpad branch.

        :param branch: A Launchpad Branch object.
        """
        hosted_path = self.getHostedPath(branch)
        if tree is None:
            tree = self.createTemporaryBazaarBranchAndTree()
        out, err = self.run_bzr(
            ['push', '--create-prefix', '-d',
             local_path_from_url(tree.branch.base), hosted_path],
            retcode=None)
        # We want to be sure that a new branch was indeed created.
        self.assertEqual("Created new branch.\n", err)

    def runSubprocess(self, command):
        """Run the given command in a subprocess.

        :param command: A command and arguments given as a list.
        :return: retcode, stdout, stderr
        """
        process = Popen(command, stdout=PIPE, stderr=PIPE)
        output, error = process.communicate()
        return process.returncode, output, error

    def runPuller(self, branch_type):
        """Run the puller script for the given branch type.

        :param branch_type: One of 'upload', 'mirror' or 'import'
        :return: Tuple of command, retcode, output, error. 'command' is the
            executed command as a list, retcode is the process's return code,
            output and error are strings contain the output of the process to
            stdout and stderr respectively.
        """
        command = [
            sys.executable, os.path.join(self._puller_script), '-q',
            branch_type]
        retcode, output, error = self.runSubprocess(command)
        return command, retcode, output, error

    def serveOverHTTP(self, port=0):
        """Serve the current directory over HTTP, returning the server URL."""
        http_server = HttpServer()
        http_server.port = port
        http_server.setUp()
        self.addCleanup(http_server.tearDown)
        return http_server.get_url().rstrip('/')

    def test_fixture(self):
        """Confirm the fixture is set up correctly.

        We want the branch upload area and the supermirror destination area to
        both be empty. We also want the branch pull queue to be empty.
        """
        self.assertEqual([], os.listdir(config.codehosting.branches_root))
        self.assertEqual([], os.listdir(config.supermirror.branchesdest))
        server = xmlrpclib.Server(config.supermirror.authserver_url)
        self.assertEqual(
            [], server.getBranchPullQueue(BranchType.HOSTED.name))
        self.assertEqual(
            [], server.getBranchPullQueue(BranchType.MIRRORED.name))
        self.assertEqual(
            [], server.getBranchPullQueue(BranchType.IMPORTED.name))
        self.failUnless(
            os.path.isfile(self._puller_script),
            "%s doesn't exist" % (self._puller_script,))

    def test_mirrorAHostedBranch(self):
        """Run the puller on a populated hosted branch pull queue."""
        # XXX: JonathanLange 2007-08-21, This test will fail if run by itself,
        # due to an unidentified bug in bzrlib.trace, possibly related to bug
        # 124849.
        branch = self.makeBranch(BranchType.HOSTED)
        self.pushToBranch(branch)
        branch.requestMirror()
        transaction.commit()
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(self.getHostedPath(branch), branch)

    def test_mirrorAHostedLoomBranch(self):
        """Run the puller over a branch with looms enabled."""
        branch = self.makeBranch(BranchType.HOSTED)
        loom_tree = self.makeLoomBranchAndTree('loom')
        self.pushToBranch(branch, loom_tree)
        branch.requestMirror()
        transaction.commit()
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(self.getHostedPath(branch), branch)

    def test_mirrorAPrivateBranch(self):
        """Run the puller with a private branch in the queue."""
        branch = self.makeBranch(BranchType.HOSTED)
        self.pushToBranch(branch)
        branch.requestMirror()
        branch.private = True
        transaction.commit()
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(self.getHostedPath(branch), branch)

    def test_mirrorAMirroredBranch(self):
        """Run the puller on a populated mirrored branch pull queue."""
        branch = self.makeBranch(BranchType.MIRRORED)
        tree = self.createTemporaryBazaarBranchAndTree()
        branch.url = self.serveOverHTTP()
        branch.requestMirror()
        transaction.commit()
        command, retcode, output, error = self.runPuller('mirror')
        self.assertRanSuccessfully(command, retcode, output, error)
        # XXX: The first argument used to be branch.url, but this triggered
        # Bug #193253 where for some reason Branch.open via HTTP makes
        # an incomplete request to the HttpServer leaving a dangling thread.
        # Our test suite now fails tests leaving dangling threads.
        # -- StuartBishop 20080312
        self.assertMirrored(os.getcwd(), branch)

    def _getImportMirrorPort(self):
        """Return the port used to serve imported branches, as specified in
        config.launchpad.bzr_imports_root_url.
        """
        address = urlparse(config.launchpad.bzr_imports_root_url)[1]
        host, port = address.split(':')
        self.assertEqual(
            'localhost', host,
            'bzr_imports_root_url must be configured on localhost: %s'
            % (config.launchpad.bzr_imports_root_url,))
        return int(port)

    def test_mirrorAnImportedBranch(self):
        """Run the puller on a populated imported branch pull queue."""
        # Create the branch in the database.
        branch = self.makeBranch(BranchType.IMPORTED)
        branch.requestMirror()
        transaction.commit()

        # Create the Bazaar branch and serve it in the expected location.
        branch_path = '%08x' % branch.id
        os.mkdir(branch_path)
        self.createTemporaryBazaarBranchAndTree(branch_path)
        self.serveOverHTTP(self._getImportMirrorPort())

        # Run the puller.
        command, retcode, output, error = self.runPuller("import")
        self.assertRanSuccessfully(command, retcode, output, error)

        # XXX: Because of Bug #193253, check the branch is mirrored by going
        # straight to the filesystem, rather than over HTTP. This is to
        # avoid Bazaar opening an HTTP connection that never closes.
        self.assertMirrored(branch_path, branch)

    def test_mirrorEmpty(self):
        """Run the puller on an empty pull queue."""
        command, retcode, output, error = self.runPuller("upload")
        self.assertRanSuccessfully(command, retcode, output, error)

    def test_recordsScriptActivity(self):
        """A record gets created in the ScriptActivity table."""
        script_activity_set = getUtility(IScriptActivitySet)
        self.assertIs(
            script_activity_set.getLastActivity("branch-puller-hosted"),
            None)
        self.runPuller("upload")
        transaction.abort()
        self.assertIsNot(
            script_activity_set.getLastActivity("branch-puller-hosted"),
            None)

    # Possible tests to add:
    # - branch already exists in new location
    # - branch doesn't exist in fs?
    # - different branch exists in new location
    # - running puller while another puller is running
    # - expected output on non-quiet runs


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
