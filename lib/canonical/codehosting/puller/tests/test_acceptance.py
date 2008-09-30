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
from bzrlib.bzrdir import BzrDir, format_registry
from bzrlib.repofmt.pack_repo import RepositoryFormatKnitPack5
from bzrlib.tests import HttpServer
from bzrlib.transport import get_transport
from bzrlib.upgrade import upgrade

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.codehosting.branchfs import get_puller_server
from canonical.codehosting.bzrutils import ensure_base
from canonical.codehosting.puller.tests import PullerBranchTestCase
from canonical.config import config
from canonical.launchpad.interfaces import (
    BranchType, IProductSet, IScriptActivitySet)
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

    def assertMirrored(self, source_path, db_branch, destination_path=None):
        """Assert that 'db_branch' was mirrored succesfully.

        :param source_path: The URL of the branch that was mirrored.
        :param db_branch: The `IBranch` representing the branch that was
            mirrored.
        :param destination_path: If specified, the URL to examine for the
            destination branch. If unspecified, look directly at the mirrored
            area on the filesystem.
        """
        self.assertEqual(None, db_branch.mirror_status_message)
        self.assertEqual(
            db_branch.last_mirror_attempt, db_branch.last_mirrored)
        self.assertEqual(0, db_branch.mirror_failures)
        hosted_branch = Branch.open(source_path)
        if destination_path is None:
            destination_path = self.getMirroredPath(db_branch)
        mirrored_branch = Branch.open(destination_path)
        self.assertEqual(
            hosted_branch.last_revision(), db_branch.last_mirrored_id)
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

    def test_mirror_hosted_branch(self):
        # Run the puller on a populated hosted branch pull queue.
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

    def test_remirror_hosted_branch(self):
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
        upgrade(self.getHostedPath(db_branch), format_registry.get('1.6')())
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
        self.assertIsInstance(
            mirrored_branch.repository._format, RepositoryFormatKnitPack5)

    def test_mirror_hosted_loom_branch(self):
        # Run the puller over a branch with looms enabled.
        db_branch = self.factory.makeBranch(BranchType.HOSTED)
        loom_tree = self.makeLoomBranchAndTree('loom')
        self.pushToBranch(db_branch, loom_tree)
        db_branch.requestMirror()
        transaction.commit()
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(self.getHostedPath(db_branch), db_branch)

    def test_mirror_private_branch(self):
        # Run the puller with a private branch in the queue.
        db_branch = self.factory.makeBranch(BranchType.HOSTED)
        self.pushToBranch(db_branch)
        db_branch.requestMirror()
        db_branch.private = True
        transaction.commit()
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(self.getHostedPath(db_branch), db_branch)

    def test_mirror_mirrored_branch(self):
        # Run the puller on a populated mirrored branch pull queue.
        db_branch = self.factory.makeBranch(BranchType.MIRRORED)
        tree = self.make_branch_and_tree('.')
        tree.commit('rev1')
        db_branch.url = self.serveOverHTTP()
        db_branch.requestMirror()
        transaction.commit()
        command, retcode, output, error = self.runPuller('mirror')
        self.assertRanSuccessfully(command, retcode, output, error)
        # XXX: StuartBishop 2008-03-12 bug=193253: The first argument used to
        # be db_branch.url, but this triggered Bug #193253 where for some
        # reason Branch.open via HTTP makes an incomplete request to the
        # HttpServer leaving a dangling thread. Our test suite now fails
        # tests leaving dangling threads.
        self.assertMirrored(tree.basedir, db_branch)

    def _getProductWithStacking(self):
        # XXXSTACKING
        return self.factory.makeProduct()

    def _makeDefaultStackedOnBranch(self):
        """Make a default stacked-on branch.

        This creates a database branch on a product that allows default
        stacking, makes it the default stacked-on branch for that product,
        then creates a Bazaar branch for it. The Bazaar branch goes directly
        into the mirrored area and has a stackable format.

        :return: `IBranch`.
        """
        # Make the branch.
        product = self._getProductWithStacking()
        default_branch = self.factory.makeBranch(product=product)
        # Make it the default stacked-on branch.
        series = removeSecurityProxy(product.development_focus)
        series.user_branch = default_branch
        # Put a Bazaar branch into the mirrored area.
        default_branch_path = self.getMirroredPath(default_branch)
        ensure_base(get_transport(default_branch_path))
        BzrDir.create_branch_convenience(
            default_branch_path, format=format_registry.get('1.6')())
        return default_branch

    def test_stack_mirrored_branch(self):
        # Pulling a mirrored branch stacks that branch on the default stacked
        # branch of the product if such a thing exists.
        default_branch = self._makeDefaultStackedOnBranch()
        db_branch = self.factory.makeBranch(
            BranchType.MIRRORED, product=default_branch.product)

        tree = self.make_branch_and_tree('.', format='1.6')
        tree.commit('rev1')

        db_branch.url = self.serveOverHTTP()
        db_branch.requestMirror()
        transaction.commit()
        command, retcode, output, error = self.runPuller('mirror')
        self.assertRanSuccessfully(command, retcode, output, error)

        # To open this branch, we're going to need to use the Launchpad vfs.
        server = get_puller_server()
        server.setUp()
        self.addCleanup(server.tearDown)

        mirrored_url = 'lp-mirrored:///%s' % db_branch.unique_name
        self.assertMirrored(tree.basedir, db_branch, mirrored_url)
        mirrored_branch = Branch.open(mirrored_url)
        self.assertEqual(
            '/' + default_branch.unique_name,
            mirrored_branch.get_stacked_on_url())

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

    def test_mirror_imported_branch(self):
        # Run the puller on a populated imported branch pull queue.
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

        # XXX: StuartBishop 2008-03-12 bug=193253: check that the branch is
        # mirrored by going straight to the filesystem, rather than over HTTP.
        # This is to avoid Bazaar opening an HTTP connection that never
        # closes.
        self.assertMirrored(branch_path, db_branch)

    def test_mirror_empty(self):
        # Run the puller on an empty pull queue.
        command, retcode, output, error = self.runPuller("upload")
        self.assertRanSuccessfully(command, retcode, output, error)

    def test_records_script_activity(self):
        # A record gets created in the ScriptActivity table.
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
