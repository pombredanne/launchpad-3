# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

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
from bzrlib.bzrdir import BzrDir, format_registry
from bzrlib.config import TransportConfig
from bzrlib import errors
from bzrlib.tests import HttpServer
from bzrlib.transport import get_transport
from bzrlib.upgrade import upgrade
from bzrlib import urlutils

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.codehosting.vfs import get_lp_server
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
        self.makeCleanDirectory(config.codehosting.hosted_branches_root)
        self.addCleanup(
            shutil.rmtree, config.codehosting.hosted_branches_root)
        self.makeCleanDirectory(config.codehosting.mirrored_branches_root)
        self.addCleanup(
            shutil.rmtree, config.codehosting.mirrored_branches_root)

    def assertMirrored(self, db_branch, source_branch=None,
                       accessing_user=None):
        """Assert that 'db_branch' was mirrored succesfully.

        This method checks that the fields on db_branch show that the branch
        has been mirrored successfully, and checks that the Bazaar source and
        destination branches (from the puller's point of view) are consistent
        with this and each other.

        :param db_branch: The `IBranch` representing the branch that was
            mirrored.
        :param source_branch: The source branch.  If not passed, look for the
            branch in the hosted area.
        :param accessing_user: Open the mirrored branch as this user.  If not
            supplied create a fresh user for this -- but this won't work for a
            private branch.
        """
        if source_branch is None:
            source_branch = self.openBranchAsUser(db_branch, db_branch.owner)
        if accessing_user is None:
            accessing_user = self.factory.makePerson()
        transaction.commit()
        self.assertEqual(None, db_branch.mirror_status_message)
        self.assertEqual(
            db_branch.last_mirror_attempt, db_branch.last_mirrored)
        self.assertEqual(0, db_branch.mirror_failures)
        mirrored_branch = self.openBranchAsUser(db_branch, accessing_user)
        self.assertEqual(
            source_branch.last_revision(), db_branch.last_mirrored_id)
        self.assertEqual(
            source_branch.last_revision(), mirrored_branch.last_revision())
        self.assertEqual(
            source_branch._format.__class__,
            mirrored_branch._format.__class__)
        self.assertEqual(
            source_branch.repository._format.__class__,
            mirrored_branch.repository._format.__class__)
        return mirrored_branch

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

    def getLPServerForUser(self, user):
        """Construct a LaunchpadServer that serves branches as seen by `user`.

        Given 'db_branch', a database branch object 'db_branch', and
        'lp_server', the server returned by this method,
        'Branch.open(lp_server.get_url() + db_branch.unique_name)' will open
        the branch as 'user' sees it as a client of the code hosting service,
        i.e. it will be opened from the hosting area if the branch type HOSTED
        and the user has launchpad.Edit on the branch and opened from the
        mirrored area otherwise.
        """
        # We use the configured directories because these tests run the puller
        # in a subprocess which would have no way of knowing which directories
        # to look in if we used freshly created temporary directories.
        upload_directory = config.codehosting.hosted_branches_root
        mirror_directory = config.codehosting.mirrored_branches_root
        branchfs_endpoint_url = config.codehosting.branchfs_endpoint

        upload_url = urlutils.local_path_to_url(upload_directory)
        mirror_url = urlutils.local_path_to_url(mirror_directory)
        branchfs_client = xmlrpclib.ServerProxy(branchfs_endpoint_url)

        lp_server = get_lp_server(
            branchfs_client, user.id, upload_url, mirror_url)
        lp_server.setUp()
        self.addCleanup(lp_server.tearDown)
        return lp_server

    def openBranchAsUser(self, db_branch, user):
        """Open the branch as 'user' would see it as a client of codehosting.
        """
        lp_server = self.getLPServerForUser(user)
        return Branch.open(lp_server.get_url() + db_branch.unique_name)

    def pushBranch(self, db_branch, tree=None, format=None):
        """Push a Bazaar branch to db_branch.

        This method pushes the branch of the supplied tree (or an empty branch
        containing one revision if no tree is suppplied) to the location
        represented by the database branch 'db_branch'.
        """
        if tree is None:
            tree = self.make_branch_and_tree(
                self.factory.getUniqueString(), format=format)
            tree.commit('rev1')
        lp_server = self.getLPServerForUser(db_branch.owner)
        dest_transport = get_transport(
            lp_server.get_url() + db_branch.unique_name)
        try:
            dir_to = BzrDir.open_from_transport(dest_transport)
        except errors.NotBranchError:
            # create new branch
            tree.branch.bzrdir.clone_on_transport(dest_transport)
        else:
            tree.branch.push(dir_to.open_branch())

    def setUpMirroredBranch(self, db_branch, format=None):
        """Make a tree in the cwd and serve it over HTTP, returning the URL.
        """
        tree = self.make_branch_and_tree('.', format=format)
        tree.commit('rev1')
        db_branch.url = self.serveOverHTTP()
        db_branch.requestMirror()
        return tree

    def test_mirror_hosted_branch(self):
        # Run the puller on a populated hosted branch pull queue.
        db_branch = self.factory.makeAnyBranch(branch_type=BranchType.HOSTED)
        transaction.commit()
        self.pushBranch(db_branch)
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(db_branch)

    def test_remirror_hosted_branch(self):
        # When the format of a branch changes, we completely remirror it.
        # First we push up and mirror the branch in one format.
        db_branch = self.factory.makeAnyBranch(branch_type=BranchType.HOSTED)
        transaction.commit()
        pack_tree = self.make_branch_and_tree('pack', format='pack-0.92')
        self.pushBranch(db_branch, tree=pack_tree)
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(db_branch)
        # Then we upgrade the to a different format and ask for it to be
        # mirrored again.
        upgrade(self.getHostedPath(db_branch), format_registry.get('1.6')())
        transaction.begin()
        db_branch.requestMirror()
        transaction.commit()
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(db_branch)

    def test_mirror_hosted_loom_branch(self):
        # Run the puller over a branch with looms enabled.
        db_branch = self.factory.makeAnyBranch(branch_type=BranchType.HOSTED)
        transaction.commit()
        loom_tree = self.makeLoomBranchAndTree('loom')
        self.pushBranch(db_branch, tree=loom_tree)
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(db_branch)

    def test_mirror_private_branch(self):
        # Run the puller with a private branch in the queue.
        db_branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED, private=True)
        accessing_user = self.factory.makePerson()
        self.factory.makeBranchSubscription(
            branch=db_branch, person=accessing_user)
        transaction.commit()
        self.pushBranch(db_branch)
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(db_branch, accessing_user=accessing_user)

    def test_mirror_mirrored_branch(self):
        # Run the puller on a populated mirrored branch pull queue.
        db_branch = self.factory.makeAnyBranch(
            branch_type=BranchType.MIRRORED)
        tree = self.setUpMirroredBranch(db_branch)
        transaction.commit()
        command, retcode, output, error = self.runPuller('mirror')
        self.assertRanSuccessfully(command, retcode, output, error)
        self.assertMirrored(db_branch, source_branch=tree.branch)

    def _makeDefaultStackedOnBranch(self, private=False,
                                    branch_type=BranchType.HOSTED):
        """Make a default stacked-on branch.

        This creates a database branch on a product that allows default
        stacking, makes it the default stacked-on branch for that product,
        creates a Bazaar branch for it and pulls it over into the mirrored
        area.

        :return: `IBranch`.
        """
        # Make the branch.
        product = self.factory.makeProduct()
        default_branch = self.factory.makeProductBranch(
            product=product, private=private, name='trunk',
            branch_type=branch_type)
        # Make it the default stacked-on branch.
        series = removeSecurityProxy(product.development_focus)
        series.user_branch = default_branch
        # Arrange for it to be pulled.
        if branch_type == BranchType.HOSTED:
            puller_type = 'upload'
            transaction.commit()
            # For hosted branches, we just push it into the hosted area via
            # the codehosting vfs.
            self.pushBranch(default_branch)
        elif branch_type == BranchType.MIRRORED:
            puller_type = 'mirror'
            # For mirrored branches, we serve the branch over HTTP, point the
            # database branch at this HTTP server and call requestMirror()
            self.setUpMirroredBranch(default_branch, format='1.6')
            transaction.commit()
        else:
            raise AssertionError(
                "don't know how to make a %s default branch"
                % branch_type.TITLE)
        # Pull it.
        command, retcode, output, error = self.runPuller(puller_type)
        self.assertRanSuccessfully(command, retcode, output, error)
        return default_branch

    def test_stack_mirrored_branch(self):
        # Pulling a mirrored branch stacks that branch on the default stacked
        # branch of the product if such a thing exists.
        default_branch = self._makeDefaultStackedOnBranch()
        db_branch = self.factory.makeProductBranch(
            branch_type=BranchType.MIRRORED, product=default_branch.product)
        tree = self.setUpMirroredBranch(db_branch, format='1.6')
        transaction.commit()
        command, retcode, output, error = self.runPuller('mirror')
        self.assertRanSuccessfully(command, retcode, output, error)
        mirrored_branch = self.assertMirrored(
            db_branch, source_branch=tree.branch)
        self.assertEqual(
            '/' + default_branch.unique_name,
            mirrored_branch.get_stacked_on_url())

    def test_hosted_branch_stacked_on_mirrored_branch(self):
        # If a hosted branch is stacked on a mirrored branch, the puller opens
        # the hosted branch stacked on the copy of the branch in the mirrored
        # area, rather than trying to open it stacked on the non-existent
        # version of the branch in the hosted area.
        default_branch = self._makeDefaultStackedOnBranch(
            branch_type=BranchType.MIRRORED)
        db_branch = self.factory.makeProductBranch(
            branch_type=BranchType.HOSTED, product=default_branch.product)
        transaction.commit()
        self.pushBranch(db_branch, format='1.6')
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        mirrored_branch = self.assertMirrored(db_branch)
        self.assertEqual(
            '/' + default_branch.unique_name,
            mirrored_branch.get_stacked_on_url())

    def test_manual_stacking(self):
        # If the user manually stacks on a Launchpad branch, the branch.conf
        # file of the resulting branch will contain the full URL of the
        # manually selected branch.  The puller still manages to open the
        # branch and sets the stacking information of the branch in the
        # mirrored area to be the most compatible "/" + unique_name form.  We
        # have to cheat rather to test this because the full URLs don't work
        # in the environment this test is run in, so we set the stacking URL
        # in the hosted area directory after we've pushed it and then clear it
        # again so that assertMirrored can work.  The test is still valid
        # though, as the paths are as they should be when the puller is run.
        default_branch = self._makeDefaultStackedOnBranch()
        db_branch = self.factory.makeProductBranch(
            branch_type=BranchType.HOSTED, product=default_branch.product)
        transaction.commit()
        self.pushBranch(db_branch, format='1.6')
        # Because Bazaar can't access branches over bzr+ssh in this test, we
        # cheat and set the stacking information directly.
        branch_config = TransportConfig(
            get_transport(self.getHostedPath(db_branch)), 'branch.conf')
        branch_config.set_option(
            'stacked_on_location',
            'bzr+ssh://bazaar.launchpad.dev/' + default_branch.unique_name)
        command, retcode, output, error = self.runPuller('upload')
        self.assertRanSuccessfully(command, retcode, output, error)
        # We clear the stacking information again here so that assertMirrored
        # can open the branch in the hosted area.
        branch_config.set_option('stacked_on_location', '')
        mirrored_branch = self.assertMirrored(db_branch)
        self.assertEqual(
            '/' + default_branch.unique_name,
            mirrored_branch.get_stacked_on_url())

    def test_stack_mirrored_branch_onto_private(self):
        # If the default stacked-on branch is private then mirrored branches
        # aren't stacked when they are mirrored.
        default_branch = self._makeDefaultStackedOnBranch(private=True)
        db_branch = self.factory.makeProductBranch(
            branch_type=BranchType.MIRRORED, product=default_branch.product)

        tree = self.setUpMirroredBranch(db_branch, format='1.6')
        transaction.commit()
        command, retcode, output, error = self.runPuller('mirror')
        self.assertRanSuccessfully(command, retcode, output, error)
        mirrored_branch = self.assertMirrored(
            db_branch, source_branch=tree.branch)
        self.assertRaises(
            errors.NotStacked, mirrored_branch.get_stacked_on_url)

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
        db_branch = self.factory.makeAnyBranch(
            branch_type=BranchType.IMPORTED)
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

        self.assertMirrored(db_branch, source_branch=tree.branch)

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


# XXX: JonathanLange 2009-03-27 bug=349316: Disable these tests because they
# are leaking threads, causing intermittent test failures.
def test_suite():
#    return unittest.TestLoader().loadTestsFromName(__name__)
    return unittest.TestSuite()
