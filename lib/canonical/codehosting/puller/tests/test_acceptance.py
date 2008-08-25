# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

"""End-to-end tests for the branch puller."""

__metaclass__ = type
__all__ = []


import os
from subprocess import PIPE, Popen
import sys
import unittest
from urlparse import urlparse

import transaction

from bzrlib.branch import Branch, BzrBranchFormat7
from bzrlib.bzrdir import format_registry
from bzrlib.tests import HttpServer
from bzrlib.upgrade import upgrade

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.codehosting.puller.tests import PullerBranchTestCase
from canonical.config import config
from canonical.launchpad.interfaces import BranchType, IScriptActivitySet
from canonical.testing import ZopelessAppServerLayer


class TestBranchPuller(PullerBranchTestCase):
    """Integration tests for the branch puller.

    These tests actually run the supermirror-pull.py script. Instead of
    checking specific behaviour, these tests help ensure that all of the
    components in the branch puller system work together sanely.
    """

    layer = ZopelessAppServerLayer

    def setUp(self):
        PullerBranchTestCase.setUp(self)
        self._puller_script = os.path.join(
            config.root, 'cronscripts', 'supermirror-pull.py')
        self.makeCleanDirectory(config.codehosting.branches_root)
        self.makeCleanDirectory(config.supermirror.branchesdest)

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

        'Successfully' means that it's return code was 0 and it printed
        nothing to stdout or stderr.
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
        command = [sys.executable, self._puller_script, '-q', branch_type]
        retcode, output, error = self.runSubprocess(command)
        return command, retcode, output, error

    def serveOverHTTP(self, port=0):
        """Serve the current directory over HTTP, returning the server URL."""
        http_server = HttpServer()
        http_server.port = port
        http_server.setUp()
        self.addCleanup(http_server.tearDown)
        return http_server.get_url().rstrip('/')

    def test_mirrorAHostedBranch(self):
        """Run the puller on a populated hosted branch pull queue."""
        # XXX: JonathanLange 2007-08-21, This test will fail if run by itself,
        # due to an unidentified bug in bzrlib.trace, possibly related to bug
        # 124849.
        db_branch = self.factory.makeBranch(BranchType.HOSTED)
        self.pushToBranch(db_branch)
        db_branch.requestMirror()
        transaction.commit()
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(self.getHostedPath(db_branch), db_branch)

    def test_reMirrorAHostedBranch(self):
        # When the format of a branch changes, we completely remirror it.
        # First we push up and mirror the branch in one format.
        db_branch = self.factory.makeBranch(BranchType.HOSTED)
        pack_tree = self.make_branch_and_tree('pack', format='pack-0.92')
        self.pushToBranch(db_branch, pack_tree)
        db_branch.requestMirror()
        transaction.commit()
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(self.getHostedPath(db_branch), db_branch)
        # Then we upgrade the to a different format and ask for it to be
        # mirrored again.
        upgrade(self.getHostedPath(db_branch), format_registry.get('1.6'))
        transaction.begin()
        db_branch.requestMirror()
        transaction.commit()
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(self.getHostedPath(db_branch), db_branch)
        # In addition, we check that the format of the branch in the mirrored
        # area is what we expect.
        mirrored_branch = Branch.open(self.getMirroredPath(db_branch))
        self.assertIsInstance(mirrored_branch._format, BzrBranchFormat7)

    def test_mirrorAHostedLoomBranch(self):
        """Run the puller over a branch with looms enabled."""
        db_branch = self.factory.makeBranch(BranchType.HOSTED)
        loom_tree = self.makeLoomBranchAndTree('loom')
        self.pushToBranch(db_branch, loom_tree)
        db_branch.requestMirror()
        transaction.commit()
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(self.getHostedPath(db_branch), db_branch)

    def test_mirrorAPrivateBranch(self):
        """Run the puller with a private branch in the queue."""
        db_branch = self.factory.makeBranch(BranchType.HOSTED)
        self.pushToBranch(db_branch)
        db_branch.requestMirror()
        db_branch.private = True
        transaction.commit()
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(self.getHostedPath(db_branch), db_branch)

    def test_mirrorAMirroredBranch(self):
        """Run the puller on a populated mirrored branch pull queue."""
        db_branch = self.factory.makeBranch(BranchType.MIRRORED)
        tree = self.make_branch_and_tree('.')
        tree.commit('rev1')
        db_branch.url = self.serveOverHTTP()
        db_branch.requestMirror()
        transaction.commit()
        command, retcode, output, error = self.runPuller('mirror')
        self.assertRanSuccessfully(command, retcode, output, error)
        # XXX: The first argument used to be db_branch.url, but this triggered
        # Bug #193253 where for some reason Branch.open via HTTP makes
        # an incomplete request to the HttpServer leaving a dangling thread.
        # Our test suite now fails tests leaving dangling threads.
        # -- StuartBishop 20080312
        self.assertMirrored(tree.basedir, db_branch)

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
        db_branch = self.factory.makeBranch(BranchType.IMPORTED)
        db_branch.requestMirror()
        transaction.commit()

        # Create the Bazaar branch and serve it in the expected location.
        branch_path = '%08x' % db_branch.id
        os.mkdir(branch_path)
        tree = self.make_branch_and_tree(branch_path)
        tree.commit('rev1')
        self.serveOverHTTP(self._getImportMirrorPort())

        # Run the puller.
        command, retcode, output, error = self.runPuller("import")
        self.assertRanSuccessfully(command, retcode, output, error)

        # XXX: Because of Bug #193253, check the branch is mirrored by going
        # straight to the filesystem, rather than over HTTP. This is to
        # avoid Bazaar opening an HTTP connection that never closes.
        self.assertMirrored(branch_path, db_branch)

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
