# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Acceptance tests for Supermirror SFTP server's bzr support.
"""

__metaclass__ = type

#import unittest
import tempfile

from bzrlib.branch import ScratchBranch
import bzrlib.branch

from twisted.trial import unittest
from twisted.python.util import sibpath

from canonical.launchpad import database


class AcceptanceTests(unittest.TestCase):
    """ 
    These are the agreed acceptance tests for the Supermirror SFTP system's
    initial implementation of bzr support, converted from the English at
    https://wiki.launchpad.canonical.com/SupermirrorTaskList
    """

    def setUp(self):
        # XXX spiv 2005-12-14
        # This should be unnecessary, but bzr's use of paramiko always tries
        # password auth, even though Conch correctly tells it that only
        # publickey is supported.  So, we temporarily monkey-patch getpass to
        # stop the tests hanging at a password prompt if logging in breaks.
        import getpass
        self.getpass = getpass.getpass
        def newgetpass(prompt=None):
            self.fail('getpass should not be called.')
        getpass.getpass = newgetpass

        # Create a local branch with one revision
        self.local_branch = ScratchBranch(files=['foo'])
        self.local_branch.add('foo')
        self.local_branch.commit('Added foo')

        # Point $HOME at a test ssh config and key.
        self.userHome = os.path.abspath(self.mktemp())
        print 'userHome:', self.userHome
        os.makedirs(os.path.join(self.userHome, '.ssh'))
        os.makedirs(os.path.join(self.userHome, 'bin'))
        shutil.copyfile(
            sibpath(__file__, 'id_dsa'), 
            os.path.join(self.userHome, '.ssh', 'id_dsa'))
        shutil.copyfile(
            sibpath(__file__, 'id_dsa.pub'), 
            os.path.join(self.userHome, '.ssh', 'id_dsa.pub'))
        shutil.copyfile(
            sibpath(__file__, 'ssh'), 
            os.path.join(self.userHome, 'bin', 'ssh'))
        os.chmod(os.path.join(self.userHome, '.ssh', 'id_dsa'), 0600)
        os.chmod(os.path.join(self.userHome, 'bin', 'ssh'), 0755)
        self.realHome = os.environ['HOME']
        self.realPath = os.environ['PATH']
        os.environ['HOME'] = self.userHome
        os.environ['PATH'] = self.userHome + '/bin:' + self.realPath

    def tearDown(self):
        import getpass
        getpass.getpass = self.getpass
        os.environ['HOME'] = self.realHome
        os.environ['PATH'] = self.realPath

    def test_1_bzr_sftp(self):
        """
        The bzr client should be able to read and write to the Supermirror SFTP
        server just like another other SFTP server.  This means that actions
        like:
            * `bzr push sftp://testinstance/somepath`
            * `bzr log sftp://testinstance/somepath`
        (and/or their bzrlib equivalents) and so on should work, so long as the
        user has permission to read or write to those URLs.
        """
        
        # Start test server
        server = start_test_sftp_server()

        # Push the local branch to the server
        rv = os.system('cd %s; PYTHONPATH= bzr push %s' 
                       % (self.local_branch.base, 
                          server.base + '~testuser/+junk/test-branch',))
        self.assertEqual(0, rv)
        remote_branch = bzrlib.branch.Branch.open(
            server.base + '~testuser/+junk/test-branch')
        #remote_branch.pull(self.local_branch)
        
        # Check that the pushed branch looks right
        self.assertEqual(
            self.local_branch.last_revision(), remote_branch.last_revision())

        # Tear down test server
        server.stop()

    def test_2_namespace_restrictions(self):        
        """
        The namespace restrictions described in
        SupermirrorFilesystemHierarchy should be enforced. So operations
        such as:
            * `bzr push sftp://testinstance/~user/missing-product/new-branch`
            * `bzr push sftp://testinstance/~not-my-team/real-product/some-branch`
            * `bzr push sftp://testinstance/~team/+junk/anything`
        should fail.
        """

        # Start test server
        server = start_test_sftp_server()

        # Cannot push branches to products that don't exist
        self.assertRaises(
            PermissionError, 
            bzrlib.branch.Branch.initialize,
            server.base + '~testuser/fake-product/hello')

        # Teams cannot have +junk products
        self.assertRaises(
            PermissionError,
            bzrlib.branch.Branch.initialize,
            server.base + '~testteam/+junk/hello')

        # Cannot push to team directories that the user isn't a member of
        self.assertRaises(
            PermissionError,
            bzrlib.branch.Branch.initialize,
            server.base + '~not-my-team/real-product/hello')

        # XXX: what about lp-incompatible branch dir names (e.g. capital
        # Letters) -- Are they disallowed or accepted?  If accepted, what will
        # that branch's Branch.name be in the database?

    def test_3_rename_branch(self):
        """
        Branches should be able to be renamed in the Launchpad webapp, and those
        renames should be immediately reflected in subsequent SFTP connections.

        Also, the renames may happen in the database for other reasons, e.g. if
        the DBA running a one-off script.
        """

        # Start test server
        server = start_test_sftp_server()
        
        # Push the local branch to the server
        remote_branch = bzrlib.branch.Branch.initialize(
            server.base + '~testuser/+junk/test-branch')
        remote_branch.pull(self.local_branch)

        # Rename branch in the database
        lp_txn.begin()
        branch = database.Branch.selectOneBy(name='test-branch')
        branch_id = branch.id
        branch.name = 'renamed-branch'
        lp_txn.commit()
        remote_branch = bzrlib.branch.Branch.initialize(
            server.base + '~testuser/+junk/renamed-branch')
        self.assertEqual(
            self.local_branch.last_revision(), remote_branch.last_revision())

        # Assign to a different product in the database.  This is effectively a
        # Rename as far as bzr is concerned: the URL changes.
        lp_txn.begin()
        branch = database.Branch.get(branch_id)
        branch.product = database.Product.get('mozilla-firefox')
        lp_txn.commit()
        remote_branch = bzrlib.branch.Branch.initialize(
            server.base + '~testuser/mozilla-firefox/renamed-branch')
        self.assertEqual(
            self.local_branch.last_revision(), remote_branch.last_revision())

        # Rename person in the database.  Again, the URL changes.
        lp_txn.begin()
        branch = database.Branch.get(branch_id)
        branch.person.name = 'renamed-user'
        lp_txn.commit()
        remote_branch = bzrlib.branch.Branch.initialize(
            server.base + '~renamed-user/mozilla-firefox/renamed-branch')
        self.assertEqual(
            self.local_branch.last_revision(), remote_branch.last_revision())

    def _push_branch_to_sftp_server(self):
        """
        Helper function that starts a test sftp server, and uploads
        self.local_branch to it.

        Returns branch_id.
        """
          
        # Start test server
        server = start_test_sftp_server()
        
        # Push the local branch to the server
        remote_branch = bzrlib.branch.Branch.initialize(
            server.base + '~testuser/+junk/test-branch')
        remote_branch.pull(self.local_branch)

        branch_id = server.last_accessed_branch_id
        server.stop()
        return branch_id

    def test_4_url_for_mirror(self):
        """
        There should be an API that can generate a URL for a branch for
        copy-to-mirror script to use. For example, for a branch with a database
        ID of 0xabcdef12, the URL may be something like
        `/srv/supermirrorsftp/branches/ab/cd/ef/12`.
        """
        # Push branch to sftp server
        branch_id = self._push_branch_to_sftp_server()

        # Generate the path for copy-to-mirror script to use
        mirror_from_path = get_path_for_copy_to_mirror(branch_id)

        # Construct a Branch object that reads directly from the on-disk storage
        # of the server.
        server_branch = bzrlib.branch.Branch.initialize(mirror_from_path)

        # Check that it's the branch we're looking for
        self.assertEqual(
            self.local_branch.last_revision(), server_branch.last_revision())
        
    def test_5_mod_rewrite_data(self):
        """
        A mapping file for use with Apache's mod_rewrite should be generated
        correctly.
        """
        # Push branch to sftp server
        branch_id = self._push_branch_to_sftp_server()

        # Check the generated mapping file has the right contents        
        self.assertEqual(
            '~testuser/+junk/test-branch %d\n' % branch_id,
            generate_path_mapping([branch_id]))


def start_test_sftp_server():
    return TestSFTPServer()

from canonical.launchpad.daemons import tachandler
import os
import shutil

class SFTPSetup(tachandler.TacTestSetup):
    root = '/tmp/sftp-test'
    tacfile = '/home/andrew/warthogs/supermirrorsftp/devel/supermirrorsftp/tests/test.tac'
    pidfile = root + '/twistd.pid'
    logfile = root + '/twistd.log'
    def setUpRoot(self):
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
        os.makedirs(self.root, 0700)

class TestSFTPServer:
    """This is the object returned by start_test_sftp_server."""
    # XXX: stub implementation for now.
    base = 'sftp://testuser@localhost:22222/'

    def __init__(self):
        #import os
        #os.system('cd ..; SUPERMIRROR_PORT=22222 PYTHONPATH=%s
        #/home/andrew/svn/Twisted/bin/twistd -oy
        #/home/andrew/warthogs/supermirrorsftp/devel/sftp.tac' 
        #    % os.environ.get('PYTHONPATH', ''))
        self.sftp = SFTPSetup()
        self.sftp.setUp()

    def stop(self):
        #import os
        #os.kill(int(open('twistd.pid', 'r').read()))
        self.sftp.tearDown()

    last_accessed_branch_id = -1

