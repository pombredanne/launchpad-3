# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Acceptance tests for Supermirror SFTP server's bzr support.
"""

__metaclass__ = type

import unittest
import tempfile

from bzrlib.branch import ScratchBranch

from canonical.launchpad import database


class AcceptanceTests(unittest.TestCase):
    """ 
    These are the agreed acceptance tests for the Supermirror SFTP system's
    initial implementation of bzr support, converted from the English at
    https://wiki.launchpad.canonical.com/SupermirrorTaskList
    """

    def setUp(self):
        # Create a local branch with one revision
        self.local_branch = ScratchBranch(files=['foo'])
        self.local_branch.add('foo')
        self.local_branch.commit('Added foo')

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
        remote_branch = bzrlib.branch.Branch.initialize(
            server.base + '~testuser/+junk/test-branch')
        remote_branch.pull(self.local_branch)
        
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


class TestSFTPServer:
    """This is the object returned by start_test_sftp_server."""
    # XXX: stub implementation for now.
    base = 'sftp://localhost:22222/'

    def stop(self):
        pass

    last_accessed_branch_id = -1

